#include "simulator.h"
#include "config.hpp"
#include "log.h"
#include "stats.h"
#include "prefetcher_model_next_n_pages.h"

PrefetcherModelNextNPages::PrefetcherModelNextNPages(UInt32 page_size, UInt32 num_pages_to_prefetch)
   : m_page_size(page_size)
   , m_num_pages_to_prefetch(num_pages_to_prefetch)
{
}

PrefetcherModelNextNPages::~PrefetcherModelNextNPages()
{
}

// Returns the next N physical pages in memory as the page prefetch candidates
void
PrefetcherModelNextNPages::pagePrefetchCandidates(UInt64 current_phys_page, std::vector<UInt64>& prefetch_candidates)
{
    for (UInt32 i = 1; i < m_num_pages_to_prefetch + 1; ++i) {
        prefetch_candidates.push_back(current_phys_page + i * m_page_size);
    }
}
