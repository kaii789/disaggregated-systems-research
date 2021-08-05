/** This file is based off of the modified queue_model_windowed_mg1. 
 * At the time of writing, the main differences are:
 *  1) The inclusion of remote_mem_add_lat in the returned queue delay latency
 *  2) The effective bandwidth within the window size is tracked, and if it
 *     exceeds the specified bandwidth over a user-provided ratio, an error message
 *     will be printed
*/

#include "queue_model_windowed_mg1_remote.h"
#include "simulator.h"
#include "config.hpp"
#include "log.h"
#include "stats.h"

// #include <algorithm>

QueueModelWindowedMG1Remote::QueueModelWindowedMG1Remote(String name, UInt32 id, UInt64 bw_bits_per_us)
   : m_window_size(SubsecondTime::NS(Sim()->getCfg()->getInt("queue_model/windowed_mg1_remote/window_size")))
   , m_use_separate_queue_delay_cap(Sim()->getCfg()->getBool("queue_model/windowed_mg1_remote/use_separate_queue_delay_cap"))
   , m_total_requests(0)
   , m_total_requests_queue_full(0)
   , m_total_requests_capped_by_window_size(0)
   , m_total_requests_capped_by_queue_delay_cap(0)
   , m_total_utilized_time(SubsecondTime::Zero())
   , m_total_queue_delay(SubsecondTime::Zero())
   , m_num_arrivals(0)
   , m_service_time_sum(0)
   , m_service_time_sum2(0)
   , m_r_added_latency(SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/remote_mem_add_lat"))) // Network latency for remote DRAM access 
   , m_name(name)
   , m_specified_bw_GB_per_s((double)bw_bits_per_us / 8 / 1000)  // convert bits/us to GB/s
   , m_max_bandwidth_allowable_excess_ratio(Sim()->getCfg()->getFloat("queue_model/windowed_mg1_remote/bandwidth_allowable_excess_ratio"))
   , m_effective_bandwidth_exceeded_allowable_max(0)
   , m_bytes_tracking(0)
   , m_max_effective_bandwidth(0.0)
   , m_max_effective_bandwidth_bytes(0)
   , m_max_effective_bandwidth_ps(1)  // dummy value; can't be 0
{  
   if (m_use_separate_queue_delay_cap) {
      m_queue_delay_cap = SubsecondTime::NS(Sim()->getCfg()->getInt("queue_model/windowed_mg1_remote/queue_delay_cap"));
   } else {
      m_queue_delay_cap = m_window_size;  // in this case m_queue_delay_cap won't be used, but set accordingly just in case
   }
   
   registerStatsMetric(name, id, "num-requests", &m_total_requests);
   registerStatsMetric(name, id, "total-time-used", &m_total_utilized_time);
   registerStatsMetric(name, id, "total-queue-delay", &m_total_queue_delay);
   registerStatsMetric(name, id, "num-requests-queue-full", &m_total_requests_queue_full);
   registerStatsMetric(name, id, "num-requests-capped-by-window-size", &m_total_requests_capped_by_window_size);
   registerStatsMetric(name, id, "num-requests-capped-by-custom-cap", &m_total_requests_capped_by_queue_delay_cap);
   
   // Divide the first following stat by the second one to get bytes / ps (can't register a double type as a stat)
   // The only reason why it's in bytes/ps is because these were the raw values used to compute effective bandwidth
   // in this class. Considering converting to GB/s like other bandwidth values?
   registerStatsMetric(name, id, "max-effective-bandwidth-bytes", &m_max_effective_bandwidth_bytes);
   registerStatsMetric(name, id, "max-effective-bandwidth-ps", &m_max_effective_bandwidth_ps);

   // Only tracked m_total_requests is incremented and addItems() is called (ie once per actual queue delay request)
   registerStatsMetric(name, id, "num-effective-bandwidth-exceeded-allowable-max", &m_effective_bandwidth_exceeded_allowable_max);
}

QueueModelWindowedMG1Remote::~QueueModelWindowedMG1Remote()
{
   if (m_total_requests < 1) {
      return;
   }
   // Print one time debug output in the destructor method, to be printed once when the program finishes
   // if (m_effective_bandwidth_tracker.size() < 1) {
   //    return;
   // }
   std::cout << "Queue " << m_name << ":" << std::endl; 
   std::cout << "m_max_effective_bandwidth gave: " << 1000 * m_max_effective_bandwidth << " GB/s" << std::endl;

   // // Compute approximate percentiles of m_effective_bandwidth_tracker
   // std::sort(m_effective_bandwidth_tracker.begin(), m_effective_bandwidth_tracker.end());

   // // Compute percentiles for stats
   // UInt64 index;
   // double percentile;
   
   // // Compute more percentiles for output
   // UInt32 num_bins = 40;  // the total number of points is 1 more than num_bins, since it includes the endpoints
   // std::map<double, double> effective_bandwidth_percentiles;
   // for (UInt32 bin = 0; bin < num_bins; ++bin) {
   //    double percentage = (double)bin / num_bins;
   //    index = (UInt64)(percentage * (m_effective_bandwidth_tracker.size() - 1));  // -1 so array indices don't go out of bounds
   //    percentile = m_effective_bandwidth_tracker[index];  // in bytes/ps
   //    std::cout << "percentage: " << percentage << ", vector index: " << index << ", percentile: " << 1000 * percentile << " GB/s" << std::endl;
   //    effective_bandwidth_percentiles.insert(std::pair<double, double>(percentage, percentile));
   // }
   // // Print output in format that can easily be graphed in Python
   // std::ostringstream percentages_buffer;
   // std::ostringstream cdf_buffer;
   // percentages_buffer << "[";
   // cdf_buffer << "[";
   // for (std::map<double, double>::iterator it = effective_bandwidth_percentiles.begin(); it != effective_bandwidth_percentiles.end(); ++it) {
   //    percentages_buffer << it->first << ", ";
   //    cdf_buffer << 1000 * it->second << ", ";  // Convert to GB/s
   // }
   // percentages_buffer << "]";
   // cdf_buffer << "]";

   // std::cout << "CDF X values (bandwidth), in GB/s:\n" << cdf_buffer.str() << std::endl;
   // std::cout << "CDF Y values (probability):\n" << percentages_buffer.str() << std::endl;

   if ((double) m_effective_bandwidth_exceeded_allowable_max / m_total_requests > 0.01) {
      std::cout << "Queue " << m_name << " had " << 100 * (double)m_effective_bandwidth_exceeded_allowable_max / m_total_requests;
      std::cout << "% of windows with effective bandwidth that exceeded the allowable max bandwidth of " << m_specified_bw_GB_per_s * m_max_bandwidth_allowable_excess_ratio << "GB/s" << std::endl;
   }
}

double QueueModelWindowedMG1Remote::getTotalQueueUtilizationPercentage(SubsecondTime pkt_time) {
   // Remove packets that now fall outside the window
   // Advance the window based on the global (barrier) time, as this guarantees the earliest time any thread may be at.
   // Use a backup value of 10 window sizes before the current request to avoid excessive memory usage in case something fishy is going on.
   SubsecondTime backup = pkt_time > 10*m_window_size ? pkt_time - 10*m_window_size : SubsecondTime::Zero();
   SubsecondTime main = Sim()->getClockSkewMinimizationServer()->getGlobalTime() > m_window_size ? Sim()->getClockSkewMinimizationServer()->getGlobalTime() - m_window_size : SubsecondTime::Zero();
   SubsecondTime time_point = SubsecondTime::max(main, backup);
   removeItems(time_point);
   removeItemsUpdateBytes(time_point, pkt_time, false);

   // Use queue utilization as measure to determine whether the queue is full
   double utilization = (double)m_service_time_sum / m_window_size.getPS();
   return utilization;
}

// With computeQueueDelayTrackBytes(), computeQueueDelay() shouldn't be used anymore
SubsecondTime
QueueModelWindowedMG1Remote::computeQueueDelay(SubsecondTime pkt_time, SubsecondTime processing_time, core_id_t requester)
{
   SubsecondTime t_queue = SubsecondTime::Zero();

   // Advance the window based on the global (barrier) time, as this guarantees the earliest time any thread may be at.
   // Use a backup value of 10 window sizes before the current request to avoid excessive memory usage in case something fishy is going on.
   SubsecondTime backup = pkt_time > 10*m_window_size ? pkt_time - 10*m_window_size : SubsecondTime::Zero();
   SubsecondTime main = Sim()->getClockSkewMinimizationServer()->getGlobalTime() > m_window_size ? Sim()->getClockSkewMinimizationServer()->getGlobalTime() - m_window_size : SubsecondTime::Zero();
   // if (m_name == "dram-datamovement-queue") {
   //    LOG_PRINT("m_num_arrivals=%ld initially; removeItems argument was max of %ld ns and %ld ns", m_num_arrivals,
   //              main.getNS(), backup.getNS());
   // }
   removeItems(SubsecondTime::max(main, backup));

   if (m_num_arrivals > 1)
   {
      double utilization = (double)m_service_time_sum / m_window_size.getPS();
      double arrival_rate = (double)m_num_arrivals / m_window_size.getPS();

      double service_time_Es2 = m_service_time_sum2 / m_num_arrivals;

      // If requesters do not throttle based on returned latency, it's their problem, not ours
      if (utilization > .9999) { // number here changed from .99 to .9999; still needed?
         ++m_total_requests_queue_full;
         utilization = .9999;
      }

      t_queue = SubsecondTime::PS(arrival_rate * service_time_Es2 / (2 * (1. - utilization)));
      if (m_name == "dram-datamovement-queue")
         LOG_PRINT("t_queue initially calculated as %ld ns: %f / %f = %f ps", t_queue.getNS(),
                   (arrival_rate * service_time_Es2), (2 * (1. - utilization)), arrival_rate * service_time_Es2 / (2 * (1. - utilization)));

      // Our memory is limited in time to m_window_size. It would be strange to return more latency than that.
      if (!m_use_separate_queue_delay_cap && t_queue > m_window_size) {
         // Normally, use m_window_size as the cap
         t_queue = m_window_size;
         ++m_total_requests_capped_by_window_size;
      } else if (m_use_separate_queue_delay_cap) {
         if (t_queue > m_queue_delay_cap) {
            // When m_use_separate_queue_delay_cap is true, try using a custom queue_delay_cap to handle the cases when the queue is full
            t_queue = m_queue_delay_cap;
            ++m_total_requests_capped_by_queue_delay_cap;
         }
         if (t_queue > m_window_size) {
            ++m_total_requests_capped_by_window_size;  // still keep track of this stat when separate queue delay cap is used
         }
      }
   }
   // Add additional network latency
   t_queue += m_r_added_latency;  // is it ok for t_queue to potentially be larger than m_window_size?

   addItem(pkt_time, processing_time);

   m_total_requests++;
   m_total_utilized_time += processing_time;
   m_total_queue_delay += t_queue;

   return t_queue;
}

/* Get estimate of queue delay without adding the packet to the queue */
SubsecondTime
QueueModelWindowedMG1Remote::computeQueueDelayNoEffect(SubsecondTime pkt_time, SubsecondTime processing_time, request_t request_type, core_id_t requester)
{
   SubsecondTime t_queue = SubsecondTime::Zero();

   // Advance the window based on the global (barrier) time, as this guarantees the earliest time any thread may be at.
   // Use a backup value of 10 window sizes before the current request to avoid excessive memory usage in case something fishy is going on.
   SubsecondTime backup = pkt_time > 10*m_window_size ? pkt_time - 10*m_window_size : SubsecondTime::Zero();
   SubsecondTime main = Sim()->getClockSkewMinimizationServer()->getGlobalTime() > m_window_size ? Sim()->getClockSkewMinimizationServer()->getGlobalTime() - m_window_size : SubsecondTime::Zero();
   SubsecondTime time_point = SubsecondTime::max(main, backup);
   removeItems(time_point);
   removeItemsUpdateBytes(time_point, pkt_time, false);

   if (m_num_arrivals > 1)
   {
      double utilization = (double)m_service_time_sum / m_window_size.getPS();
      double arrival_rate = (double)m_num_arrivals / m_window_size.getPS();

      double service_time_Es2 = m_service_time_sum2 / m_num_arrivals;

      // If requesters do not throttle based on returned latency, it's their problem, not ours
      if (utilization > .9999)  // number here changed from .99 to .9999
         utilization = .9999;

      t_queue = SubsecondTime::PS(arrival_rate * service_time_Es2 / (2 * (1. - utilization)));

      // Our memory is limited in time to m_window_size. It would be strange to return more latency than that.
      // Don't update stats here for computeQueueDelayNoEffect
      if (!m_use_separate_queue_delay_cap && t_queue > m_window_size) {
         // Normally, use m_window_size as the cap
         t_queue = m_window_size;
      } else if (m_use_separate_queue_delay_cap) {
         if (t_queue > m_queue_delay_cap) {
            // When m_use_separate_queue_delay_cap is true, try using a custom queue_delay_cap to handle the cases when the queue is full
            t_queue = m_queue_delay_cap;
         }
      }
   }
   // Add additional network latency
   t_queue += m_r_added_latency;  // is it ok for t_queue to potentially be larger than m_window_size?

   // removed addItem() call and calls that updated stats

   return t_queue;
}


// Also include the num_bytes parameter; last two arguments currently not used
SubsecondTime
QueueModelWindowedMG1Remote::computeQueueDelayTrackBytes(SubsecondTime pkt_time, SubsecondTime processing_time, UInt64 num_bytes, request_t request_type, core_id_t requester, bool is_inflight_page, UInt64 phys_page)
{
   SubsecondTime t_queue = SubsecondTime::Zero();

   // Advance the window based on the global (barrier) time, as this guarantees the earliest time any thread may be at.
   // Use a backup value of 10 window sizes before the current request to avoid excessive memory usage in case something fishy is going on.
   SubsecondTime backup = pkt_time > 10*m_window_size ? pkt_time - 10*m_window_size : SubsecondTime::Zero();
   SubsecondTime main = Sim()->getClockSkewMinimizationServer()->getGlobalTime() > m_window_size ? Sim()->getClockSkewMinimizationServer()->getGlobalTime() - m_window_size : SubsecondTime::Zero();
   // if (m_name == "dram-datamovement-queue") {
   //    LOG_PRINT("m_num_arrivals=%ld initially; removeItems argument was max of %ld ns and %ld ns", m_num_arrivals,
   //              main.getNS(), backup.getNS());
   // }
   SubsecondTime time_point = SubsecondTime::max(main, backup);
   removeItems(time_point);
   removeItemsUpdateBytes(time_point, pkt_time, true);  // only track effective bandwidth when m_total_requests is incremented and addItems() is called

   if (m_num_arrivals > 1)
   {
      double utilization = (double)m_service_time_sum / m_window_size.getPS();
      double arrival_rate = (double)m_num_arrivals / m_window_size.getPS();

      double service_time_Es2 = m_service_time_sum2 / m_num_arrivals;

      // If requesters do not throttle based on returned latency, it's their problem, not ours
      if (utilization > .9999) { // number here changed from .99 to .9999; still needed?
         ++m_total_requests_queue_full;
         utilization = .9999;
      }

      t_queue = SubsecondTime::PS(arrival_rate * service_time_Es2 / (2 * (1. - utilization)));
      if (m_name == "dram-datamovement-queue")
         LOG_PRINT("t_queue initially calculated as %ld ns: %f / %f = %f ps", t_queue.getNS(),
                   (arrival_rate * service_time_Es2), (2 * (1. - utilization)), arrival_rate * service_time_Es2 / (2 * (1. - utilization)));

      // Our memory is limited in time to m_window_size. It would be strange to return more latency than that.
      if (!m_use_separate_queue_delay_cap && t_queue > m_window_size) {
         // Normally, use m_window_size as the cap
         t_queue = m_window_size;
         ++m_total_requests_capped_by_window_size;
      } else if (m_use_separate_queue_delay_cap) {
         if (t_queue > m_queue_delay_cap) {
            // When m_use_separate_queue_delay_cap is true, try using a custom queue_delay_cap to handle the cases when the queue is full
            t_queue = m_queue_delay_cap;
            ++m_total_requests_capped_by_queue_delay_cap;
         }
         if (t_queue > m_window_size) {
            ++m_total_requests_capped_by_window_size;  // still keep track of this stat when separate queue delay cap is used
         }
      }
   }
   // Add additional network latency
   t_queue += m_r_added_latency;  // is it ok for t_queue to potentially be larger than m_window_size?

   addItem(pkt_time, processing_time);
   addItemUpdateBytes(pkt_time, num_bytes, t_queue);

   m_total_requests++;
   m_total_utilized_time += processing_time;
   m_total_queue_delay += t_queue;

   return t_queue;
}

void
QueueModelWindowedMG1Remote::addItemUpdateBytes(SubsecondTime pkt_time, UInt64 num_bytes, SubsecondTime pkt_queue_delay)
{
   // Add num_bytes to map tracking the current window & update m_bytes_tracking
   m_packet_bytes.insert(std::pair<SubsecondTime, UInt64>(pkt_time + pkt_queue_delay, num_bytes));
   m_bytes_tracking += num_bytes;
}

void
QueueModelWindowedMG1Remote::removeItemsUpdateBytes(SubsecondTime earliest_time, SubsecondTime pkt_time, bool track_effective_bandwidth)
{
   // Can remove packets that arrived earlier than the current window
   while(!m_packet_bytes.empty() && m_packet_bytes.begin()->first < earliest_time)
   {
      std::multimap<SubsecondTime, UInt64>::iterator bytes_entry = m_packet_bytes.begin();
      m_bytes_tracking -= bytes_entry->second;
      m_packet_bytes.erase(bytes_entry);
   }

   UInt64 bytes_in_window = m_bytes_tracking;
   // Update bytes_in_window by not considering packets in m_bytes_tracking that arrive later than pkt_time
   for (std::multimap<SubsecondTime, UInt64>::iterator bytes_entry = m_packet_bytes.upper_bound(pkt_time); bytes_entry != m_packet_bytes.end(); ++bytes_entry) {
      bytes_in_window -= bytes_entry->second;
   }
   
   // Intention: only track effective bandwidth when m_total_requests is incremented and addItems() is called
   if (track_effective_bandwidth) {
      // Compute the effective current window length, and calculate the current effective bandwidth
      // Note: bytes_in_window is used instead of m_bytes_tracking
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
      
      // m_effective_bandwidth_tracker.push_back(cur_effective_bandwidth);
   }
}


void
QueueModelWindowedMG1Remote::addItem(SubsecondTime pkt_time, SubsecondTime service_time)
{
   m_window.insert(std::pair<SubsecondTime, SubsecondTime>(pkt_time, service_time));
   m_num_arrivals ++;
   m_service_time_sum += service_time.getPS();
   m_service_time_sum2 += service_time.getPS() * service_time.getPS();
}

void
QueueModelWindowedMG1Remote::removeItems(SubsecondTime earliest_time)
{
   while(!m_window.empty() && m_window.begin()->first < earliest_time)
   {
      std::multimap<SubsecondTime, SubsecondTime>::iterator entry = m_window.begin();
      m_num_arrivals --;
      m_service_time_sum -= entry->second.getPS();
      m_service_time_sum2 -= entry->second.getPS() * entry->second.getPS();
      m_window.erase(entry);
   }
}
