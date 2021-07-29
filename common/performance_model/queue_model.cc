#include "queue_model.h"
#include "simulator.h"
#include "config.h"
#include "queue_model_basic.h"
#include "queue_model_history_list.h"
#include "queue_model_contention.h"
#include "queue_model_windowed_mg1.h"
#include "queue_model_windowed_mg1_remote.h"
#include "queue_model_windowed_mg1_remote_combined.h"
#include "queue_model_windowed_mg1_remote_subqueuemodels.h"
#include "queue_model_network_latency_only.h"
#include "log.h"
#include "config.hpp"

QueueModel*
QueueModel::create(String name, UInt32 id, String model_type, SubsecondTime min_processing_time)
{
   if (model_type == "basic")
   {
      bool moving_avg_enabled = Sim()->getCfg()->getBool("queue_model/basic/moving_avg_enabled");
      UInt32 moving_avg_window_size = Sim()->getCfg()->getInt("queue_model/basic/moving_avg_window_size");
      String moving_avg_type = Sim()->getCfg()->getString("queue_model/basic/moving_avg_type");
      return new QueueModelBasic(name, id, moving_avg_enabled, moving_avg_window_size, moving_avg_type);
   }
   else if (model_type == "history_list")
   {
      return new QueueModelHistoryList(name, id, min_processing_time);
   }
   else if (model_type == "contention")
   {
      return new QueueModelContention(name, id, 1);
   }
   else if (model_type == "windowed_mg1")
   {
      return new QueueModelWindowedMG1(name, id);
   }
   else if (model_type == "network_latency_only")
   {
      return new QueueModelNetworkLatencyOnly(name, id);
   }
   else
   {
      LOG_PRINT_ERROR("Unrecognized Queue Model Type(%s)", model_type.c_str());
      return (QueueModel*) NULL;
   }
}

// To create a windowed_mg1_remote queue model, must use this second create method
QueueModel*
QueueModel::create(String name, UInt32 id, String model_type, SubsecondTime min_processing_time, UInt64 bw_bits_per_us, SubsecondTime baseline_page_processing_time, SubsecondTime baseline_cacheline_processing_time)
{
   if (model_type == "basic")
   {
      bool moving_avg_enabled = Sim()->getCfg()->getBool("queue_model/basic/moving_avg_enabled");
      UInt32 moving_avg_window_size = Sim()->getCfg()->getInt("queue_model/basic/moving_avg_window_size");
      String moving_avg_type = Sim()->getCfg()->getString("queue_model/basic/moving_avg_type");
      return new QueueModelBasic(name, id, moving_avg_enabled, moving_avg_window_size, moving_avg_type);
   }
   else if (model_type == "history_list")
   {
      return new QueueModelHistoryList(name, id, min_processing_time);
   }
   else if (model_type == "contention")
   {
      return new QueueModelContention(name, id, 1);
   }
   else if (model_type == "windowed_mg1")
   {
      return new QueueModelWindowedMG1(name, id);
   }
   else if (model_type == "windowed_mg1_remote")
   {
      return new QueueModelWindowedMG1Remote(name, id, bw_bits_per_us);
   }
   else if (model_type == "windowed_mg1_remote_combined")
   {
      return new QueueModelWindowedMG1RemoteCombined(name, id, bw_bits_per_us, baseline_page_processing_time, baseline_cacheline_processing_time);
   }
   else if (model_type == "windowed_mg1_remote_subqueuemodels")
   {
      return new QueueModelWindowedMG1Subqueuemodels(name, id, bw_bits_per_us);
   }
   else if (model_type == "network_latency_only")
   {
      return new QueueModelNetworkLatencyOnly(name, id);
   }
   else
   {
      LOG_PRINT_ERROR("Unrecognized Queue Model Type(%s)", model_type.c_str());
      return (QueueModel*) NULL;
   }
}
