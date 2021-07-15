#ifndef __PREFETCHER_MODEL_H__
#define __PREFETCHER_MODEL_H__

#include "fixed_types.h"
#include "subsecond_time.h"

class PrefetcherModel
{
   public:
      PrefetcherModel() {}
      virtual ~PrefetcherModel() {}

      virtual UInt64 pagePrefetchCandidate(UInt64 current_phys_page) = 0;

      static PrefetcherModel* createPrefetcherModel(UInt32 page_size);
};

#endif /* __PREFETCHER_MODEL_H__ */
