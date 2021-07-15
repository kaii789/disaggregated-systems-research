#include "simulator.h"
#include "config.hpp"
#include "log.h"
#include "stats.h"
#include "prefetcher_model_next_page.h"

PrefetcherModelNextPage::PrefetcherModelNextPage(UInt32 page_size)
   : m_page_size(page_size)
{
}

PrefetcherModelNextPage::~PrefetcherModelNextPage()
{
}

// Return the next physical page
UInt64
PrefetcherModelNextPage::pagePrefetchCandidate(UInt64 current_phys_page)
{
    return current_phys_page + 1 * m_page_size;
}
