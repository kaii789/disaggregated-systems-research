/** This file is based off of the modified queue_model_windowed_mg1_remote_subqueuemodels. 
 * At the time of writing, the main differences are:
 *  1) Tries to account for both 
*/

#include "queue_model_windowed_mg1_remote_ind_queues.h"
#include "simulator.h"
#include "config.hpp"
#include "log.h"
#include "stats.h"
#include "print_utils.h"

// #include <algorithm>

QueueModelWindowedMG1RemoteIndQueues::QueueModelWindowedMG1RemoteIndQueues(String name, UInt32 id, UInt64 bw_bits_per_us)
   : m_window_size(SubsecondTime::NS(Sim()->getCfg()->getInt("queue_model/windowed_mg1_remote_ind_queues/window_size")))
   , m_use_separate_queue_delay_cap(Sim()->getCfg()->getBool("queue_model/windowed_mg1_remote_ind_queues/use_separate_queue_delay_cap"))
   , m_use_utilization_overflow(Sim()->getCfg()->getBool("queue_model/windowed_mg1_remote_ind_queues/use_utilization_overflow"))
   , m_page_queue_overflowed_to_cacheline_queue(0)
   , m_cacheline_queue_overflowed_to_page_queue(0)
   , m_num_page_arrivals(0)
   , m_num_cacheline_arrivals(0)
   , m_page_service_time_sum(0)
   , m_cacheline_service_time_sum(0)
   , m_page_service_time_sum2(0)
   , m_cacheline_service_time_sum2(0)
   , m_r_added_latency(SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/remote_mem_add_lat"))) // Network latency for remote DRAM access 
   , m_r_partition_queues(Sim()->getCfg()->getInt("perf_model/dram/remote_partitioned_queues")) // Whether partitioned queues is enabled
   , m_r_cacheline_queue_fraction(Sim()->getCfg()->getFloat("perf_model/dram/remote_cacheline_queue_fraction"))
   , m_page_inject_delay_when_queue_full(Sim()->getCfg()->getBool("queue_model/windowed_mg1_remote_ind_queues/page_inject_delay_when_queue_full"))
   , m_cacheline_inject_delay_when_queue_full(Sim()->getCfg()->getBool("queue_model/windowed_mg1_remote_ind_queues/cacheline_inject_delay_when_queue_full"))
   , m_name(name)
   , m_specified_bw_GB_per_s((double)bw_bits_per_us / 8 / 1000)  // convert bits/us to GB/s
   , m_max_bandwidth_allowable_excess_ratio(Sim()->getCfg()->getFloat("queue_model/windowed_mg1_remote_ind_queues/bandwidth_allowable_excess_ratio"))
   , m_effective_bandwidth_exceeded_allowable_max(0)
   , m_page_effective_bandwidth_exceeded_allowable_max(0)
   , m_cacheline_effective_bandwidth_exceeded_allowable_max(0)
   , m_max_effective_bandwidth(0.0)
   , m_max_effective_bandwidth_bytes(0)
   , m_max_effective_bandwidth_ps(1)  // dummy value; can't be 0
   , m_page_bytes_tracking(0)
   , m_cacheline_bytes_tracking(0)
   , m_page_max_effective_bandwidth(0.0)
   , m_cacheline_max_effective_bandwidth(0.0)
   , m_page_max_effective_bandwidth_bytes(0)
   , m_page_max_effective_bandwidth_ps(1)  // dummy value; can't be 0
   , m_cacheline_max_effective_bandwidth_bytes(0)
   , m_cacheline_max_effective_bandwidth_ps(1)  // dummy value; can't be 0
   , m_total_requests(0)
   , m_total_page_requests(0)
   , m_total_cacheline_requests(0)
   , m_total_page_requests_queue_full(0)
   , m_total_page_requests_capped_by_window_size(0)
   , m_total_cacheline_requests_queue_full(0)
   , m_total_cacheline_requests_capped_by_window_size(0)
   // , m_total_requests_capped_by_queue_delay_cap(0)
   , m_total_utilized_time(SubsecondTime::Zero())
   , m_total_queue_delay(SubsecondTime::Zero())
   , m_total_page_queue_delay(SubsecondTime::Zero())
   , m_total_cacheline_queue_delay(SubsecondTime::Zero())
   , m_page_utilization_full_injected_delay(SubsecondTime::Zero())
   , m_cacheline_utilization_full_injected_delay(SubsecondTime::Zero())
   , m_page_utilization_full_injected_delay_max(SubsecondTime::Zero())
   , m_cacheline_utilization_full_injected_delay_max(SubsecondTime::Zero())
   , m_total_page_queue_utilization_during_cacheline_requests_numerator(0)
   , m_total_page_queue_utilization_during_cacheline_requests_denominator(0)
   , m_total_cacheline_queue_utilization_during_page_requests_numerator(0)
   , m_total_cacheline_queue_utilization_during_page_requests_denominator(0)
   , m_total_page_queue_utilization_during_cacheline_no_effect_numerator(0)
   , m_total_page_queue_utilization_during_cacheline_no_effect_denominator(0)
   , m_total_cacheline_queue_utilization_during_page_no_effect_numerator(0)
   , m_total_cacheline_queue_utilization_during_page_no_effect_denominator(0)
{  
   if (m_use_separate_queue_delay_cap) {
      m_queue_delay_cap = SubsecondTime::NS(Sim()->getCfg()->getInt("queue_model/windowed_mg1_remote_ind_queues/queue_delay_cap"));
   } else {
      m_queue_delay_cap = m_window_size;  // in this case m_queue_delay_cap won't be used, but set accordingly just in case
   }

   if (m_use_utilization_overflow) {
      m_utilization_overflow_threshold = Sim()->getCfg()->getFloat("queue_model/windowed_mg1_remote_ind_queues/subqueue_utilization_overflow_threshold");
   }
   
   registerStatsMetric(name, id, "num-requests", &m_total_requests);
   registerStatsMetric(name, id, "num-page-requests", &m_total_page_requests);
   registerStatsMetric(name, id, "num-cacheline-requests", &m_total_cacheline_requests);

   registerStatsMetric(name, id, "total-time-used", &m_total_utilized_time);
   registerStatsMetric(name, id, "total-queue-delay", &m_total_queue_delay);
   registerStatsMetric(name, id, "total-page-queue-delay", &m_total_page_queue_delay);
   registerStatsMetric(name, id, "total-cacheline-queue-delay", &m_total_cacheline_queue_delay);
     
   registerStatsMetric(name, id, "num-page-requests-queue-full", &m_total_page_requests_queue_full);
   registerStatsMetric(name, id, "num-page-requests-capped-by-window-size", &m_total_page_requests_capped_by_window_size);
   registerStatsMetric(name, id, "num-cacheline-requests-queue-full", &m_total_cacheline_requests_queue_full);
   registerStatsMetric(name, id, "num-cacheline-requests-capped-by-window-size", &m_total_cacheline_requests_capped_by_window_size);
   // registerStatsMetric(name, id, "num-requests-capped-by-custom-cap", &m_total_requests_capped_by_queue_delay_cap);
   registerStatsMetric(name, id, "page-requests-queue-full-injected-delay", &m_page_utilization_full_injected_delay);
   registerStatsMetric(name, id, "cacheline-requests-queue-full-injected-delay", &m_cacheline_utilization_full_injected_delay);

   registerStatsMetric(name, id, "num-requests-page-queue-overflowed-to-cacheline-queue", &m_page_queue_overflowed_to_cacheline_queue);
   registerStatsMetric(name, id, "num-requests-cacheline-queue-overflowed-to-page-queue", &m_cacheline_queue_overflowed_to_page_queue);

   registerStatsMetric(name, id, "total-cacheline-queue-utilization-during-page-requests-numerator", &m_total_cacheline_queue_utilization_during_page_requests_numerator);
   registerStatsMetric(name, id, "total-cacheline-queue-utilization-during-page-requests-denominator", &m_total_cacheline_queue_utilization_during_page_requests_denominator);
   registerStatsMetric(name, id, "total-page-queue-utilization-during-cacheline-requests-numerator", &m_total_page_queue_utilization_during_cacheline_requests_numerator);
   registerStatsMetric(name, id, "total-page-queue-utilization-during-cacheline-requests-denominator", &m_total_page_queue_utilization_during_cacheline_requests_denominator);

   registerStatsMetric(name, id, "total-cacheline-queue-utilization-during-page-no-effect-numerator", &m_total_cacheline_queue_utilization_during_page_no_effect_numerator);
   registerStatsMetric(name, id, "total-cacheline-queue-utilization-during-page-no-effect-denominator", &m_total_cacheline_queue_utilization_during_page_no_effect_denominator);
   registerStatsMetric(name, id, "total-page-queue-utilization-during-cacheline-no-effect-numerator", &m_total_page_queue_utilization_during_cacheline_no_effect_numerator);
   registerStatsMetric(name, id, "total-page-queue-utilization-during-cacheline-no-effect-denominator", &m_total_page_queue_utilization_during_cacheline_no_effect_denominator);
   registerStatsMetric(name, id, "num-no-effect-page-requests", &m_total_no_effect_page_requests);
   registerStatsMetric(name, id, "num-no-effect-cacheline-requests", &m_total_no_effect_cacheline_requests);

   // Divide the first following stat by the second one to get bytes / ps (can't register a double type as a stat)
   // The only reason why it's in bytes/ps is because these were the raw values used to compute effective bandwidth
   // in this class
   registerStatsMetric(name, id, "max-effective-bandwidth-bytes", &m_max_effective_bandwidth_bytes);
   registerStatsMetric(name, id, "max-effective-bandwidth-ps", &m_max_effective_bandwidth_ps);
   registerStatsMetric(name, id, "page-max-effective-bandwidth-bytes", &m_page_max_effective_bandwidth_bytes);
   registerStatsMetric(name, id, "page-max-effective-bandwidth-ps", &m_page_max_effective_bandwidth_ps);
   registerStatsMetric(name, id, "cacheline-max-effective-bandwidth-bytes", &m_cacheline_max_effective_bandwidth_bytes);
   registerStatsMetric(name, id, "cacheline-max-effective-bandwidth-ps", &m_cacheline_max_effective_bandwidth_ps);

   // Effective bandwidth only tracked when m_total_requests is incremented and addItems() is called (ie once per actual queue delay request)
   registerStatsMetric(name, id, "num-effective-bandwidth-exceeded-allowable-max", &m_effective_bandwidth_exceeded_allowable_max);
   registerStatsMetric(name, id, "num-page-effective-bandwidth-exceeded-allowable-max", &m_page_effective_bandwidth_exceeded_allowable_max);
   registerStatsMetric(name, id, "num-cacheline-effective-bandwidth-exceeded-allowable-max", &m_cacheline_effective_bandwidth_exceeded_allowable_max);

   std::cout << "Using windowed_mg1_remote_ind_queues queue model with m_use_utilization_overflow=" << m_use_utilization_overflow;
   if (m_use_utilization_overflow) {
      std::cout << ", utilization overflow threshold=" << m_utilization_overflow_threshold;
   }
   std::cout << std::endl;
   std::cout << "m_page_inject_delay_when_queue_full=" << m_page_inject_delay_when_queue_full << ", m_cacheline_inject_delay_when_queue_full=" << m_cacheline_inject_delay_when_queue_full << std::endl;

   m_total_page_queue_utilization_during_cacheline_requests_denominator += 1000 * 1000;
   m_total_cacheline_queue_utilization_during_page_requests_denominator += 1000 * 1000;
   m_total_page_queue_utilization_during_cacheline_no_effect_denominator += 1000 * 1000;
   m_total_cacheline_queue_utilization_during_page_no_effect_denominator += 1000 * 1000;
}

QueueModelWindowedMG1RemoteIndQueues::~QueueModelWindowedMG1RemoteIndQueues()
{
   if (m_total_requests < 1) {
      return;
   }
   // Print one time debug output in the destructor method, to be printed once when the program finishes
   std::cout << "Queue " << m_name << ":" << std::endl; 
   std::cout << "m_max_effective_bandwidth gave: " << 1000 * m_max_effective_bandwidth << " GB/s" << std::endl;

   // if (m_effective_bandwidth_tracker.size() > 0) {
   //    // Compute approximate percentiles of m_effective_bandwidth_tracker
   //    std::cout << "True page locality measure:" << std::endl;
   //    std::ostringstream percentages_buffer, cdf_buffer;
   //    sortAndPrintVectorPercentiles(m_effective_bandwidth_tracker, percentages_buffer, cdf_buffer);
   //    std::cout << "CDF X values (bandwidth), in GB/s:\n" << cdf_buffer.str() << std::endl;
   //    std::cout << "CDF Y values (probability):\n" << percentages_buffer.str() << std::endl;
   // }

   if ((double) m_effective_bandwidth_exceeded_allowable_max / m_total_requests > 0.0001) {
      std::cout << "Queue " << m_name << " overall had " << 100 * (double)m_effective_bandwidth_exceeded_allowable_max / m_total_requests;
      std::cout << "% of windows with effective bandwidth that exceeded the allowable max bandwidth of " << m_specified_bw_GB_per_s * m_max_bandwidth_allowable_excess_ratio << "GB/s" << std::endl;
   }

   if (m_total_page_requests > 0) {
      if ((double) m_page_effective_bandwidth_exceeded_allowable_max / m_total_page_requests > 0.0001) {
         std::cout << "Queue " << m_name << " page portion had " << 100 * (double)m_page_effective_bandwidth_exceeded_allowable_max / m_total_page_requests;
         std::cout << "% of windows with effective bandwidth that exceeded the allowable max bandwidth of " << m_specified_bw_GB_per_s * (1 - m_r_cacheline_queue_fraction) * m_max_bandwidth_allowable_excess_ratio << "GB/s" << std::endl;
      }
      std::cout << "Avg cacheline queue utilization during page requests: " << 100 * m_total_cacheline_queue_utilization_during_page_requests / m_total_page_requests << "%" << std::endl;
   }

   if (m_total_cacheline_requests > 0) {
      if ((double) m_cacheline_effective_bandwidth_exceeded_allowable_max / m_total_cacheline_requests > 0.0001) {
         std::cout << "Queue " << m_name << " cacheline portion had " << 100 * (double)m_cacheline_effective_bandwidth_exceeded_allowable_max / m_total_cacheline_requests;
         std::cout << "% of windows with effective bandwidth that exceeded the allowable max bandwidth of " << m_specified_bw_GB_per_s * m_r_cacheline_queue_fraction * m_max_bandwidth_allowable_excess_ratio << "GB/s" << std::endl;
      }
      std::cout << "Avg page queue utilization during cacheline requests: " << 100 * m_total_page_queue_utilization_during_cacheline_requests / m_total_cacheline_requests << "%" << std::endl;
   }

   if (m_total_no_effect_page_requests > 0) {
      std::cout << "Avg cacheline queue utilization during page No Effect requests: " << 100 * m_total_cacheline_queue_utilization_during_page_no_effect / m_total_no_effect_page_requests << "%" << std::endl;
   }
   if (m_total_no_effect_cacheline_requests > 0) {
      std::cout << "Avg page queue utilization during cacheline No Effect requests: " << 100 * m_total_page_queue_utilization_during_cacheline_no_effect / m_total_no_effect_cacheline_requests << "%" << std::endl;
   }

   if (m_total_page_requests_queue_full > 0)
      std::cout << "page utilization full avg injected delay = " << (double)(m_page_utilization_full_injected_delay.getNS()) / m_total_page_requests_queue_full << " ns" << std::endl;
   if (m_total_cacheline_requests_queue_full > 0)
      std::cout << "cacheline utilization full avg injected delay = " << (double)(m_cacheline_utilization_full_injected_delay.getNS()) / m_total_cacheline_requests_queue_full << " ns" << std::endl;

   if (m_page_inject_delay_when_queue_full)
      std::cout << "Max page queue full injected delay (ns)=" << m_page_utilization_full_injected_delay_max.getNS() << std::endl;
   if (m_cacheline_inject_delay_when_queue_full)
      std::cout << "Max cacheline queue full injected delay (ns)=" << m_cacheline_utilization_full_injected_delay_max.getNS() << std::endl;
}

void QueueModelWindowedMG1RemoteIndQueues::finalizeStats() {
   // Doing it again here at the end; only the += here gets the value to show up in the stats for some reason
   m_total_page_queue_utilization_during_cacheline_requests_denominator += 1000 * 1000;
   m_total_cacheline_queue_utilization_during_page_requests_denominator += 1000 * 1000;
   m_total_page_queue_utilization_during_cacheline_no_effect_denominator += 1000 * 1000;
   m_total_cacheline_queue_utilization_during_page_no_effect_denominator += 1000 * 1000;
}

void QueueModelWindowedMG1RemoteIndQueues::updateQueues(SubsecondTime pkt_time, bool track_effective_bandwidth, request_t request_type) {
   // Remove packets that now fall outside the window
   // Advance the window based on the global (barrier) time, as this guarantees the earliest time any thread may be at.
   // Use a backup value of 10 window sizes before the current request to avoid excessive memory usage in case something fishy is going on.
   SubsecondTime backup = pkt_time > 10*m_window_size ? pkt_time - 10*m_window_size : SubsecondTime::Zero();
   SubsecondTime main = Sim()->getClockSkewMinimizationServer()->getGlobalTime() > m_window_size ? Sim()->getClockSkewMinimizationServer()->getGlobalTime() - m_window_size : SubsecondTime::Zero();
   SubsecondTime time_point = SubsecondTime::max(main, backup);
   removeItems(time_point);
   removeItemsUpdateBytes(time_point, pkt_time, track_effective_bandwidth);
}

double QueueModelWindowedMG1RemoteIndQueues::getPageQueueUtilizationPercentage(SubsecondTime pkt_time) {
   updateQueues(pkt_time, false);

   // Use queue utilization as measure to determine whether the queue is full
   double utilization = (double)m_page_service_time_sum / m_window_size.getPS();
   return utilization;
}

double QueueModelWindowedMG1RemoteIndQueues::getCachelineQueueUtilizationPercentage(SubsecondTime pkt_time) {
   updateQueues(pkt_time, false);

   // Use queue utilization as measure to determine whether the queue is full
   double utilization = (double)m_cacheline_service_time_sum / m_window_size.getPS();
   return utilization;
}

double QueueModelWindowedMG1RemoteIndQueues::getTotalQueueUtilizationPercentage(SubsecondTime pkt_time) {
   if (!m_r_partition_queues) {
      return getPageQueueUtilizationPercentage(pkt_time);
   }

   updateQueues(pkt_time, false);

   // Use queue utilization as measure to determine whether the queue is full
   double utilization = (double)(m_page_service_time_sum + m_cacheline_service_time_sum) / (2 * m_window_size.getPS());
   return utilization;
}

// Currently, this only affects the stats tracking what effective max bandwidths are reached
void QueueModelWindowedMG1RemoteIndQueues::updateBandwidth(UInt64 bw_bits_per_us, double r_cacheline_queue_fraction) {
   m_specified_bw_GB_per_s = ((double)bw_bits_per_us / 8 / 1000);  // convert bits/us to GB/s
   m_r_cacheline_queue_fraction = r_cacheline_queue_fraction;
}

void QueueModelWindowedMG1RemoteIndQueues::updateAddedNetLat(int added_latency_ns) {
   m_r_added_latency.setInternalDataForced(1000000UL * added_latency_ns);
}

// With computeQueueDelayTrackBytes(), computeQueueDelay() shouldn't be used anymore
SubsecondTime
QueueModelWindowedMG1RemoteIndQueues::computeQueueDelay(SubsecondTime pkt_time, SubsecondTime processing_time, core_id_t requester)
{
   throw std::logic_error("QueueModelWindowedMG1RemoteIndQueues::computeQueueDelay shouldn't be called");
}

/* Get estimate of queue delay without adding the packet to the queue */
SubsecondTime
QueueModelWindowedMG1RemoteIndQueues::computeQueueDelayNoEffect(SubsecondTime pkt_time, SubsecondTime processing_time, request_t request_type, core_id_t requester)
{
   SubsecondTime t_queue = SubsecondTime::Zero();
   SubsecondTime utilization_overflow_wait_time = SubsecondTime::Zero();
   if (!m_r_partition_queues) {
      request_type = QueueModel::PAGE;
   }

   updateQueues(pkt_time, false);

   double page_queue_utilization_percentage = getPageQueueUtilizationPercentage(pkt_time);
   double cacheline_queue_utilization_percentage = getCachelineQueueUtilizationPercentage(pkt_time);

   if ((request_type == QueueModel::PAGE && m_num_page_arrivals > 1) || (request_type == QueueModel::CACHELINE && m_num_cacheline_arrivals > 1))  // Share num_arrivals among both queues, since the number gets cancelled out anyways
   {
      UInt64 service_time_sum;
      UInt64 service_time_sum2;
      UInt64 num_arrivals;
      
      // Process differently whether this is a page or cacheline access
      if (request_type == QueueModel::PAGE) {
         service_time_sum = m_page_service_time_sum;
         service_time_sum2 = m_page_service_time_sum2;
         num_arrivals = m_num_page_arrivals;
      } else {  // request_type == QueueModel::CACHELINE
         service_time_sum = m_cacheline_service_time_sum;
         service_time_sum2 = m_cacheline_service_time_sum2;
         num_arrivals = m_num_cacheline_arrivals;
      }
      t_queue = applySingleWindowSizeFormula(request_type, service_time_sum, service_time_sum2, num_arrivals, false, pkt_time, utilization_overflow_wait_time);
   }
   // Add additional network latency
   t_queue += m_r_added_latency;  // is it ok for t_queue to potentially be larger than m_window_size?

   // removed addItem() call and calls that updated stats
   
   // Stats for diagnosing
   if (request_type == QueueModel::PAGE) {
      ++m_total_no_effect_page_requests;
      m_total_cacheline_queue_utilization_during_page_no_effect += cacheline_queue_utilization_percentage;
      m_total_cacheline_queue_utilization_during_page_no_effect_numerator += (UInt64)(cacheline_queue_utilization_percentage * m_total_cacheline_queue_utilization_during_page_no_effect_denominator);
   } else {  // request_type == QueueModel::CACHELINE
      ++m_total_no_effect_cacheline_requests;
      m_total_page_queue_utilization_during_cacheline_no_effect += page_queue_utilization_percentage;
      m_total_page_queue_utilization_during_cacheline_no_effect_numerator += (UInt64)(cacheline_queue_utilization_percentage * m_total_page_queue_utilization_during_cacheline_no_effect_denominator);
   }

   return t_queue + utilization_overflow_wait_time;
}

SubsecondTime
QueueModelWindowedMG1RemoteIndQueues::computeQueueDelayTrackBytes(SubsecondTime pkt_time, SubsecondTime processing_time, UInt64 num_bytes, request_t request_type, core_id_t requester, bool is_inflight_page, UInt64 phys_page)
{
   SubsecondTime t_queue = SubsecondTime::Zero();
   SubsecondTime utilization_overflow_wait_time = SubsecondTime::Zero();
   if (!m_r_partition_queues) {
      request_type = QueueModel::PAGE;
   }

   updateQueues(pkt_time, true, request_type);  // only track effective bandwidth when m_total_requests is incremented and addItems() is called

   double page_queue_utilization_percentage = getPageQueueUtilizationPercentage(pkt_time);
   double cacheline_queue_utilization_percentage = getCachelineQueueUtilizationPercentage(pkt_time);

   if ((request_type == QueueModel::PAGE && m_num_page_arrivals > 1) || (request_type == QueueModel::CACHELINE && m_num_cacheline_arrivals > 1))  // Share num_arrivals among both queues, since the number gets cancelled out anyways
   {
      UInt64 service_time_sum;
      UInt64 service_time_sum2;
      UInt64 num_arrivals;
      
      // Process differently whether this is a page or cacheline access
      if (request_type == QueueModel::PAGE) {
         service_time_sum = m_page_service_time_sum;
         service_time_sum2 = m_page_service_time_sum2;
         num_arrivals = m_num_page_arrivals;
      } else {  // request_type == QueueModel::CACHELINE
         service_time_sum = m_cacheline_service_time_sum;
         service_time_sum2 = m_cacheline_service_time_sum2;
         num_arrivals = m_num_cacheline_arrivals;
      }
      t_queue = applySingleWindowSizeFormula(request_type, service_time_sum, service_time_sum2, num_arrivals, true, pkt_time, utilization_overflow_wait_time);
   }
   // Add additional network latency
   t_queue += m_r_added_latency;  // is it ok for t_queue to potentially be larger than m_window_size?

   // If one queue's utilization is high, add it to the other queue if the other queue has space
   // TODO: need to modify processing time to be based off of the other queue's bandwidth?
   if (m_use_utilization_overflow && request_type == QueueModel::PAGE && page_queue_utilization_percentage > m_utilization_overflow_threshold && cacheline_queue_utilization_percentage < m_utilization_overflow_threshold - 0.1) {
      // Add to cacheline queue instead (fills its utilization)
      addItem(pkt_time + utilization_overflow_wait_time, processing_time, QueueModel::CACHELINE);
      addItemUpdateBytes(pkt_time + utilization_overflow_wait_time, num_bytes, t_queue, QueueModel::CACHELINE);
      ++m_page_queue_overflowed_to_cacheline_queue;
   } else if (m_use_utilization_overflow && request_type == QueueModel::CACHELINE && cacheline_queue_utilization_percentage > m_utilization_overflow_threshold && page_queue_utilization_percentage < m_utilization_overflow_threshold - 0.1) {
      // Add to page queue instead (fills its utilization)
      addItem(pkt_time + utilization_overflow_wait_time, processing_time, QueueModel::PAGE);
      addItemUpdateBytes(pkt_time + utilization_overflow_wait_time, num_bytes, t_queue, QueueModel::PAGE);
      ++m_cacheline_queue_overflowed_to_page_queue;
   } else {
      addItem(pkt_time + utilization_overflow_wait_time, processing_time, request_type);
      addItemUpdateBytes(pkt_time + utilization_overflow_wait_time, num_bytes, t_queue, request_type);
   }


   m_total_utilized_time += processing_time;
   ++m_total_requests;
   m_total_queue_delay += t_queue + utilization_overflow_wait_time;
   if (request_type == QueueModel::PAGE) {
      ++m_total_page_requests;
      m_total_page_queue_delay += t_queue + utilization_overflow_wait_time;
      m_total_cacheline_queue_utilization_during_page_requests += cacheline_queue_utilization_percentage;
      m_total_cacheline_queue_utilization_during_page_requests_numerator += (UInt64)(cacheline_queue_utilization_percentage * m_total_cacheline_queue_utilization_during_page_requests_denominator);
   } else {  // request_type == QueueModel::CACHELINE
      ++m_total_cacheline_requests;
      m_total_cacheline_queue_delay += t_queue + utilization_overflow_wait_time;
      m_total_page_queue_utilization_during_cacheline_requests += page_queue_utilization_percentage;
      m_total_page_queue_utilization_during_cacheline_requests_numerator += (UInt64)(cacheline_queue_utilization_percentage * m_total_page_queue_utilization_during_cacheline_requests_denominator);
   }

   return t_queue + utilization_overflow_wait_time;
}

// total_service_time is in ps, total_service_time2 is in ps^2, utilization_window_size is in ps
SubsecondTime
QueueModelWindowedMG1RemoteIndQueues::applyQueueDelayFormula(request_t request_type, UInt64 total_service_time, UInt64 total_service_time2, UInt64 num_arrivals, UInt64 utilization_window_size, bool update_stats, SubsecondTime pkt_time, SubsecondTime &utilization_overflow_wait_time)
{
   const double max_utilization = 0.9999;  // number here changed from .99 to .9999; still needed?
   // See if we need to make the request at a future time (for queue delay correctness)
   // Assume utilization_overflow_wait_time is passed in with an initialized value
   UInt64 max_total_service_time = max_utilization * utilization_window_size;
   if (((request_type == QueueModel::PAGE && m_page_inject_delay_when_queue_full) || (request_type == QueueModel::CACHELINE && m_cacheline_inject_delay_when_queue_full)) &&total_service_time > max_total_service_time) {
      // m_print_debugging_info = true;
      SubsecondTime initial_time, moved_time;
      if (request_type == QueueModel::PAGE) {
         std::multimap<SubsecondTime, SubsecondTime>::iterator entry = m_window_page_requests.begin();
         initial_time = entry->first;
         // See how long we need to wait for the utilization to drop to max_utilization or lower
         while(entry != m_window_page_requests.end() && total_service_time > max_total_service_time)
         {
            moved_time = entry->first;
            total_service_time -= entry->second.getPS();
            total_service_time2 -= entry->second.getPS() * entry->second.getPS();
            num_arrivals --;
            entry++;
         }
      } else {  // request_type == QueueModel::CACHELINE
         std::multimap<SubsecondTime, SubsecondTime>::iterator entry = m_window_cacheline_requests.begin();
         initial_time = entry->first;
         // See how long we need to wait for the utilization to drop to max_utilization or lower
         while(entry != m_window_cacheline_requests.end() && total_service_time > max_total_service_time)
         {
            moved_time = entry->first;
            total_service_time -= entry->second.getPS();
            total_service_time2 -= entry->second.getPS() * entry->second.getPS();
            num_arrivals --;
            entry++;
         }
      }

      utilization_overflow_wait_time += (moved_time - initial_time);

      if (update_stats && request_type == QueueModel::PAGE) {
         ++m_total_page_requests_queue_full;
         m_page_utilization_full_injected_delay += utilization_overflow_wait_time;
         if (utilization_overflow_wait_time > m_page_utilization_full_injected_delay_max) {
            m_page_utilization_full_injected_delay_max = utilization_overflow_wait_time;
         }
      }
      else if (update_stats) {  // request_type == QueueModel::CACHELINE
         ++m_total_cacheline_requests_queue_full;
         m_cacheline_utilization_full_injected_delay += utilization_overflow_wait_time;
         if (utilization_overflow_wait_time > m_cacheline_utilization_full_injected_delay_max) {
            m_cacheline_utilization_full_injected_delay_max = utilization_overflow_wait_time;
         }
      }
   }

   double utilization = (double)total_service_time / utilization_window_size;
   double service_time_Es2 = total_service_time2 / num_arrivals;
   double arrival_rate = (double)num_arrivals / utilization_window_size;

   // When not injecting delay when the queue is full, have a cap on the utilization value input into the formula
   if (((request_type == QueueModel::PAGE && !m_page_inject_delay_when_queue_full) || (request_type == QueueModel::CACHELINE && !m_cacheline_inject_delay_when_queue_full)) && utilization > max_utilization) {
      // If requesters do not throttle based on returned latency, it's their problem, not ours
      utilization = max_utilization;
      if (update_stats && request_type == QueueModel::PAGE)
         ++m_total_page_requests_queue_full;
      else if (update_stats)  // request_type == QueueModel::CACHELINE
         ++m_total_cacheline_requests_queue_full;
   }

   SubsecondTime t_queue = SubsecondTime::PS(arrival_rate * service_time_Es2 / (2 * (1. - utilization)));
   // if (m_name == "dram-datamovement-queue")
   //    LOG_PRINT("t_queue initially calculated as %ld ns: %f / %f = %f ps", t_queue.getNS(),
   //              (arrival_rate * service_time_Es2), (2 * (1. - utilization)), arrival_rate * service_time_Es2 / (2 * (1. - utilization)));

   // Our memory is limited in time to m_window_size. It would be strange to return more latency than that.
   if (!m_use_separate_queue_delay_cap && t_queue > m_window_size) {
      // Normally, use m_window_size as the cap
      t_queue = m_window_size;
      if (update_stats && request_type == QueueModel::PAGE)
         ++m_total_page_requests_capped_by_window_size;
      else if (update_stats)  // request_type == QueueModel::CACHELINE
         ++m_total_cacheline_requests_capped_by_window_size;
   } else if (m_use_separate_queue_delay_cap) {
      if (t_queue > m_queue_delay_cap) {
         // When m_use_separate_queue_delay_cap is true, try using a custom queue_delay_cap to handle the cases when the queue is full
         t_queue = m_queue_delay_cap;
         // ++m_total_requests_capped_by_queue_delay_cap;
      }
      if (update_stats && t_queue > m_window_size) {
         // still keep track of this stat when separate queue delay cap is used
         if (request_type == QueueModel::PAGE)
            ++m_total_page_requests_capped_by_window_size;
         else  // request_type == QueueModel::CACHELINE
            ++m_total_cacheline_requests_capped_by_window_size;
      }
   }
   // Note: network additional latency is NOT added in this method, needs to be added separately
   return t_queue;  // caller should add utilization_overflow_wait_time as appropriate
}

// total_service_time is in ps, total_service_time2 is in ps^2
SubsecondTime
QueueModelWindowedMG1RemoteIndQueues::applySingleWindowSizeFormula(request_t request_type, UInt64 total_service_time, UInt64 total_service_time2, UInt64 num_arrivals, bool update_stats, SubsecondTime pkt_time, SubsecondTime &utilization_overflow_wait_time)
{
   return applyQueueDelayFormula(request_type, total_service_time, total_service_time2, num_arrivals, m_window_size.getPS(), update_stats, pkt_time, utilization_overflow_wait_time);
}

// total_service_time is in ps, total_service_time2 is in ps^2
// SubsecondTime
// QueueModelWindowedMG1RemoteIndQueues::applyDoubleWindowSizeFormula(request_t request_type, UInt64 total_service_time, UInt64 total_service_time2, UInt64 num_arrivals, bool update_stats, SubsecondTime pkt_time, SubsecondTime &utilization_overflow_wait_time)
// {
//    return applyQueueDelayFormula(request_type, total_service_time, total_service_time2, num_arrivals, 2 * m_window_size.getPS(), update_stats, pkt_time, utilization_overflow_wait_time);
// }

void
QueueModelWindowedMG1RemoteIndQueues::addItemUpdateBytes(SubsecondTime pkt_time, UInt64 num_bytes, SubsecondTime pkt_queue_delay, request_t request_type)
{
   // Add num_bytes to the corresponding map, and update the total number of bytes being tracked in the map
   if (request_type == QueueModel::PAGE) {
      m_page_packet_bytes.insert(std::pair<SubsecondTime, UInt64>(pkt_time + pkt_queue_delay, num_bytes));
      m_page_bytes_tracking += num_bytes;
   } else {  // request_type == QueueModel::CACHELINE
      m_cacheline_packet_bytes.insert(std::pair<SubsecondTime, UInt64>(pkt_time + pkt_queue_delay, num_bytes));
      m_cacheline_bytes_tracking += num_bytes;
   }
}

// Parameter request_type only supplied when track_effective_bandwidth == true
void
QueueModelWindowedMG1RemoteIndQueues::removeItemsUpdateBytes(SubsecondTime earliest_time, SubsecondTime pkt_time, bool track_effective_bandwidth, request_t request_type)
{
   // Can remove packets that arrived earlier than the current window
   while(!m_page_packet_bytes.empty() && m_page_packet_bytes.begin()->first < earliest_time)
   {
      std::multimap<SubsecondTime, UInt64>::iterator bytes_entry = m_page_packet_bytes.begin();
      m_page_bytes_tracking -= bytes_entry->second;
      m_page_packet_bytes.erase(bytes_entry);
   }
   while(!m_cacheline_packet_bytes.empty() && m_cacheline_packet_bytes.begin()->first < earliest_time)
   {
      std::multimap<SubsecondTime, UInt64>::iterator bytes_entry = m_cacheline_packet_bytes.begin();
      m_cacheline_bytes_tracking -= bytes_entry->second;
      m_cacheline_packet_bytes.erase(bytes_entry);
   }
   
   // Update bytes_in_window by not considering packets in m_cacheline_packet_bytes and m_page_packet_bytes that arrive later than pkt_time
   UInt64 page_bytes_in_window = m_page_bytes_tracking;
   UInt64 cacheline_bytes_in_window = m_cacheline_bytes_tracking;
   for (std::multimap<SubsecondTime, UInt64>::iterator bytes_entry = m_page_packet_bytes.upper_bound(pkt_time); bytes_entry != m_page_packet_bytes.end(); ++bytes_entry) {
      page_bytes_in_window -= bytes_entry->second;
   }
   for (std::multimap<SubsecondTime, UInt64>::iterator bytes_entry = m_cacheline_packet_bytes.upper_bound(pkt_time); bytes_entry != m_cacheline_packet_bytes.end(); ++bytes_entry) {
      cacheline_bytes_in_window -= bytes_entry->second;
   }
   UInt64 bytes_in_window = page_bytes_in_window + cacheline_bytes_in_window;

   // Intention: only track effective bandwidth when m_total_requests is incremented and addItems() is called
   if (track_effective_bandwidth) {
      // Compute the effective current window length, and calculate the current effective bandwidth
      // Note: bytes_in_window is used instead of m_page_bytes_tracking + m_cacheline_bytes_tracking
      UInt64 effective_window_length_ps = (pkt_time - earliest_time).getPS();
      double cur_effective_bandwidth = (double)bytes_in_window / effective_window_length_ps;  // in bytes/ps
      if (cur_effective_bandwidth > m_max_effective_bandwidth) {
         m_max_effective_bandwidth = cur_effective_bandwidth;
         m_max_effective_bandwidth_bytes = bytes_in_window;
         m_max_effective_bandwidth_ps = effective_window_length_ps;
      }
      if (cur_effective_bandwidth * 1000 > m_specified_bw_GB_per_s * m_max_bandwidth_allowable_excess_ratio) {  // GB/s used here
         ++m_effective_bandwidth_exceeded_allowable_max;
      }
      // Calculate max effective bandwidth of page and cacheline portions--though they could exceed their specifications at times
      if (request_type == QueueModel::PAGE) {
         double cur_page_effective_bandwidth = (double)page_bytes_in_window / effective_window_length_ps;  // in bytes/ps
         if (cur_page_effective_bandwidth > m_page_max_effective_bandwidth) {
            m_page_max_effective_bandwidth = cur_page_effective_bandwidth;
            m_page_max_effective_bandwidth_bytes = page_bytes_in_window;
            m_page_max_effective_bandwidth_ps = effective_window_length_ps;
         }
         if (cur_page_effective_bandwidth * 1000 > m_specified_bw_GB_per_s * (1 - m_r_cacheline_queue_fraction) * m_max_bandwidth_allowable_excess_ratio) {  // GB/s used here
            ++m_page_effective_bandwidth_exceeded_allowable_max;
         }
      } else {  // request_type == QueueModel::CACHELINE
         double cur_cacheline_effective_bandwidth = (double)cacheline_bytes_in_window / effective_window_length_ps;  // in bytes/ps
         if (cur_cacheline_effective_bandwidth > m_cacheline_max_effective_bandwidth) {
            m_cacheline_max_effective_bandwidth = cur_cacheline_effective_bandwidth;
            m_cacheline_max_effective_bandwidth_bytes = cacheline_bytes_in_window;
            m_cacheline_max_effective_bandwidth_ps = effective_window_length_ps;
         }
         if (cur_cacheline_effective_bandwidth * 1000 > m_specified_bw_GB_per_s * m_r_cacheline_queue_fraction * m_max_bandwidth_allowable_excess_ratio) {  // GB/s used here
            ++m_cacheline_effective_bandwidth_exceeded_allowable_max;
         }
      }

      // m_effective_bandwidth_tracker.push_back(cur_effective_bandwidth);
   }
}


void
QueueModelWindowedMG1RemoteIndQueues::addItem(SubsecondTime pkt_time, SubsecondTime service_time, request_t request_type)
{
   if (request_type == QueueModel::PAGE) {
      m_window_page_requests.insert(std::pair<SubsecondTime, SubsecondTime>(pkt_time, service_time));
      m_page_service_time_sum += service_time.getPS();
      m_page_service_time_sum2 += service_time.getPS() * service_time.getPS();
      m_num_page_arrivals ++;
   } else {  // request_type == QueueModel::CACHELINE
      m_window_cacheline_requests.insert(std::pair<SubsecondTime, SubsecondTime>(pkt_time, service_time));
      m_cacheline_service_time_sum += service_time.getPS();
      m_cacheline_service_time_sum2 += service_time.getPS() * service_time.getPS();
      m_num_cacheline_arrivals ++;
   }
}

void
QueueModelWindowedMG1RemoteIndQueues::removeItems(SubsecondTime earliest_time)
{
   // Page request map
   while(!m_window_page_requests.empty() && m_window_page_requests.begin()->first < earliest_time)
   {
      std::multimap<SubsecondTime, SubsecondTime>::iterator entry = m_window_page_requests.begin();
      m_num_page_arrivals --;
      m_page_service_time_sum -= entry->second.getPS();
      m_page_service_time_sum2 -= entry->second.getPS() * entry->second.getPS();
      m_window_page_requests.erase(entry);
   }
   // Cacheline request map
   while(!m_window_cacheline_requests.empty() && m_window_cacheline_requests.begin()->first < earliest_time)
   {
      std::multimap<SubsecondTime, SubsecondTime>::iterator entry = m_window_cacheline_requests.begin();
      m_num_cacheline_arrivals --;
      m_cacheline_service_time_sum -= entry->second.getPS();
      m_cacheline_service_time_sum2 -= entry->second.getPS() * entry->second.getPS();
      m_window_cacheline_requests.erase(entry);
   }
}
