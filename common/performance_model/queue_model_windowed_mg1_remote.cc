/** This file is based off of the modified queue_model_windowed_mg1. 
 * At the time of writing, the main difference is the inclusion of remote_mem_add_lat
 * in the returned latency
*/

#include "queue_model_windowed_mg1_remote.h"
#include "simulator.h"
#include "config.hpp"
#include "log.h"
#include "stats.h"

QueueModelWindowedMG1Remote::QueueModelWindowedMG1Remote(String name, UInt32 id)
   : m_window_size(SubsecondTime::NS(Sim()->getCfg()->getInt("queue_model/windowed_mg1/window_size")))
   , m_total_requests(0)
   , m_total_utilized_time(SubsecondTime::Zero())
   , m_total_queue_delay(SubsecondTime::Zero())
   , m_num_arrivals(0)
   , m_service_time_sum(0)
   , m_service_time_sum2(0)
   , m_r_added_latency(SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/remote_mem_add_lat"))) // Network latency for remote DRAM access 
   , m_name(name)
{  
   registerStatsMetric(name, id, "num-requests", &m_total_requests);
   registerStatsMetric(name, id, "total-time-used", &m_total_utilized_time);
   registerStatsMetric(name, id, "total-queue-delay", &m_total_queue_delay);
}

QueueModelWindowedMG1Remote::~QueueModelWindowedMG1Remote()
{}

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
   removeItems(std::max(main, backup));

   if (m_name == "dram-datamovement-queue")
      LOG_PRINT("m_num_arrivals=%ld before if statement", m_num_arrivals);
   if (m_num_arrivals > 1)
   {
      double utilization = (double)m_service_time_sum / m_window_size.getPS();
      double arrival_rate = (double)m_num_arrivals / m_window_size.getPS();

      double service_time_Es2 = m_service_time_sum2 / m_num_arrivals;

      // If requesters do not throttle based on returned latency, it's their problem, not ours
      if (utilization > .9999) { // number here changed from .99 to .9999; still needed?
         utilization = .9999;
      }

      t_queue = SubsecondTime::PS(arrival_rate * service_time_Es2 / (2 * (1. - utilization)));
      if (m_name == "dram-datamovement-queue")
         LOG_PRINT("t_queue initially calculated as %ld ns: %f / %f = %f ps", t_queue.getNS(),
                   (arrival_rate * service_time_Es2), (2 * (1. - utilization)), arrival_rate * service_time_Es2 / (2 * (1. - utilization)));

      // Our memory is limited in time to m_window_size. It would be strange to return more latency than that.
      if (t_queue > m_window_size)
         t_queue = m_window_size;
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
QueueModelWindowedMG1Remote::computeQueueDelayNoEffect(SubsecondTime pkt_time, SubsecondTime processing_time, core_id_t requester)
{
   SubsecondTime t_queue = SubsecondTime::Zero();

   // Advance the window based on the global (barrier) time, as this guarantees the earliest time any thread may be at.
   // Use a backup value of 10 window sizes before the current request to avoid excessive memory usage in case something fishy is going on.
   SubsecondTime backup = pkt_time > 10*m_window_size ? pkt_time - 10*m_window_size : SubsecondTime::Zero();
   SubsecondTime main = Sim()->getClockSkewMinimizationServer()->getGlobalTime() > m_window_size ? Sim()->getClockSkewMinimizationServer()->getGlobalTime() - m_window_size : SubsecondTime::Zero();
   removeItems(std::max(main, backup));

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
      if (t_queue > m_window_size)
         t_queue = m_window_size;
   }
   // Add additional network latency
   t_queue += m_r_added_latency;  // is it ok for t_queue to potentially be larger than m_window_size?

   // removed addItem() call and calls that updated stats

   return t_queue;
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
