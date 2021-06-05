#include <stdio.h>
#include <stdlib.h>

#include "sim_api.h"

struct Node {
    long int contents[2047];  // a long int is 8 bytes, this is 8*2047 = 16376 bytes = 16 KB - 8 bytes
    struct Node *next;        // 8 bytes on a 64 bit machine
};

int main(int argc, char **argv) {
    printf("\n\n\n------   mem_test program starting   ------\n");
    printf("an int is %ld bytes, a long int is %ld bytes\n", sizeof(int), sizeof(long int));
    // printf("an struct Node * is %ld bytes\n", sizeof(struct Node *));
    printf("a struct Node is %ld bytes\n", sizeof(struct Node));

    SimRoiStart();
    struct Node head;
    long int num_nodes = 4096;  // 4096 means total lifetime memory usage is a little over 4096 * 16384 = 64 MB

    // Allocation
    struct Node *p_prev = &head;
    for (long int i = 0; i < num_nodes; i++) {
        struct Node *p_new_node = malloc(sizeof(struct Node));
        if (p_new_node == NULL) {
            fprintf(stderr, "malloc call in mem_test.c failed\n");
            exit(1);
        }
        p_prev->next = p_new_node;
        p_prev = p_new_node;
    }
    p_prev->next = NULL;  // p_prev points to the tail of the linked list

    //SimRoiEnd();

    struct Node *p_cur = &head;
    long int a = 1;

    //SimRoiStart();

    // Reads
    p_cur = &head;
    while (p_cur != NULL) {
        // Access one long int from each 4KB page
        a = p_cur->contents[3];
        for (long int k = 0; k < 10; ++k) {
            a /= 2;  // Drain some time
        }
        a = p_cur->contents[515];
        for (long int k = 0; k < 10; ++k) {
            a /= 2;  // Drain some time
        }
        a = p_cur->contents[1027];
        for (long int k = 0; k < 10; ++k) {
            a /= 2;  // Drain some time
        }
        a = p_cur->contents[1539];
        for (long int k = 0; k < 10; ++k) {
            a /= 2;  // Drain some time
        }
        p_cur = p_cur->next;
    }

    // Writes
    p_cur = &head;
    a = 1;
    while (p_cur != NULL) {
        // Write one long int to each 4KB page?
        p_cur->contents[2] = a;
        for (long int k = 0; k < 100; ++k) {
            a /= 2;  // Drain some time
        }
        p_cur->contents[514] = a + 2;
        for (long int k = 0; k < 100; ++k) {
            a /= 2;  // Drain some time
        }
        p_cur->contents[1026] = a + 5;
        for (long int k = 0; k < 100; ++k) {
            a /= 2;  // Drain some time
        }
        p_cur->contents[1538] = a + 7;
        for (long int k = 0; k < 200; ++k) {
            a /= 2;  // Drain some time
        }
        p_cur = p_cur->next;
        a++;  // have some changes for a bit more variability
    }

    SimRoiEnd();

    printf("------   mem_test program end   ------\n\n\n");
}