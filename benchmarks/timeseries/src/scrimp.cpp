/*++++++++
  Written by Yan Zhu, Jan 2018.

  This is SCRIMP++.

  Details of the SCRIMP++ algorithm can be found at:
  Yan Zhu, Chin-Chia M.Yeh, Zachary Zimmerman, Kaveh Kamgar and Eamonn Keogh,
  "Solving Time Series Data Mining Problems at Scale with SCRIMP++", submitted to KDD 2018.

Usage: >> scrimpplusplus InputFileName SubsequenceLength stepsize
InputFileName: Name of the time series file
SubsequenceLength: Subsequence length m
stepsize: Step size ratio s/m. For all the experiments in the paper, stepsize is always set as 0.25.

example input:
>> scrimpplusplus ts_1000.txt 50 0.25

example output:
The code will generate two outputs.
SCRIMP_PLUS_PLUS_New_PreSCRIMP_MatrixProfile_and_Index_50_ts_1000.txt          This is the approximate matrix profile and matrix profile index generated after PreSCRIMP.
SCRIMP_PLUS_PLUS_New_MatrixProfile_and_Index_50_ts_1000.txt                    This is the final/exact matrix profile and matrix profile index, generated when the whole algorithm (PreSCRIMP+SCRIMP) is completed.

The first column of the output file is the matrix profile value.
The second column of the output file is the matrix profile index.
*/
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <limits>
#include <vector>
#include <algorithm>
#include <string>
#include <sstream>
#include <chrono>
#include <pthread.h>
#include "mprofile.h"

#include "cas_lock.h"
#include "cas_barrier.h"
#include "sim_api.h"

struct arg_struct {
    int start;
    int end;
    int tid;
#ifdef CUSTOM
    lock_t** locks;
    barrier_t* barrier;
#endif
#ifdef PTHREAD
    pthread_mutex_t **locks;
    pthread_barrier_t *barrier;
#endif

};




int bw_cnt = 0;
int completion_factor = 1;
int numThreads, exclusionZone;
int windowSize, timeSeriesLength, ProfileLength;
//double windowSize;
int* profileIndex;
double *AMean, *ASigma;
profile * prof;
std::vector<int> idx;
std::vector<double> A;

#ifdef CUSTOM
lock_t* lock;
lock_t** locks;
barrier_t* barrier;
#endif
#ifdef PTHREAD
pthread_mutex_t *lock;
pthread_mutex_t **locks;
pthread_barrier_t *barrier;
#endif



void preprocess()
{
    double* ACumSum   = new double[timeSeriesLength];
    double* ASqCumSum = new double[timeSeriesLength];
    double* ASum      = new double[ProfileLength];
    double* ASumSq    = new double[ProfileLength];
    double* ASigmaSq  = new double[ProfileLength];

    AMean  = new double[ProfileLength];
    ASigma = new double[ProfileLength];

    ACumSum[0]   = A[0];
    ASqCumSum[0] = A[0] * A[0];

    for (int i = 1; i < timeSeriesLength; i++)
    {
        ACumSum[i]   = A[i] + ACumSum[i - 1];
        ASqCumSum[i] = A[i] * A[i] + ASqCumSum[i - 1];
    }

    ASum[0] = ACumSum[windowSize - 1];
    ASumSq[0] = ASqCumSum[windowSize - 1];

    for (int i = 0; i < timeSeriesLength - windowSize; i++)
    {
        ASum[i + 1]   = ACumSum[windowSize + i] - ACumSum[i];
        ASumSq[i + 1] = ASqCumSum[windowSize + i] - ASqCumSum[i];
    }

    for (int i = 0; i < ProfileLength; i++)
    {
        AMean[i] = ASum[i] / windowSize;
        ASigmaSq[i] = ASumSq[i] / windowSize - AMean[i] * AMean[i];
        ASigma[i] = sqrt(ASigmaSq[i]);
    }

    delete ACumSum;
    delete ASqCumSum;
    delete ASum;
    delete ASumSq;
    delete ASigmaSq;
}

void* scrimp(void *th_args)
{
    struct arg_struct *my_data;
    my_data = (struct arg_struct *) th_args;
    int tid =  my_data->tid;

    int ri;
    double  distance, lastz, windowSizeDouble;
    windowSizeDouble = windowSize;

#ifdef CUSTOM
    barrier_wait(my_data->barrier, tid);
#endif
#ifdef PTHREAD
    pthread_barrier_wait(my_data->barrier);
#endif


    for (ri = my_data->start; ri < my_data->end; ri++)
    {
        //select a random diagonal
        int diag = idx[ri];
        lastz = 0;

        //calculate the dot product of every two time series values that ar diag away
        for (int j = diag; j < windowSize + diag; j++)
        {
            lastz += A[j] * A[j-diag];
        }

        //j is the column index, i is the row index of the current distance value in the distance matrix
        int j = diag, i;
        i = 0;
        //evaluate the distance based on the dot product
        distance = 2 * (windowSizeDouble - (lastz - windowSizeDouble * AMean[j] * AMean[i]) / (ASigma[j] * ASigma[i]));

        //update matrix profile and matrix profile index if the current distance value is smaller
#ifdef CUSTOM
        lock_acquire(my_data->locks[j], tid);
        lock_acquire(my_data->locks[i], tid);
#endif
#ifdef PTHREAD
        pthread_mutex_lock(my_data->locks[j]);
        pthread_mutex_lock(my_data->locks[i]);
#endif

        if (distance < prof[j].value)
        {
            prof[j].value = distance;
            prof[j].idx = i;
        }
        if (distance < prof[i].value)
        {
            prof[i].value = distance;
            prof[i].idx = j;
        }

#ifdef CUSTOM
        lock_release(my_data->locks[j], tid);
        lock_release(my_data->locks[i], tid);
#endif
#ifdef PTHREAD
        pthread_mutex_unlock(my_data->locks[j]);
        pthread_mutex_unlock(my_data->locks[i]);
#endif


        i = 1;

        for (j=diag+1; j<ProfileLength; j++)
        {
            lastz    = lastz + (A[j+windowSize-1] * A[i+windowSize-1]) - (A[j-1] * A[i-1]);
            distance = 2 * (windowSizeDouble - (lastz -  AMean[j]  * AMean[i] * windowSizeDouble) / (ASigma[j] * ASigma[i]));

#ifdef CUSTOM
            lock_acquire(my_data->locks[j], tid);
            lock_acquire(my_data->locks[i], tid);
#endif
#ifdef PTHREAD
            pthread_mutex_lock(my_data->locks[j]);
            pthread_mutex_lock(my_data->locks[i]);
#endif

            if (distance < prof[j].value)
            {
                prof[j].value = distance;
                prof[j].idx = i;
            }
            if (distance < prof[i].value)
            {
                prof[i].value = distance;
                prof[i].idx = j;
            }

#ifdef CUSTOM
            lock_release(my_data->locks[j], tid);
            lock_release(my_data->locks[i], tid);
#endif
#ifdef PTHREAD
            pthread_mutex_unlock(my_data->locks[j]);
            pthread_mutex_unlock(my_data->locks[i]);
#endif


            i++;
        }

    }
    return NULL;
}

int main(int argc, char* argv[])
{

    std::chrono::high_resolution_clock::time_point tprogstart, tstart, tend;
    std::chrono::duration<double> time_elapsed;

    // read time series and subsequence length (windowSize).
    std::fstream timeSeriesFile(argv[1], std::ios_base::in);

    windowSize = atoi(argv[2]);

    numThreads = atoi(argv[4]);

    completion_factor = atoi(argv[5]);


    std::cout << std::endl;
    std::cout << "############################################################" << std::endl;
    std::cout << "///////////////////////// SCRIMP ///////////////////////////" << std::endl;
    std::cout << "############################################################" << std::endl;
    std::cout << std::endl;

    std::cout << "[>>] Reading File..." << std::endl;
    tstart = std::chrono::high_resolution_clock::now();
    tprogstart = tstart;

    std::stringstream outfilename_num;
    outfilename_num << windowSize;
    std::string outfilenamenum = outfilename_num.str();
    std::string inputfilename = argv[1];
    std::string outfilename = "SCRIMP_PLUS_PLUS_New_MatrixProfile_and_Index_" + outfilenamenum + "_" + inputfilename;

    loadTimeSeriesFromFile(inputfilename, A, timeSeriesLength);


    tend = std::chrono::high_resolution_clock::now();
    time_elapsed = tend - tstart;
    std::cout << "[OK] Read File Time: " << std::setprecision(std::numeric_limits<double>::digits10 + 2) << time_elapsed.count() << " seconds." << std::endl;

    // set exclusion zone
    exclusionZone = windowSize / 4;
    // set Matrix Profile Length
    ProfileLength = timeSeriesLength - windowSize + 1;

    std::cout << std::endl;
    std::cout << "------------------------------------------------------------" << std::endl;
    std::cout << "************************** INFO ****************************" << std::endl;
    std::cout << std::endl;
    std::cout << " Time series length: " << timeSeriesLength << std::endl;
    std::cout << " Window size:        " << windowSize       << std::endl;
    std::cout << " Exclusion zone:     " << exclusionZone    << std::endl;
    std::cout << " Profile length:     " << timeSeriesLength << std::endl;
    std::cout << " Number of threads:  " << numThreads       << std::endl;
    std::cout << " Completion factor:  " << (double) 100 / completion_factor  << " %"<<std::endl;
    std::cout << std::endl;
    std::cout << "------------------------------------------------------------" << std::endl;
    std::cout << std::endl;

    int grps;
    if (numThreads <= 16)
        grps = 1;
    else if (numThreads <= 32)
        grps = 2;
    else if (numThreads <= 48)
        grps = 3;
    else if (numThreads <= 64)
        grps = 4;
    else if (numThreads <= 128)
        grps = 4;



#ifdef CUSTOM
    locks = (lock_t **) malloc(ProfileLength* sizeof(lock_t *));
    for (int i=0; i<ProfileLength; i++)
        locks[i] = lock_init(numThreads);

    barrier_t *barrier = barrier_init(numThreads);
#endif
#ifdef PTHREAD
    locks = (pthread_mutex_t **) malloc((ProfileLength) * sizeof(pthread_mutex_t *));
    for(int i=0; i<ProfileLength; i++) {
        locks[i] = (pthread_mutex_t *) malloc(sizeof(pthread_mutex_t));
        pthread_mutex_init(locks[i], NULL);
    }
    barrier = (pthread_barrier_t *) malloc(sizeof(pthread_barrier_t));
    pthread_barrier_init(barrier, NULL, numThreads);
#endif 

    // cgiannoula
    int groups;
    if (numThreads <= 16)
        groups = 1;
    else if (numThreads <= 32)
        groups = 2;
    else if (numThreads <= 48)
        groups = 3;
    else if (numThreads <= 64)
        groups = 4;
    else if (numThreads <= 128)
        groups = 4;


    std::cout << "[>>] Preprocessing..." << std::endl;
    // preprocess, statistics, get the mean and standard deviation of every subsequence in the time series

    tstart = std::chrono::high_resolution_clock::now();
    preprocess();
    tend = std::chrono::high_resolution_clock::now();
    time_elapsed = tend - tstart;
    std::cout << "[OK] Preprocess Time:         " << std::setprecision(std::numeric_limits<double>::digits10 + 2) << time_elapsed.count() << " seconds." << std::endl;


    std::cout << "[>>] Initializing Profile..." << std::endl;
    tstart = std::chrono::high_resolution_clock::now();

    //Initialize Matrix Profile and Matrix Profile Index
    prof      = new  profile [ProfileLength];

    for (int i=0; i<ProfileLength; i++)
    {
        prof[i].value = std::numeric_limits<double>::infinity();
        prof[i].idx = 0;
    }
    //Random shuffle the computation order of the diagonals of the distance matrix
    idx.clear();
    for (int i = exclusionZone+1; i < ProfileLength; i++)
        idx.push_back(i);
    std::random_shuffle(idx.begin(), idx.end());


    tend = std::chrono::high_resolution_clock::now();
    time_elapsed = tend - tstart;
    std::cout << "[OK] Initialize Profile Time: " << std::setprecision(std::numeric_limits<double>::digits10 + 2) << time_elapsed.count() << " seconds." << std::endl;


    std::cout << "[>>] Performing SCRIMP..." << std::endl;

    tstart = std::chrono::high_resolution_clock::now();
    pthread_t threads[numThreads];
    void *status;
    pthread_attr_t attr;
    pthread_attr_init(&attr);
    pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_JOINABLE);

    struct arg_struct td[numThreads];

    int size_work = (idx.size() / numThreads) / completion_factor;
    int over_work = idx.size() % numThreads;



    for (int thread = 0; thread < numThreads; thread++)
    {
        td[thread].start = thread * size_work;
        //td[thread].end   = td[thread].start + size_work - 1;
        td[thread].end   = td[thread].start + size_work;
        if(thread == numThreads - 1) td[thread].end += over_work;
        td[thread].tid = thread;
        td[thread].locks = locks;
        td[thread].barrier = barrier;
    }

    //  SCRIMP 
    struct timespec requestStart, requestEnd;
    clock_gettime(CLOCK_REALTIME, &requestStart);

    SimRoiStart();


    for (int thread = 1; thread < numThreads; thread++)
    {
        pthread_create (&threads[thread], &attr, scrimp, (void*)&td[thread]);
    }

    scrimp((void*) &td[0]);//master thread initializes itself

    // free attribute and wait for the other threads
    //pthread_attr_destroy(&attr);
    // join the threads
    for (int thread = 1; thread < numThreads; thread++)
    {
        pthread_join(threads[thread], &status);
    }

    printf("\nThreads Joined!\n");

    if (SimInSimulator()) {
        printf("API Test: Running in the simulator\n"); fflush(stdout);
    } else {
        printf("API Test: Not running in the simulator\n"); fflush(stdout);
    }

    SimRoiEnd();

    clock_gettime(CLOCK_REALTIME, &requestEnd);
    double accum = ( requestEnd.tv_sec - requestStart.tv_sec ) + ( requestEnd.tv_nsec - requestStart.tv_nsec ) / 1000000000;
    printf( "\nTime Taken:\n%lf seconds\n", accum );


    tend = std::chrono::high_resolution_clock::now();
    time_elapsed = tend - tstart;
    std::cout << "[OK] SCRIMP Time:             " << std::setprecision(std::numeric_limits<double>::digits10 + 2) << time_elapsed.count() << " seconds." << std::endl;

    /*
       std::cout << "[>>] Saving Profile..." << std::endl;
       tstart = std::chrono::high_resolution_clock::now();

       saveProfileToFile(outfilename.c_str(), prof, timeSeriesLength, windowSize);

       tend = std::chrono::high_resolution_clock::now();
       time_elapsed = tend - tstart;

       std::cout << "[OK] Save Profile Time:       " << std::setprecision(std::numeric_limits<double>::digits10 + 2) << time_elapsed.count() << " seconds." << std::endl;
       */

    time_elapsed = tend - tprogstart;
    std::cout << "[OK] Total Time:              " << std::setprecision(std::numeric_limits<double>::digits10 + 2) << time_elapsed.count() << " seconds." << std::endl;
    std::cout << std::endl;

    delete prof;
    delete profileIndex;
    delete locks;
    delete AMean;
    delete ASigma;

}
