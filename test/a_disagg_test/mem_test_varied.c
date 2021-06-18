#include <stdio.h>
#include <stdlib.h>

#include "sim_api.h"

// struct SmallNode {
//     long int contents[127];   // a long int is 8 bytes, this is 8*127 = 1016 bytes = 0.25 KB - 8 bytes
//     struct SmallNode *next;        // 8 bytes on a 64 bit machine
// };
struct SmallNode {
    long int contents[255];   // a long int is 8 bytes, this is 8*255 = 2040 bytes = 2 KB - 8 bytes
    struct SmallNode *next;        // 8 bytes on a 64 bit machine
};

int main(int argc, char **argv) {
    printf("\n\n\n------   mem_test program starting   ------\n");
    printf("an int is %ld bytes, a long int is %ld bytes\n", sizeof(int), sizeof(long int));
    // printf("an struct SmallNode * is %ld bytes\n", sizeof(struct SmallNode *));
    printf("a struct SmallNode is %ld bytes\n", sizeof(struct SmallNode));

    SimRoiStart();
    long int num_nodes = 512;  // 512 means total lifetime memory usage is a little over ((2 + 513) * 512 / 2 + 512 / 2) * 2KB ~= 263 681 KB ~= 257.5 MB
    struct SmallNode * arrays[num_nodes + 1];

    // Allocation
    for (long int i = 2; i < num_nodes + 2; ++i) {
        struct SmallNode *p_array_head = malloc((i + i % 2) * sizeof(struct SmallNode));  // Add i % 2 to have some portions not filling a whole 4KB page
        if (p_array_head == NULL) {
            fprintf(stderr, "malloc call in mem_test.c failed\n");
            exit(1);
        }
        arrays[i - 1] = p_array_head;
    }
    
    // Reads
    long int a;
    for (long int i = 2; i < num_nodes + 2; ++i) {
        for (long int j = 0; j < i; j += 8) {  // every 8th one for faster runtime
            a = arrays[i - 1][j].contents[3];
            for (long int k = 0; k < 5; ++k) {
                // Drain some time
                ++a;
            }
        }
        // a = arrays[i - 1][0].contents[3];
        // a = arrays[i - 1][1].contents[3];  // these first two usually are on the same 4 KB page
        // a = arrays[i - 1][i - 2].contents[3];
        // a = arrays[i - 1][i - 1].contents[3];  // these last two may or may not be on the same 4 KB page, depending on i
    }

    // Writes
    for (long int i = 2; i < num_nodes + 2; ++i) {
        for (long int j = 0; j < i; j += 8) {  // every 8th one for faster runtime
            arrays[i - 1][j].contents[250] = a + j;
        }
        // arrays[i - 1][0].contents[3] = a;
        // arrays[i - 1][1].contents[3] = a + 2;
        // arrays[i - 1][i - 2].contents[3] = a + 5;
        // arrays[i - 1][i - 1].contents[3] = a + 7;
        a++;  // have some changes for a bit more variability
    }

    SimRoiEnd();

    printf("------   mem_test program end   ------\n\n\n");
}