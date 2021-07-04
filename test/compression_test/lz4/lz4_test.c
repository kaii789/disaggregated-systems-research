#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <sys/types.h>
#include <pthread.h>
#include <lz4.h>


int main(int argc, char** argv)
{
    float *in;
    float *out;
    int size = atoi(argv[1]);

    srand((time(0)));

    in = (float *) malloc(size * sizeof(float));
    out = (float *) malloc(size * sizeof(float));

    
    for(int i=0; i < size; i++) {
        in[i] = (float)rand()/(float)(RAND_MAX);
    }
 
    /*
#if INT        
    srand(time(NULL));
#endif
    for(uint64_t i=0; i < size / 2; i++) {
#if INT        
        in[4096 + i] = (((int)rand())/((int)(RAND_MAX/1000000))+2000);
#else
        in[4096 + i] = (float) (((float)rand())/((float)(RAND_MAX/1)));
#endif
    }
    */ 
    
    
    clock_t begin = clock();
    int compressed_size = LZ4_compress_default((char *) in, (char *) out, size * sizeof(float), size * sizeof(float));
    clock_t end = clock();
    double compression_latency = (double)(end - begin) / CLOCKS_PER_SEC;

    printf("compressed page %d compression ratio %lf compression latency %lf\n", compressed_size, (float) (size * sizeof(float)) / (float) compressed_size, compression_latency);
    
    /* 
    clock_t begin = clock();
    int compressed_size = LZ4_compress_default((char *) in, (char *) out, size / 2 * sizeof(float), size / 2 * sizeof(float));
    clock_t end = clock();
    double compression_latency = (double)(end - begin) / CLOCKS_PER_SEC;

    printf("compressed page %d compression ratio %lf compression latency %lf\n", compressed_size, (float) (size / 2 * sizeof(float)) / (float) compressed_size, compression_latency);

    begin = clock();
    compressed_size = LZ4_compress_default((char *) &in[size / 2], (char *) out, size / 2 * sizeof(float), size / 2 * sizeof(float));
    end = clock();
    compression_latency = (double)(end - begin) / CLOCKS_PER_SEC;

    printf("compressed page %d compression ratio %lf compression latency %lf\n", compressed_size, (float) (size / 2 * sizeof(float)) / (float) compressed_size, compression_latency);
    */



    begin = clock();
    LZ4_decompress_safe((char *) out, (char *) in, compressed_size, size * sizeof(float));
    end = clock();
    double decompression_latency = (double)(end - begin) / CLOCKS_PER_SEC;
    printf("compressed page %d compression ratio %lf decompression latency %lf\n", compressed_size, (float) (size * sizeof(float)) / (float) compressed_size, decompression_latency);
    

    /*
    float *test = (float *) calloc(size * sizeof(float), 8);

    begin = clock();
    compressed_size = LZ4_compress_default((char *) test, (char *) out, 4096 * sizeof(float), 4096 * sizeof(float));
    end = clock();
    compression_latency = (double)(end - begin) / CLOCKS_PER_SEC;

    printf("compressed page %d compression ratio %lf compression latency %lf\n", compressed_size, (float) (4096 * sizeof(float)) / (float) compressed_size, compression_latency);
    */

   
    free(in);
    free(out);
    return 0;
}
 
