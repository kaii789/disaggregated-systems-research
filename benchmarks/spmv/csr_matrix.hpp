#pragma once

#include <algorithm>
#include <cassert>
#include <cstring>
#include <functional>
#include <iomanip>
#include <iostream>
#include <memory>

#include <omp.h>

#include "io/mmf.hpp"
#include "allocator.hpp"
#include "platforms.hpp"
#include "runtime.hpp"

using namespace std;
using namespace util;
using namespace util::io;
using namespace util::runtime;

namespace matrix {
namespace sparse {

// Forward declarations
template <typename IndexT, typename ValueT> class SparseMatrix;

template <typename IndexT, typename ValueT>
class CSRMatrix : public SparseMatrix<IndexT, ValueT> {
public:
  CSRMatrix() = delete;

  // Initialize CSR from an MMF file
  CSRMatrix(const string &filename, Platform platform = Platform::cpu)
      : platform_(platform), owns_data_(true)
  {
#ifdef _LOG_INFO
    std::cout << "[INFO]: using CSR format to store the sparse matrix..."
              << std::endl;
#endif
    MMF<IndexT, ValueT> mmf(filename);
    nrows_ = mmf.GetNrRows();
    ncols_ = mmf.GetNrCols();
    nnz_ = mmf.GetNrNonzeros();
    rowptr_ = (IndexT *)internal_alloc((nrows_ + 1) * sizeof(IndexT), platform_);
    colind_ = (IndexT *)internal_alloc(nnz_ * sizeof(IndexT), platform_);
    values_ = (ValueT *)internal_alloc(nnz_ * sizeof(ValueT), platform_);
    // Partitioning
    part_by_nrows_ = part_by_nnz_ = false;
    nthreads_ = omp_get_max_threads(); //get_threads(); cgiannoula
    row_split_ = nullptr;

    // Enforce first touch policy
    #pragma omp parallel num_threads(nthreads_)
    {
      #pragma omp for schedule(static)
      for (int i = 0; i < nrows_ + 1; i++) {
        rowptr_[i] = 0;
      }
      #pragma omp for schedule(static)
      for (int i = 0; i < nnz_; i++) {
        colind_[i] = 0;
        values_[i] = 0.0;
      }
    }

    auto iter = mmf.begin();
    auto iter_end = mmf.end();
    IndexT row_i = 0, val_i = 0, row_prev = 0;
    IndexT row, col;
    ValueT val;

    rowptr_[row_i++] = val_i;
    for (; iter != iter_end; ++iter) {
      // MMF returns one-based indices
      row = (*iter).row - 1;
      col = (*iter).col - 1;
      val = (*iter).val;
      assert(row >= row_prev);
      assert(row < nrows_);
      assert(col >= 0 && col < ncols_);
      assert(val_i < nnz_);

      if (row != row_prev) {
        for (IndexT i = 0; i < row - row_prev; i++) {
          rowptr_[row_i++] = val_i;
        }
        row_prev = row;
      }

      colind_[val_i] = (IndexT)col;
      values_[val_i] = val;
      val_i++;
    }

    rowptr_[row_i] = val_i;

    // More sanity checks.
    assert(row_i == nrows_);
    assert(val_i == nnz_);
  }

  // Initialize CSR from another CSR matrix (no ownership)
  CSRMatrix(IndexT *rowptr, IndexT *colind, ValueT *values, IndexT nrows,
            IndexT ncols, Platform platform = Platform::cpu)
    : platform_(platform), nrows_(nrows), ncols_(ncols), owns_data_(false)
  {
#ifdef _LOG_INFO
    std::cout << "[INFO]: using CSR format to store the sparse matrix..."
              << std::endl;
#endif
    rowptr_ = rowptr;
    colind_ = colind;
    values_ = values;
    nnz_ = rowptr_[nrows];
    // Partitioning
    part_by_nrows_ = part_by_nnz_ = part_by_ncnfls_ = false;
    nthreads_ = omp_get_max_threads(); //get_threads(); cgiannoula
    row_split_ = nullptr;
  }

  virtual ~CSRMatrix() {
    // If CSRMatrix was initialized using pre-defined arrays, we release
    // ownership.
    if (owns_data_) {
      internal_free(rowptr_, platform_);
      internal_free(colind_, platform_);
      internal_free(values_, platform_);
    } else {
      rowptr_ = nullptr;
      colind_ = nullptr;
      values_ = nullptr;
    }

    // Partitioning
    internal_free(row_split_, platform_);
  }

  virtual int nrows() const override { return nrows_; }
  virtual int ncols() const override { return ncols_; }
  virtual int nnz() const override { return nnz_; }

  virtual size_t size() const override {
    size_t size = 0;
    size += (nrows_ + 1) * sizeof(IndexT); // rowptr
    size += nnz_ * sizeof(IndexT);         // colind
    size += nnz_ * sizeof(ValueT);         // values
    if (part_by_nnz_)
      size += (nthreads_ + 1) * sizeof(IndexT); // row_split

    return size;
  }

  virtual inline Platform platform() const override { return platform_; }

  virtual bool tune(Kernel k, Tuning t) override {
    using placeholders::_1;
    using placeholders::_2;

    if (t == Tuning::None) {
      spmv_fn = bind(&CSRMatrix<IndexT, ValueT>::cpu_mv_vanilla, this, _1, _2);
      return false;
    } else if (t == Tuning::Nnz) {
      partition_by_nnz(nthreads_);
      spmv_fn = bind(&CSRMatrix<IndexT, ValueT>::cpu_mv_split_nnz, this, _1, _2);
    } else {
      partition_round(nthreads_);
      spmv_fn = bind(&CSRMatrix<IndexT, ValueT>::cpu_mv_split_round, this, _1, _2);
    }

    return true;
  }

  virtual void dense_vector_multiply(ValueT *__restrict y,
                                     const ValueT *__restrict x) override {
    spmv_fn(y, x);
  }

  // Export CSR internal representation
  IndexT *rowptr() const { return rowptr_; }
  IndexT *colind() const { return colind_; }
  ValueT *values() const { return values_; }

private:
  Platform platform_;
  int nrows_, ncols_, nnz_;
  bool owns_data_;
  IndexT *rowptr_;
  IndexT *colind_;
  ValueT *values_;
  // Partitioning
  bool part_by_nrows_, part_by_nnz_, part_by_ncnfls_;
  int nthreads_;
  int *row_split_;
  // Internal function pointer
  function<void(ValueT *__restrict, const ValueT *__restrict)> spmv_fn;

  /*
  * Preprocessing routines
  */
  void partition_by_nnz(int nthreads);
  void partition_round(int nthreads);

  /*
   * Sparse Matrix - Dense Vector Multiplication kernels
   */
  void cpu_mv_vanilla(ValueT *__restrict y, const ValueT *__restrict x);
  void cpu_mv_split_nnz(ValueT *__restrict y, const ValueT *__restrict x);
  void cpu_mv_split_round(ValueT *__restrict y, const ValueT *__restrict x);
};

template <typename IndexT, typename ValueT>
void CSRMatrix<IndexT, ValueT>::partition_by_nnz(int nthreads) {
#ifdef _LOG_INFO
  cout << "[INFO]: partitioning by number of nonzeros" << endl;
#endif

  if (!row_split_) {
    row_split_ =
        (IndexT *)internal_alloc((nthreads + 1) * sizeof(IndexT), platform_);
  }

  if (nthreads_ == 1) {
    row_split_[0] = 0;
    row_split_[1] = nrows_;
    part_by_nnz_ = true;
    return;
  }

  // Compute the matrix splits.
  int nnz_cnt = nnz_;
  int nnz_per_split = nnz_cnt / nthreads_;
  int curr_nnz = 0;
  int row_start = 0;
  int split_cnt = 0;
  int i;
  
  int min_nnz_per_thread = nnz_cnt;
  int max_nnz_per_thread = 0;
  float sum_nnz_per_thread = 0;  

  row_split_[0] = row_start;
  for (i = 0; i < nrows_; i++) {
    curr_nnz += rowptr_[i + 1] - rowptr_[i];
    // The number of rows assigned to each thread has to be a multiple 
    // of cache_line_size / precision (float/double). 
    // Each thread writes/"owns" a multiple of cache lines of the vector y.
    if ((curr_nnz >= nnz_per_split) && ((i + 1) % (CACHE_LINE / sizeof(ValueT)) == 0)) {
    //if ((curr_nnz >= nnz_per_split) && ((i + 1) % BLK_FACTOR == 0)) { // cgiannoula
    //if (curr_nnz >= nnz_per_split) { // default: assuming coherence
      row_start = i + 1;
      ++split_cnt;
      if (split_cnt <= nthreads)
	    row_split_[split_cnt] = row_start;

      if (min_nnz_per_thread > curr_nnz)
          min_nnz_per_thread = curr_nnz;

      if (max_nnz_per_thread < curr_nnz)
          max_nnz_per_thread = curr_nnz;

      sum_nnz_per_thread += curr_nnz;

      curr_nnz = 0;
    }
  }

  // Fill the last split with remaining elements
  if (curr_nnz < nnz_per_split && split_cnt <= nthreads) {
    row_split_[++split_cnt] = nrows_;

    // cgiannoula
    if (min_nnz_per_thread > curr_nnz)
        min_nnz_per_thread = curr_nnz;

    if (max_nnz_per_thread < curr_nnz)
        max_nnz_per_thread = curr_nnz;

    sum_nnz_per_thread += curr_nnz;

  }

  // If there are any remaining rows merge them in last partition
  if (split_cnt > nthreads_) {
    row_split_[nthreads_] = nrows_;
  }

  // If there are remaining threads create empty partitions
  for (int i = split_cnt + 1; i <= nthreads; i++) {
    row_split_[i] = nrows_;

    if (min_nnz_per_thread > 0)
        min_nnz_per_thread = 0;
  }

  part_by_nnz_ = true;


  cout << "[min_nnz_per_thread] : " << min_nnz_per_thread << endl;
  cout << "[max_nnz_per_thread] : " << max_nnz_per_thread << endl;
  cout << "[avg_nnz_per_thread] : " << sum_nnz_per_thread / nthreads << endl;
  cout << "[#threads with zero computation] : " << nthreads - split_cnt << endl;

}

template <typename IndexT, typename ValueT>
void CSRMatrix<IndexT, ValueT>::partition_round(int nthreads) {
#ifdef _LOG_INFO
  cout << "[INFO]: partitioning with round static scheduling" << endl;
#endif

  int i;
  int curr_nnz = 0;
  int min_nnz_per_thread = nnz_; 
  int max_nnz_per_thread = 0;
  float sum_nnz_per_thread = 0;  

  IndexT *nnz_per_thread = (IndexT *)internal_alloc((nthreads) * sizeof(IndexT), platform_);
  for (i = 0; i < nthreads; i++) {
    nnz_per_thread[i] = 0;
  }

  int block_factor = CACHE_LINE / sizeof(ValueT);

  int currRow = 0;
  int tid = 0;
  while (currRow < nrows_) {
    curr_nnz = 0;
    for (i = 0; i < block_factor && currRow + i < nrows_; ++i) {
      curr_nnz += rowptr_[currRow + i + 1] - rowptr_[currRow + i];
    }
    nnz_per_thread[tid%nthreads] += curr_nnz;
    currRow += i;
    tid++;
  }

  for (i = 0; i < nthreads; i++) {
    if (nnz_per_thread[i] < min_nnz_per_thread)
        min_nnz_per_thread = nnz_per_thread[i];

    if (nnz_per_thread[i] > max_nnz_per_thread)
        max_nnz_per_thread = nnz_per_thread[i];
    
    sum_nnz_per_thread += nnz_per_thread[i];
    //cout << "TID " << i << " [nnz_per_thread] : " << nnz_per_thread[i] << " " << nnz_ << endl;
  }

  cout << "[min_nnz_per_thread] : " << min_nnz_per_thread << endl;
  cout << "[max_nnz_per_thread] : " << max_nnz_per_thread << endl;
  cout << "[avg_nnz_per_thread] : " << sum_nnz_per_thread / nthreads << endl;

  internal_free(nnz_per_thread, platform_);
}


template <typename IndexT, typename ValueT>
void CSRMatrix<IndexT, ValueT>::cpu_mv_vanilla(ValueT *__restrict y,
                                               const ValueT *__restrict x) {
  #pragma omp parallel for schedule(static) num_threads(nthreads_)
  for (int i = 0; i < nrows_; ++i) {
    ValueT y_tmp = 0.0;

    //#pragma omp simd reduction(+: y_tmp)
    for (IndexT j = rowptr_[i]; j < rowptr_[i + 1]; ++j) {
      y_tmp += values_[j] * x[colind_[j]];
    }

    y[i] = y_tmp;
  }
}

template <typename IndexT, typename ValueT>
void CSRMatrix<IndexT, ValueT>::cpu_mv_split_nnz(ValueT *__restrict y,
                                                 const ValueT *__restrict x) {
  #pragma omp parallel num_threads(nthreads_)
  {
    int tid = omp_get_thread_num();
    //cout << "[TID] " << tid << "\n"; 

    for (IndexT i = row_split_[tid]; i < row_split_[tid + 1]; ++i) {
      register ValueT y_tmp = 0;

      //#pragma omp simd reduction(+: y_tmp)
      for (IndexT j = rowptr_[i]; j < rowptr_[i + 1]; ++j) {
#if defined(_PREFETCH) && defined(_INTEL_COMPILER)
        // T0: prefetch into L1, temporal with respect to all level caches 
        _mm_prefetch((const char *)&x[colind_[j + 16]], _MM_HINT_T2);
#endif
        y_tmp += values_[j] * x[colind_[j]];
      }

      // Reduction on y 
      y[i] = y_tmp;
    }
  }
}

template <typename IndexT, typename ValueT>
void CSRMatrix<IndexT, ValueT>::cpu_mv_split_round(ValueT *__restrict y,
                                                 const ValueT *__restrict x) {
  #pragma omp parallel num_threads(nthreads_)
  {
    int tid = omp_get_thread_num();
    //cout << "[TID] " << tid << "\n"; 
    int block_factor = CACHE_LINE / sizeof(ValueT);
    IndexT currRow = tid * block_factor;

    while (currRow < nrows_) {
      for (IndexT i = 0; i < block_factor && currRow + i < nrows_; ++i) {
        register ValueT y_tmp = 0;

        for (IndexT j = rowptr_[currRow + i]; j < rowptr_[currRow + i + 1]; ++j) {
#if defined(_PREFETCH) && defined(_INTEL_COMPILER)
          // T0: prefetch into L1, temporal with respect to all level caches 
          _mm_prefetch((const char *)&x[colind_[j + 16]], _MM_HINT_T2);
#endif
          y_tmp += values_[j] * x[colind_[j]];
        }

        // Reduction on y 
        y[currRow + i] = y_tmp;
      }

      currRow += nthreads_ * block_factor;
    }
  }

}

} // end of namespace sparse
} // end of namespace matrix
