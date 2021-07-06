#include <stdlib.h>
#include "barrier_api.h"

struct barrier_struct {
    unsigned int nthreads;
    unsigned int cnt;
	volatile unsigned int passed;
    char padding[64 - 3*sizeof(unsigned int)];
} __attribute__((packed)) __attribute__((aligned(64)));

typedef struct barrier_struct barrier_t;

barrier_t *barrier_init(int nthreads)
{
    barrier_t *barrier;

    if(posix_memalign((void **)&barrier, 64, sizeof(*barrier))) {
        printf("Error\n");
        return NULL;
    }

    barrier->nthreads = nthreads;
    barrier->cnt = 0;
    barrier->passed = 0;

    return barrier;
}

void barrier_free(barrier_t *barrier)
{
    free(barrier);
}

void barrier_wait(barrier_t *barrier, int tid)
{
    barrier_t *b = barrier;
    unsigned int passed_old = b->passed;

    if(__sync_fetch_and_add(&b->cnt, 1) == (b->nthreads - 1)) {   
        // The last thread, faced barrier.

        b->cnt = 0;
        // *bar* should be reseted strictly before updating of barriers counter.
        __sync_synchronize(); 
        b->passed++; // Mark barrier as passed.
    } else {   
        // Not the last thread. Wait others.
        //while(b->passed == passed_old) {;} 
        while(b->passed == passed_old) {for(int i=0; i<10; i++) asm("nop");} 
        // Need to synchronize cache with other threads, passed barrier.
        __sync_synchronize();
    }   
}
