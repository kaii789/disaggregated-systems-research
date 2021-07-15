#ifndef __PREFETCHER_MODEL_NEXT_PAGE_H__
#define __PREFETCHER_MODEL_NEXT_PAGE_H__

#include "fixed_types.h"
#include "subsecond_time.h"
#include "prefetcher_model.h"

// Returns the next physical page in memory as the page prefetch candidate
class PrefetcherModelNextPage : public PrefetcherModel
{
   public:
      PrefetcherModelNextPage(UInt32 page_size);
      ~PrefetcherModelNextPage();

      UInt64 pagePrefetchCandidate(UInt64 current_phys_page);

   private:
      UInt32 m_page_size;
};

#endif /* __PREFETCHER_MODEL_NEXT_PAGE_H__ */
