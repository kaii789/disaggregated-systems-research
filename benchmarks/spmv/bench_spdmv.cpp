
#include <iostream>
#include <string> 
#include <cmath>
#include <cstdlib>
#include <time.h>
#include <omp.h>
#include <sys/time.h>
#include <stdlib.h>
#include <stdio.h>

#include "platforms.hpp"
#include "sparse_matrix.hpp"
#include "sparse_kernels.hpp"

/// Sniper Hooks
#include "sim_api.h"

using namespace std;
using namespace util;
using namespace matrix::sparse;
using namespace kernel::sparse;

typedef int INDEX;
#ifdef _USE_DOUBLE
typedef double VALUE;
#else
typedef float VALUE;
#endif

int main(int argc, char *argv[])
{

    if(argc != 4){
        std::cerr << "Usage: " << argv[0] << " require Matrix Size"
            << "\t-h,--help\t\tShow this help message\n"
            << "\t,--matrix Matrix\tSpecify Matrix"
            << "\t,--format Format\tSpecify Matrix Format"
            << "\t,--nthreads Number of threads\tSpecify Number of Threads"
            << std::endl;
        return 1;
    }

    char *matrix = argv[1];
    int fmt = atoi(argv[2]);
    int thr = atoi(argv[3]);
    cout << "Matrix: " << matrix << "\n";
    cout << "Format: " << fmt << "\n";
    cout << "Threads: " << thr << "\n";

    omp_set_dynamic(0);
    omp_set_num_threads(thr);
#pragma omp parallel num_threads(thr)
    {
//        cout << "Hello! " << omp_get_thread_num() << "\n";
    }

    const string mmf_file(argv[1]);

    string format_string;
    Format format = Format::none;
    switch (fmt) {
        case 0: {
                    format = Format::coo;
                    format_string = "COO";
                    break;
                }
        case 1: {
                    format = Format::csr;
                    format_string = "CSR";
                    break;
                }
    }

    // Load a sparse matrix from an MMF file
    void *mat = nullptr;
    int nrows = 0, ncols = 0, nnz = 0;

    SparseMatrix<INDEX, VALUE> *tmp = SparseMatrix<INDEX, VALUE>::create(mmf_file, format);
    nrows = tmp->nrows();
    ncols = tmp->ncols();
    nnz = tmp->nnz();
    mat = (void *)tmp;


    // Prepare vectors
    random_device rd;
    mt19937 gen(rd());
    uniform_real_distribution<> dis_val(0.01, 0.42);

    VALUE *y = (VALUE *)internal_alloc(nrows * sizeof(VALUE));
#pragma omp parallel for schedule(static)
    for (int i = 0; i < nrows; i++) {
        y[i] = 0.0;
    }

    VALUE *x = (VALUE *)internal_alloc(ncols * sizeof(VALUE));
#pragma omp parallel for schedule(static)
    for (int i = 0; i < ncols; i++) {
        x[i] = dis_val(gen);
    }

    double compute_time = 0.0, preproc_time = 0.0, tstart = 0.0, tstop = 0.0,
           gflops = 0.0;    

    SparseMatrix<INDEX, VALUE> *A = (SparseMatrix<INDEX, VALUE> *)mat;

    tstart = omp_get_wtime();
    SpDMV<INDEX, VALUE> spdmv(A, Tuning::Nnz);
    //SpDMV<INDEX, VALUE> spdmv(A, Tuning::Round);
    tstop = omp_get_wtime();
    preproc_time = tstop - tstart;

    // Warm up run
    unsigned int loops = 1;
    for (size_t i = 0; i < 0; i++)
        spdmv(y, nrows, x, ncols);

    // Benchmark run
    tstart = omp_get_wtime();

    SimRoiStart();
 
    for (size_t i = 0; i < loops; i++) {
        spdmv(y, nrows, x, ncols);
    }

    if (SimInSimulator()) {
        cout << "API Test: Running in the simulator" << endl;
    } else {
        cout << "API Test: Not Running in the simulator" << endl;
    }

    SimRoiEnd();


    tstop = omp_get_wtime();
    compute_time = tstop - tstart;

    gflops = ((double)loops * 2 * nnz * 1.e-9) / compute_time;

    #pragma omp parallel
    {
        int tid = omp_get_thread_num();
        if (tid == 0)
            cout << setprecision(4) << "matrix: " << basename(mmf_file.c_str())
                << " format: " << format_string << " preproc(sec): " << preproc_time
                << " t(sec): " << compute_time / loops << " gflops/s: " << gflops
                << " threads: " << omp_get_num_threads()
                << " size(MB): " << A->size() / (float)(1024 * 1024) << endl;
    }

    // Cleanup
    delete A;

    return 0;
}

