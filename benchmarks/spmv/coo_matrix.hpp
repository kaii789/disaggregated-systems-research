#pragma once

#include <cassert>
#include <cstring>
#include <functional>
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

// Formward declarations
template <typename IndexT, typename ValueT> class SparseMatrix;

template <typename IndexT, typename ValueT>
class COOMatrix : public SparseMatrix<IndexT, ValueT> {
public:
  COOMatrix() = delete;

  // Initialize COOMatrix from an MMF file
  COOMatrix(const std::string &filename, Platform platform = Platform::cpu)
      : platform_(platform), nthreads_(omp_get_max_threads()), owns_data_(true) {
      //: platform_(platform), nthreads_(get_threads()), owns_data_(true) { cgiannoula
#ifdef _LOG_INFO
    std::cout << "[INFO]: using COO format to store the sparse matrix..."
              << std::endl;
#endif
    MMF<IndexT, ValueT> mmf(filename);
    nrows_ = mmf.GetNrRows();
    ncols_ = mmf.GetNrCols();
    nnz_ = mmf.GetNrNonzeros();
    rowind_ = (IndexT *)internal_alloc(nnz_ * sizeof(IndexT), platform_);
    colind_ = (IndexT *)internal_alloc(nnz_ * sizeof(IndexT), platform_);
    values_ = (ValueT *)internal_alloc(nnz_ * sizeof(ValueT), platform_);

    auto iter = mmf.begin();
    auto iter_end = mmf.end();
    IndexT idx = 0;
    for (; iter != iter_end; ++iter) {
      // MMF returns one-based indices
      rowind_[idx] = (*iter).row - 1;
      colind_[idx] = (*iter).col - 1;
      values_[idx++] = (*iter).val;
    }

    assert(idx == nnz_);
  }

  // Initialize COOMatrix from another COOMatrix matrix (no ownership)
  COOMatrix(IndexT *rowind, IndexT *colind, ValueT *values, IndexT nrows,
            IndexT ncols, Platform platform = Platform::cpu)
      : platform_(platform), nrows_(nrows), ncols_(ncols), owns_data_(false)
  {
#ifdef _LOG_INFO
    std::cout << "[INFO]: using COO format to store the sparse matrix..."
              << std::endl;
#endif
    rowind_ = rowind;
    colind_ = colind;
    values_ = values;
    nnz_ = rowind_[nrows];
  }

  virtual ~COOMatrix() {
    // If COOMatrix was initialized using pre-defined arrays, we release
    // ownership.
    if (owns_data_) {
      internal_free(rowind_, platform_);
      internal_free(colind_, platform_);
      internal_free(values_, platform_);
    } else {
      rowind_ = nullptr;
      colind_ = nullptr;
      values_ = nullptr;
    }
  }

  virtual int nrows() const override { return nrows_; }
  virtual int ncols() const override { return ncols_; }
  virtual int nnz() const override { return nnz_; }

  virtual size_t size() const override {
    size_t size = nnz_ * sizeof(IndexT); // rowind
    size += nnz_ * sizeof(IndexT);       // colind
    size += nnz_ * sizeof(ValueT);       // values
    return size;
  }

  virtual inline Platform platform() const override { return platform_; }

  virtual bool tune(Kernel k, Tuning t) override {
    using placeholders::_1;
    using placeholders::_2;
    spmv_fn = bind(&COOMatrix<IndexT, ValueT>::cpu_mv_vanilla, this, _1, _2);
    return false;
  }

  virtual void dense_vector_multiply(ValueT *__restrict y,
                                     const ValueT *__restrict x) override {
    spmv_fn(y, x);
  }

private:
  Platform platform_;
  int nthreads_;
  int nrows_, ncols_, nnz_;
  bool owns_data_;
  IndexT *rowind_;
  IndexT *colind_;
  ValueT *values_;
  function<void(ValueT *__restrict, const ValueT *__restrict)> spmv_fn;

  /*
   * Sparse Matrix - Dense Vector Multiplication kernels
   */
  void cpu_mv_vanilla(ValueT *__restrict y, const ValueT *__restrict x);
};

template <typename IndexT, typename ValueT>
void COOMatrix<IndexT, ValueT>::cpu_mv_vanilla(ValueT *__restrict y,
                                               const ValueT *__restrict x) {
  memset(y, 0.0, nrows_ * sizeof(ValueT));
#ifdef _INTEL_COMPILER
  __assume_aligned(y, 64);
  __assume_aligned(x, 64);
#endif
  #pragma omp parallel for schedule(static) num_threads(nthreads_)
  for (IndexT i = 0; i < nnz_; i++) {
    y[rowind_[i]] += values_[i] * x[colind_[i]];
  }
}

} // end of namespace sparse
} // end of namespace matrix
