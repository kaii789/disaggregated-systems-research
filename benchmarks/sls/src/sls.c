#define _GNU_SOURCE

/**
 * Christina Giannoula
 * cgiannoula
 * christina.giann@gmail.com
 */

/**
 * @file dlrm.c
 * @brief Host Application Source File for SLS Operation
 * Tables are stored as: table_size (rows) x feature_size (columns)
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>
#include <getopt.h>
#include <assert.h>
#include <inttypes.h>

#include "sim_api.h"

#include "timer.h"

// Data type
#define T uint32_t

#define PRINT 0


/*
 * @brief CSR format for SLS query
 */
struct CSRfrmt {
    uint32_t *batchptr;
    uint32_t *poolindx;
};

/*
 * Global variables
 */
uint32_t ntables;
uint32_t tbl_sizes[100];
uint32_t feature_size;
uint32_t nbatches;
uint32_t pooling;
uint32_t mini_batch_size;
struct CSRfrmt **batch_queries; // 2D: nbatches * ntables * struct CSRfrmt
float *tables; // 3D: ntables * tbl_sizes[i] * feature_size
float *output_host; // 4D: nbatches * ntables * mini_batch_size * feature_size

/**
 * @brief Trim a character in a string
 */
char *trimstr(char *str, int *end_tbl) {
    char *end;

    // Trim leading space
    while(str[0] == '[') str++;

    //if(*str == 0)  // All spaces?
    //    return str;

    // Trim trailing space
    end = str + strlen(str) - 1;
    // Trim comma and brackets
    while(end > str && end[0] == '\n') end--;
    while(end > str && end[0] == ',') end--;
    while(end > str && end[0] == ']') {
        end--;
        *end_tbl = true;
    }
    while(end > str && end[0] == ',') end--;

    // Write new null terminator character
    end[1] = '\0';

    return str;
}

/** 
 * @brief read SLS data from input fileName
 * @param filename to read SLS data
 */
static void read_SLSdata(const char* fileName) {
    FILE *fp = fopen(fileName, "r");
    char *line;
    char *token, *rest_token;
    char *splt_token, *rest_splt_token;
    line = (char *) malloc(500000 * sizeof(char));
    rest_token = (char *) malloc(500000 * sizeof(char));
    int done = false, indices = false, end_tbl = false;
    uint32_t batch_id=0; 
    uint32_t min_batch=0;

    while(fgets(line, 500000, fp) != NULL) {
	//printf("%s", line);
        token = strtok_r(line, " ", &rest_token);
        //printf("token %s\n", token);

        if (done == false) {
            done = true;

            while (token != NULL) {
                //printf("token %s\n", token);
                if (strstr(token, "--mini-batch-size") != NULL) {
                    splt_token = strtok_r(token, "=", &rest_splt_token);
                    splt_token = strtok_r(NULL, "=", &rest_splt_token);
                    //printf("splt_token %s %s ", splt_token, token);
                    min_batch = atoi(splt_token); 
                    mini_batch_size = min_batch;
                } else if (strstr(token, "--num-batches") != NULL) {
                    splt_token = strtok_r(token, "=", &rest_splt_token);
                    splt_token = strtok_r(NULL, "=", &rest_splt_token);
                    //printf("splt_token %s %s ", splt_token, token);
                    nbatches = atoi(splt_token);
                } else if (strstr(token, "--arch-sparse-feature-size") != NULL) {
                    splt_token = strtok_r(token, "=", &rest_splt_token);
                    splt_token = strtok_r(NULL, "=", &rest_splt_token);
                    //printf("splt_token %s %s ", splt_token, token);
                    feature_size = atoi(splt_token);
                } else if (strstr(token, "--arch-embedding-size") != NULL) {
                    splt_token = strtok_r(token, "=", &rest_splt_token);
                    splt_token = strtok_r(NULL, "=", &rest_splt_token);
                    splt_token = strtok_r(splt_token, "-", &rest_splt_token);
                    unsigned int tbls = 0;
                    while(splt_token != NULL) {
                        tbl_sizes[tbls] = atoi(splt_token);
                        tbls++;
                        splt_token = strtok_r(NULL, "-", &rest_splt_token);
                    }
                    ntables = tbls;
                    //printf("splt_token %s %s tbls %d ", splt_token, token, tbls);

                    // Allocate batch queries
                    batch_queries = (struct CSRfrmt **) malloc(nbatches * sizeof(struct CSRfrmt *));
                    for (int i=0; i < nbatches; i++) {
                        batch_queries[i] = (struct CSRfrmt *) malloc(ntables * sizeof(struct CSRfrmt));
                    }
                } else if (strstr(token, "--num-indices-per-lookup=") != NULL) { // FIXME works only with fixed pooling size !
                    splt_token = strtok_r(token, "=", &rest_splt_token);
                    splt_token = strtok_r(NULL, "=", &rest_splt_token);
                    //printf("splt_token %s %s ", splt_token, token);
                    pooling = atoi(splt_token);
                    for (int i=0; i < nbatches; i++) {
                        for(int j=0; j < ntables; j++) {
                            // Assuming batch size is always an even number !
                            batch_queries[i][j].batchptr = (uint32_t *) malloc((min_batch + 2) * sizeof(uint32_t));
                            // Allocate the worst case
                            batch_queries[i][j].poolindx = (uint32_t *) malloc(pooling * min_batch * sizeof(uint32_t));
                        }
                    }
                }
                token = strtok_r(NULL, " ", &rest_token);
            }
        } else if ((strstr(token, "\n") == NULL) && (strstr(token, "mini-batch") == NULL)) {
            if (indices == false) { // Read batch ptrs
                for (int i=0; i < ntables; i++) 
                    for (int j=0; j < min_batch + 1; j++) {
                        //printf("token row %s ", trimstr(token));
                        batch_queries[batch_id][i].batchptr[j] = atoi(trimstr(token, &end_tbl));
                        end_tbl = false;
                        token = strtok_r(NULL, " ", &rest_token);
                    }
                indices = true;
            } else { // Read pool indices
                int i = 0;
                int j = 0;
                while (token != NULL) {
                    //printf("token indices %s %s ", token, trimstr(token, &end_tbl));
                    int indx = atoi(trimstr(token, &end_tbl));
                    // printf("indx %d %d %d %d", indx, batch_id, i, j);
                    batch_queries[batch_id][i].poolindx[j] = indx;
                    if (end_tbl == true) {
                        i++;
                        j = 0;
                    } else {
                        j++;
                    }

                    end_tbl = false;
                    token = strtok_r(NULL, " ", &rest_token);
                }
                indices = false;
                batch_id++;
                if (batch_id == 1000) {
                    free(line);
                    fclose(fp);
                    return;
                }
            }
        }
    }

    //printf("\n");
    free(line);
    fclose(fp);
}

/*
 * @brief Deallocate batch queries
 */
static void free_batch_queries() {

    unsigned int b, t;
    for (b = 0; b < nbatches; b++) {
        for (t = 0; t < ntables; t++) {
            free(batch_queries[b][t].batchptr);
            free(batch_queries[b][t].poolindx);
        }
        free(batch_queries[b]);
    }

    free(batch_queries);
}

/*
 * @brief Iterate over SLS data 
 */
static void print_SLSdata() {
    unsigned int b, t, r, p, f;
    printf("%d Tables with the following size, having %d feature:\n", ntables, feature_size);
    for (int t = 0; t < ntables; t++)
        printf("%d ", tbl_sizes[t]);
    printf("\n");

    for (b = 0; b < nbatches; b++) {
        printf("Batch %d:\n", b);
        for (t = 0; t < ntables; t++) {
            printf("Table %d:\n", t);
            for (r = 0; r < mini_batch_size; r++){
                printf("Mini-Batch %d (%d %d):", r, batch_queries[b][t].batchptr[r], batch_queries[b][t].batchptr[r+1]);
                for (p = batch_queries[b][t].batchptr[r]; p < batch_queries[b][t].batchptr[r+1]; p++)
                    printf("p %d %d ", r, batch_queries[b][t].poolindx[p]);
            }
            printf("\n");
        }
        printf("\n\n");
    }

    long long int table_offset = 0;
    for (t = 0; t < ntables; t++) {
        printf("Table %d:\n", t);
        for (r = 0; r < tbl_sizes[t]; r++) {
            for (f = 0; f < feature_size; f++) {
                printf("%lf ", tables[table_offset + r * feature_size + f]);
            }
            printf("\n");
        }
        table_offset += tbl_sizes[t] * feature_size;
        printf("\n");
    }
}

/*
 * @brief Compute the output to host CPU
 */
static void SLS_host() {

    unsigned int b, t, r, p, f;
    for (b = 0; b < nbatches; b++) {
        long long int table_offset = 0;
        for (t = 0; t < ntables; t++) {
            for (r = 0; r < mini_batch_size; r++){
                for (p = batch_queries[b][t].batchptr[r]; p < batch_queries[b][t].batchptr[r+1]; p++) {
                    for (f = 0; f < feature_size; f++) {
                        output_host[b * ntables * mini_batch_size * feature_size + t * mini_batch_size * feature_size + r * feature_size + f] += tables[table_offset + batch_queries[b][t].poolindx[p] * feature_size + f];
                    }
                }
                //printf("mini-batch %d %lf \n", r, output_host[b * ntables * mini_batch_size * feature_size + t * mini_batch_size * feature_size + r * feature_size]);
            }
            table_offset += tbl_sizes[t] * feature_size;
        }
    }
}


// Params ---------------------------------------------------------------------
typedef struct Params {
    char* fileName;
    unsigned int   n_warmup;
    unsigned int   n_reps;
} Params;


void usage() {
    fprintf(stderr,
            "\nUsage:  ./program [options]"
            "\n"
            "\nGeneral options:"
            "\n    -h        help"
            "\n    -w <W>    # of untimed warmup iterations (default=1)"
            "\n    -e <E>    # of timed repetition iterations (default=3)"
            "\n"
            "\nBenchmark-specific options:"
            "\n    -f <F>    Input file name (default=data/model1_sls_small.in"
            "\n");
}


struct Params input_params(int argc, char **argv) {
    struct Params p;
    p.fileName      = "../sls_inputs/model1_sls_small.in";
    p.n_warmup      = 0;
    p.n_reps        = 1;

    int opt;
    while((opt = getopt(argc, argv, "hf:w:e:")) >= 0) {
        switch(opt) {
            case 'h':
                usage();
                exit(0);
                break;
            case 'f': p.fileName      = optarg; break;
            case 'w': p.n_warmup      = atoi(optarg); break;
            case 'e': p.n_reps        = atoi(optarg); break;
            default:
                      fprintf(stderr, "\nUnrecognized option!\n");
                      usage();
                      exit(0);
        }
    }

    return p;
}


/**
 * @brief Main of the Host Application.
 */
int main(int argc, char **argv) {

    struct Params p = input_params(argc, argv);

    unsigned int i;
    double cc = 0;
    double cc_min = 0;

    // Initialize input data 
    read_SLSdata(p.fileName);
    printf("Read Input: OK\n");

    // Initialize tables
    uint32_t table_sizes = 0;
    for (uint32_t t = 0; t < ntables; t++) {
        table_sizes += tbl_sizes[t];
    }

    // Initialize tables with random values
    tables = (float *) malloc(table_sizes * feature_size * sizeof(float));
    long long int table_offset = 0;
    for (uint32_t t = 0; t < ntables; t++) {
        for (uint32_t r = 0; r < tbl_sizes[t]; r++) {
            for (uint32_t f = 0; f < feature_size; f++) {
                tables[table_offset + r * feature_size + f] = (float) (rand() % 256); // FIXME Switch to Integers ?
                //printf("float %lf ", tables[table_offset + r * feature_size + f]);
            }
        }
        table_offset += tbl_sizes[t] * feature_size;
    }

    // Print all data
    //print_SLSdata();

    // Allocate arrays for output
    output_host = (float *) calloc(nbatches * ntables * mini_batch_size * feature_size, sizeof(float));

    // Timer
    Timer timer;

    SimRoiStart();

    for (unsigned int rep = 0; rep < p.n_warmup + p.n_reps; rep++) {

        // Compute output on CPU (performance comparison and verification purposes)
        if (rep >= p.n_warmup)
            start(&timer, 0, rep - p.n_warmup);
        SLS_host(); 
        if (rep >= p.n_warmup)
            stop(&timer, 0);
    }

    if (SimInSimulator()) {
        printf("API Test: Running in the simulator\n");
    } else {
        printf("API Test: Not Running in the simulator\n");
    }

    SimRoiEnd();


    // Print timing results
    printf("\n");
    printf("CPU ");
    print(&timer, 0, p.n_reps);
    printf("\n\n");

    free_batch_queries();
    free(tables);
    free(output_host);

    return 0;
}
