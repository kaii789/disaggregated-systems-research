/** This file is based off of the modified queue_model_windowed_mg1. 
 * At the time of writing, the main difference is the inclusion of remote_mem_add_lat
 * in the returned latency
*/

#include "queue_model_network_latency_only.h"
#include "simulator.h"
#include "config.hpp"
#include "log.h"
#include "stats.h"

QueueModelNetworkLatencyOnly::QueueModelNetworkLatencyOnly(String name, UInt32 id)
   : m_total_requests(0)
   , m_total_utilized_time(SubsecondTime::Zero())
   , m_total_queue_delay(SubsecondTime::Zero())
   , m_r_added_latency(SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/remote_mem_add_lat"))) // Network latency for remote DRAM access 
   , m_name(name)
{  
   registerStatsMetric(name, id, "num-requests", &m_total_requests);
   registerStatsMetric(name, id, "total-time-used", &m_total_utilized_time);
   registerStatsMetric(name, id, "total-queue-delay", &m_total_queue_delay);
}

QueueModelNetworkLatencyOnly::~QueueModelNetworkLatencyOnly()
{}

// Return just the network latency (ie ignore bandwidth)
SubsecondTime
QueueModelNetworkLatencyOnly::computeQueueDelay(SubsecondTime pkt_time, SubsecondTime processing_time, core_id_t requester)
{
   SubsecondTime t_queue = SubsecondTime::Zero();

   // Add additional network latency
   t_queue += m_r_added_latency;

   m_total_requests++;
   m_total_utilized_time += processing_time;
   m_total_queue_delay += t_queue;

   return t_queue;
}

/* Get estimate of queue delay without adding the packet to the queue */
SubsecondTime
QueueModelNetworkLatencyOnly::computeQueueDelayNoEffect(SubsecondTime pkt_time, SubsecondTime processing_time, core_id_t requester)
{
   SubsecondTime t_queue = SubsecondTime::Zero();

   // Add additional network latency
   t_queue += m_r_added_latency;

   // removed calls that updated stats

   return t_queue;
}
