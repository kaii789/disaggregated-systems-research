#ifndef __PREFETCHER_MODEL_NEXT_N_PAGES_H__
#define __PREFETCHER_MODEL_NEXT_N_PAGES_H__

#include "fixed_types.h"
#include "subsecond_time.h"
#include "prefetcher_model.h"

// Returns the next N physical pages in memory as the page prefetch candidates
class PrefetcherModelNextNPages : public PrefetcherModel
{
   public:
      PrefetcherModelNextNPages(UInt32 page_size, UInt32 num_pages_to_prefetch);
      ~PrefetcherModelNextNPages();

      void pagePrefetchCandidates(UInt64 current_phys_page, std::vector<UInt64>& prefetch_candidates);

   private:
      UInt32 m_page_size;
      UInt32 m_num_pages_to_prefetch;
};

#endif /* __PREFETCHER_MODEL_NEXT_N_PAGES_H__ */
