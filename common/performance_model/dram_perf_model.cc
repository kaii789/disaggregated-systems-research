#include "simulator.h"
#include "dram_perf_model.h"
#include "dram_perf_model_constant.h"
#include "dram_perf_model_readwrite.h"
#include "dram_perf_model_normal.h"
#include "dram_perf_model_disagg.h"
#include "dram_perf_model_disagg_remote_only.h"
#include "dram_perf_model_disagg_page_move_free.h"
#include "dram_perf_model_disagg_multipage.h"
#include "config.hpp"

//DramPerfModel* DramPerfModel::createDramPerfModel(core_id_t core_id, UInt32 cache_block_size)
// Add address_home_lookup parameter to incorporate disagg perf model
DramPerfModel* DramPerfModel::createDramPerfModel(core_id_t core_id, UInt32 cache_block_size, AddressHomeLookup* address_home_lookup)
{
   String type = Sim()->getCfg()->getString("perf_model/dram/type");

   if (type == "constant")
   {
      return new DramPerfModelConstant(core_id, cache_block_size);
   }
   else if (type == "readwrite")
   {
      return new DramPerfModelReadWrite(core_id, cache_block_size);
   }
   else if (type == "normal")
   {
      return new DramPerfModelNormal(core_id, cache_block_size);
   }
   else if (type == "disaggregated")
   {
      return new DramPerfModelDisagg(core_id, cache_block_size, address_home_lookup);
   }
   else if (type == "disaggregated_remote_only")
   {
      return new DramPerfModelDisaggRemoteOnly(core_id, cache_block_size, address_home_lookup);
   }
   else if (type == "disaggregated_page_move_free")
   {
      return new DramPerfModelDisaggPageMoveFree(core_id, cache_block_size, address_home_lookup);
   }
   else if (type == "disaggregated_multipage")
   {
      return new DramPerfModelDisaggMultipage(core_id, cache_block_size, address_home_lookup);
   }
   else
   {
      LOG_PRINT_ERROR("Invalid DRAM model type %s", type.c_str());
   }
}

void DramPerfModel::updateLatency() {
}

void DramPerfModel::updateLocalIPCStat() {
}