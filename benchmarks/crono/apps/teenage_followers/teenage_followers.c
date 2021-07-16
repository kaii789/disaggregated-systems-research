//#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <time.h>
#include <sys/timeb.h>
#include <string.h>
#include "../../common/sim_api.h"
#include "../../common/cas_lock.h"
#include "../../common/cas_barrier.h"
#include "../../common/graph.h"

#define MAX            100000000
#define INT_MAX        100000000
#define BILLION 1E9


//Thread Structure
typedef struct
{
    struct Graph* graph;
    double*  D;
    int       tid;
    int       nthreads;
    int      groups;
#ifdef CUSTOM
    barrier_t* barrier_total;
    barrier_t* barrier;
    lock_t** locks;
#endif
#ifdef PTHREAD
    pthread_mutex_t **locks;
    pthread_barrier_t *barrier_total;
    pthread_barrier_t *barrier;
#endif
} thread_arg_t;

//Function declarations
int initialize_single_source(double* D, int N);
int find_teenagers(double*  D, struct Graph* graph, int N); 

//Global Variables
#define DUMP_FACTR 0.85 
int Total = 20;
int terminate = 0;                 //work termination
int largest=0;
thread_arg_t thread_arg[1024];
pthread_t   thread_handle[1024];
int bw_cnt = 0;
int dummy=0;

//Primary Parallel Function
void* do_work(void* args) {
    //Thread variables and arguments
    volatile thread_arg_t* arg = (thread_arg_t*) args;
    struct Graph* graph      = arg->graph;
    int tid                  = arg->tid;  //thread id cgiannoula
    int nthreads             = arg->nthreads;    //Max threads
    double* D                = arg->D;    
    int v = 0;
    int i = 0, j, neighbor;
    double inc;

    int start =  0;  //tid    * DEG / (arg->P);
    int stop  = 0;   //(tid+1) * DEG / (arg->P);

    //Chunk work for threads via double precision
    int vert_per_proc = graph->V / nthreads;
    int mod = graph->V % nthreads;

    for(i = 0; i < mod; i++)
        if(tid == i)
            vert_per_proc ++;

    start = tid * vert_per_proc;
    stop = (tid + 1) * vert_per_proc;

    if(tid >= mod) {
        start = mod * (vert_per_proc + 1) + (tid - mod) * vert_per_proc;
        stop = start + vert_per_proc;
    }


    int edg = 0;
    int remote = 0; 
    //Pagerank iteration count
    int iterations = 1; // FIXME cgiannoula

#ifdef CUSTOM
    barrier_wait(arg->barrier,tid);
#endif
#ifdef PTHREAD
    pthread_barrier_wait(arg->barrier);
#endif

    for (i=0;i<iterations;i++) {
        for(v=start; v<stop; v++){
            if (graph->array[v].neighboors > 0){ // if I am teenager ( my_age >12 && my_age < 15)
                for(j=0; j<graph->array[v].neighboors; j++) {
                    neighbor = graph->array[v].head[j].dest; 
                    edg++;  

#ifdef CUSTOM
                    lock_acquire(arg->locks[neighbor], tid); // push
#endif
#ifdef PTHREAD
                    pthread_mutex_lock(arg->locks[neighbor]);
#endif

                    D[neighbor] ++; 

#ifdef CUSTOM
                    lock_release(arg->locks[neighbor], tid);
#endif
#ifdef PTHREAD
                    pthread_mutex_unlock(arg->locks[neighbor]);
#endif
                }
            }
        }

#ifdef CUSTOM
        barrier_wait(arg->barrier, tid);
#endif
#ifdef PTHREAD
        pthread_barrier_wait(arg->barrier);
#endif


    }

    printf("\n %d %d %d %d %d",tid, edg, dummy, start, v);
    return NULL;
}


// Main
int main(int argc, char** argv)
{
    char *graphfile;
    struct Graph* graph;
    int nthreads;

    graphfile = argv[1];
    nthreads = atoi(argv[2]);

    graph = graph_read_mtx(graphfile);
    printf(" Graph Read finished %d\n", graph->V);

    // Memory Allocations
    double* D;
    D = (double *) malloc((graph->V+1) * sizeof(double));
    initialize_single_source(D, graph->V);

#ifdef CUSTOM
    // Synchronization variables
    lock_t* lock;
    lock_t** locks;
    barrier_t *barrier_total;
    barrier_t *barrier;

    lock = lock_init(nthreads);
    locks = (lock_t **) malloc((graph->V+1) * sizeof(lock_t *));
    for(int i=0; i<graph->V+1; i++) {
        locks[i] = lock_init(nthreads);
    }

    // cgiannoula
    int groups;
    if (nthreads <= 16)
        groups = 1;
    else if (nthreads <= 32)
        groups = 2;
    else if (nthreads <= 48)
        groups = 3;
    else if (nthreads <= 64)
        groups = 4;
    else if (nthreads <= 128)
        groups = 4;

    // Synchronization Initializations
    barrier_total = barrier_init(nthreads);
    barrier = barrier_init(nthreads);

    unsigned long int *barriers;
    barriers = (unsigned long int *) malloc(3*sizeof(unsigned long int));
    //barriers[0] = (unsigned long int) (&barrier->passed); 
#endif
#ifdef PTHREAD
    // cgiannoula
    int groups;
    if (nthreads <= 16)
        groups = 1;
    else if (nthreads <= 32)
        groups = 2;
    else if (nthreads <= 48)
        groups = 3;
    else if (nthreads <= 64)
        groups = 4;
    else if (nthreads <= 128)
        groups = 4;

    pthread_mutex_t **locks = (pthread_mutex_t **) malloc((graph->V+1) * sizeof(pthread_mutex_t *));
    for(int i=0; i<graph->V+1; i++) {
        locks[i] = (pthread_mutex_t *) malloc(sizeof(pthread_mutex_t));
        pthread_mutex_init(locks[i], NULL);
    }

    pthread_barrier_t *barrier_total;
    pthread_barrier_t *barrier;
    barrier_total = (pthread_barrier_t *) malloc(sizeof(pthread_barrier_t));
    barrier = (pthread_barrier_t *) malloc(sizeof(pthread_barrier_t));
    pthread_barrier_init(barrier_total, NULL, nthreads);
    pthread_barrier_init(barrier, NULL, nthreads);
#endif 
    __sync_synchronize();

    // Thread arguments
    for(int j = 0; j <nthreads; j++) {
        thread_arg[j].graph      = graph;
        thread_arg[j].D          = D;
        thread_arg[j].tid        = j;
        thread_arg[j].nthreads   = nthreads;
        thread_arg[j].groups     = groups;
        thread_arg[j].barrier_total = barrier_total;
        thread_arg[j].barrier    = barrier;
        thread_arg[j].locks      = locks;
    }

    // CPU Time
    struct timespec requestStart, requestEnd;
    clock_gettime(CLOCK_REALTIME, &requestStart);

    SimRoiStart();


    // Spawn Threads
    for(int j = 1; j < nthreads; j++) {
        pthread_create(thread_handle+j,
                NULL,
                do_work,
                (void*)&thread_arg[j]);
    }
    do_work((void*) &thread_arg[0]);  //master thread initializes itself

    // Join threads
    for(int j = 1; j < nthreads; j++) { //mul = mul*2;
        pthread_join(thread_handle[j],NULL);
    }

    printf("\nThreads Joined!\n");

    if (SimInSimulator()) {
        printf("API Test: Running in the simulator\n"); fflush(stdout);
    } else {
        printf("API Test: Not running in the simulator\n"); fflush(stdout);
    }

    SimRoiEnd();

    clock_gettime(CLOCK_REALTIME, &requestEnd);
    double accum = ( requestEnd.tv_sec - requestStart.tv_sec ) + ( requestEnd.tv_nsec - requestStart.tv_nsec ) / BILLION;
    printf( "\nTime Taken:\n%lf seconds\n", accum );

    //find_teenagers(D, graph, graph->V);
    
    return 0;
}

int initialize_single_source(double*  D, int   N) {
    for(int i = 0; i <= N; i++) {
        D[i] = 0;
    }

    return 0;
}

int find_teenagers(double*  D, struct Graph* graph, int   N) {
    for(int i = 0; i < N; i++) {
        if (D[i] != graph->array[i].neighboors)
            printf("Error %d\n", i, D[i], graph->array[i].neighboors);
    }

    return 0;
}
