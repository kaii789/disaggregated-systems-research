#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <time.h>
#include <float.h>
#include <sys/timeb.h>
#include "../../common/sim_api.h"
#include "../../common/cas_lock.h"
#include "../../common/cas_barrier.h"
#include "../../common/graph.h"


#define MAX            100000000
#define INT_MAX        100000000
#define BILLION 1E9

#define __STDC_LIMIT_MACROS
#define __STDC_CONSTANT_MACROS

// Thread Argument Structure
typedef struct
{
    struct Graph* graph;
#if INT
    int*      D;
#else
    float*      D;
#endif
    int       tid;
    int       nthreads;
    int       groups;
#ifdef CUSTOM
    lock_t**   locks;
    barrier_t* barrier_total;
    barrier_t* barrier;
#endif
#ifdef PTHREAD
    pthread_mutex_t **locks;
    pthread_barrier_t *barrier_total;
    pthread_barrier_t *barrier;
#endif
} thread_arg_t;

//Function Initializers
#if INT
int initialize_single_source(int* D, int source, int N);
#else
int initialize_single_source(float* D, int source, int N);
#endif

//Global Variables
int terminate = 0;
int range=1;       //starting range
int old_range =1;
int P_max=256;     //Heuristic parameter. A lower value will result in incorrect distances
int bw_cnt = 0;
thread_arg_t thread_arg[1024];
pthread_t   thread_handle[1024];

//Primary Parallel Function
void* do_work(void* args)
{
    volatile thread_arg_t* arg = (thread_arg_t*) args;
    struct Graph* graph      = arg->graph;
    int tid                  = arg->tid;  //thread id
    int nthreads             = arg->nthreads;    //Max threads
#if INT
    int* D                   = arg->D;  
#else
    float* D                   = arg->D;    
#endif
    int i, v = 0, neighbor;

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
        start = mod * (vert_per_proc + 1) + (tid -  mod) * vert_per_proc;
        stop = start + vert_per_proc;
    }

 
    unsigned long int *local = (unsigned long int *) malloc(2*sizeof(unsigned long int));
    local[1] = (unsigned long int) (&D[start]);
    local[0] = (unsigned long int) (&D[stop]);

    int iterations = 1;
    int edg=0;

#ifdef CUSTOM
    barrier_wait(arg->barrier,tid);
#endif
#ifdef PTHREAD
    pthread_barrier_wait(arg->barrier);
#endif

    for (i=0;i<iterations;i++) {
        for(v=start; v<stop;v++) {
            for(int i = 0; i < graph->array[v].neighboors; i++) {
                edg++;
                neighbor = graph->array[v].head[i].dest;

#ifdef CUSTOM
                lock_acquire(arg->locks[neighbor], tid);
#endif
#ifdef PTHREAD
                pthread_mutex_lock(arg->locks[neighbor]);
#endif

                //relax
                if((D[neighbor] > (D[v] + graph->array[v].head[i].weight)))        //relax, update distance
                    D[neighbor] = D[v] + graph->array[v].head[i].weight;

#ifdef CUSTOM
                lock_release(arg->locks[neighbor], tid);
#endif
#ifdef PTHREAD
                pthread_mutex_unlock(arg->locks[neighbor]);
#endif
            }
        }
#ifdef CUSTOM
        barrier_wait(arg->barrier, tid);
#endif
#ifdef PTHREAD
    pthread_barrier_wait(arg->barrier);
#endif


    }

    printf("tid %d edg %d\n", tid, edg);
    return NULL;
}


int main(int argc, char** argv)
{
    char *graphfile;
    struct Graph* graph;
    int nthreads;

    graphfile = argv[1];
    nthreads = atoi(argv[2]);

    graph = graph_read_mtx(graphfile);
    printf(" Graph Read finished\n");

    // Memory Allocations
#if INT
    int* D;
    if(posix_memalign((void**) &D, 64, graph->V * sizeof(int)))
    {
        fprintf(stderr, "Allocation of memory failed\n");
        exit(EXIT_FAILURE);
    }
#else
    float* D;
    if(posix_memalign((void**) &D, 64, graph->V * sizeof(float)))
    {
        fprintf(stderr, "Allocation of memory failed\n");
        exit(EXIT_FAILURE);
    }

#endif

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

    unsigned long int *locks_s;
    locks_s = (unsigned long int *) malloc((graph->V+1) * sizeof(unsigned long int));
    for(int i=0; i<graph->V+1; i++) {
        locks_s[i] = (unsigned long int) (&locks[i]->state);
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
    //barriers[0] = (unsigned long int) (&barrier->cnt);
    barriers[0] = (unsigned long int) (&barrier->passed);
    //barriers[2] = (unsigned long int) (&barrier->nthreads);
    //send_barriers((unsigned long int *) barriers, 1, 0);
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


    // Initialize Data Structures
    initialize_single_source(D, 0, graph->V);

    // Thread arguments
    for(int j = 0; j <nthreads; j++) {
        thread_arg[j].graph      = graph;
        thread_arg[j].D          = D;
        thread_arg[j].tid        = j;
        thread_arg[j].nthreads   = nthreads;
        thread_arg[j].groups     = groups;
        thread_arg[j].locks      = locks;
        thread_arg[j].barrier_total = barrier_total;
        thread_arg[j].barrier    = barrier;
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

    return 0;
}

#if INT
int initialize_single_source(int*  D,
        int   source,
        int   N)
#else
int initialize_single_source(float*  D,
        int   source,
        int   N)
#endif
{
    for(int i = 0; i < N; i++) {
#if INT
        D[i] = INT_MAX;
#else
        D[i] = FLT_MAX;
#endif
    }

    D[source] = 0;
    return 0;
}
