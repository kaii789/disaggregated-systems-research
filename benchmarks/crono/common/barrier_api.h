#ifndef BARRIER_H
#define BARRIER_H

/**
 * Defines the barrier API.
 **/

typedef struct barrier_struct barrier_t;

barrier_t *barrier_init(int nthreads);
void barrier_free(barrier_t *barrier);

void barrier_wait(barrier_t *barrier, int tid);

#endif /* BARRIER_H */
