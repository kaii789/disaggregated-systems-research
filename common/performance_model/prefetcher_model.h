#ifndef __PREFETCHER_MODEL_H__
#define __PREFETCHER_MODEL_H__

#include "fixed_types.h"
#include "subsecond_time.h"

#include <vector>

class PrefetcherModel
{
   public:
      PrefetcherModel() {}
      virtual ~PrefetcherModel() {}

      virtual void pagePrefetchCandidates(UInt64 current_phys_page, std::vector<UInt64>& prefetch_candidates) = 0;

      static PrefetcherModel* createPrefetcherModel(UInt32 page_size);
};

#endif /* __PREFETCHER_MODEL_H__ */
