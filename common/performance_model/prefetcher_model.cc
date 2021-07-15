#include "simulator.h"
#include "prefetcher_model.h"
#include "prefetcher_model_next_page.h"
#include "config.hpp"

PrefetcherModel*
PrefetcherModel::createPrefetcherModel(UInt32 page_size)
{
   String type = Sim()->getCfg()->getString("perf_model/dram/prefetcher_model/type");

   if (type == "next_page")
   {
      return new PrefetcherModelNextPage(page_size);
   }
   else
   {
      LOG_PRINT_ERROR("Invalid Prefetcher model type %s", type.c_str());
      return (PrefetcherModel*) NULL;
   }
}
