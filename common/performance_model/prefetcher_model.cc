#include "simulator.h"
#include "prefetcher_model.h"
#include "prefetcher_model_next_n_pages.h"
#include "config.hpp"

PrefetcherModel*
PrefetcherModel::createPrefetcherModel(UInt32 page_size)
{
   String type = Sim()->getCfg()->getString("perf_model/dram/prefetcher_model/type");

   if (type == "next_n_pages")
   {
      UInt32 num_pages_to_prefetch = Sim()->getCfg()->getInt("perf_model/dram/prefetcher_model/next_n_pages/pages_to_prefetch");
      return new PrefetcherModelNextNPages(page_size, num_pages_to_prefetch);
   }
   else
   {
      LOG_PRINT_ERROR("Invalid Prefetcher model type %s", type.c_str());
      return (PrefetcherModel*) NULL;
   }
}
