#include <stdlib.h>
#include <stdio.h>

extern int bw_cnt;

typedef struct {
	int data;
	char padding[64 - sizeof(int)];
} __attribute__((packed)) __attribute__((aligned(64))) ddata_t;

typedef enum {
    UNLOCKED = 0,
    LOCKED
} lock_state_t;

struct lock_struct {
    lock_state_t state;
    //ddata_t *dummy;
	char padding[64 - sizeof(lock_state_t)];
} __attribute__((packed)) __attribute__((aligned(64)));

typedef struct lock_struct lock_t;


lock_t *lock_init(int nthreads)
{
    lock_t *lock;

    if(posix_memalign((void **)&lock, 64, sizeof(*lock))) {
        printf("Error\n");
        return NULL;
    }
        
    lock->state = UNLOCKED;

    //XMALLOC(lock->dummy, nthreads);
    return lock;
}

void lock_free(lock_t *lock)
{
   free(lock);
}
int counter = 0;
void lock_acquire(lock_t *lock, int tid)
{
    lock_t *l = lock;

    while (__sync_val_compare_and_swap(&l->state, UNLOCKED, LOCKED) == LOCKED){
        // for(int i=0; i<2; i++);
        /* do nothing FIXME*/ ;
        bw_cnt++;
    }
}

void lock_release(lock_t *lock, int tid)
{
    lock_t *l = lock;

    /* Why not just 'l->state = UNLOCKED' here?? */
    __sync_val_compare_and_swap(&l->state, LOCKED, UNLOCKED);
}
