#ifndef __QUEUE_MODEL_WINDOWED_MG1_REMOTE_H__
#define __QUEUE_MODEL_WINDOWED_MG1_REMOTE_H__

#include "queue_model.h"
#include "fixed_types.h"
#include "contention_model.h"

#include <map>

class QueueModelWindowedMG1Remote : public QueueModel
{
public:
   QueueModelWindowedMG1Remote(String name, UInt32 id, UInt64 bw_bits_per_us);
   ~QueueModelWindowedMG1Remote();

   SubsecondTime computeQueueDelay(SubsecondTime pkt_time, SubsecondTime processing_time, core_id_t requester = INVALID_CORE_ID);
   SubsecondTime computeQueueDelayNoEffect(SubsecondTime pkt_time, SubsecondTime processing_time, core_id_t requester = INVALID_CORE_ID);

   SubsecondTime computeQueueDelayTrackBytes(SubsecondTime pkt_time, SubsecondTime processing_time, UInt64 num_bytes, core_id_t requester = INVALID_CORE_ID);

   // bool isQueueFull(SubsecondTime pkt_time);
   double getQueueUtilizationPercentage(SubsecondTime pkt_time);

private:
   const SubsecondTime m_window_size;
   SubsecondTime m_queue_delay_cap;      // Only considered if m_use_separate_queue_delay_cap is true; cap applied before network additional latency
   bool m_use_separate_queue_delay_cap;  // Whether to use a separate queue delay cap

   UInt64 m_total_requests;
   UInt64 m_total_requests_queue_full;                 // The number of requests where queue utilization was full
   UInt64 m_total_requests_capped_by_window_size;      // Note: When m_use_separate_queue_delay_cap is true, this counts requests with calculated queue delay larger than window_size, but weren't actually capped
   UInt64 m_total_requests_capped_by_queue_delay_cap;  // The number of requests where the returned queue delay was capped by the separate m_queue_delay_cap
   SubsecondTime m_total_utilized_time;
   SubsecondTime m_total_queue_delay;

   std::multimap<SubsecondTime, SubsecondTime> m_window;
   UInt64 m_num_arrivals;
   UInt64 m_service_time_sum; // In ps
   UInt64 m_service_time_sum2; // In ps^2

   const SubsecondTime m_r_added_latency; // Additional network latency from remote access

   String m_name;  // temporary, for debugging
   
   double m_specified_bw_GB_per_s;                         // The specified bandwidth this queue model is supposed to have, in GB/s
   double m_max_bandwidth_allowable_excess_ratio;          // Allow effective bandwidth to exceed the specified bandwidth by at most this ratio
   UInt64 m_effective_bandwidth_exceeded_allowable_max;    // The number of actual queue requests for which the effective bandwidth in the window exceeded m_specified_bw_GB_per_s * m_max_bandwidth_allowable_excess_ratio

   UInt64 m_bytes_tracking;                                // track the total number of bytes being transferred in the current window
   double m_max_effective_bandwidth;                       // in bytes / ps
   // The following two variables are to register stats
   UInt64 m_max_effective_bandwidth_bytes;
   UInt64 m_max_effective_bandwidth_ps;
   std::multimap<SubsecondTime, UInt64> m_packet_bytes;    // track the number of bytes of each packet being transferred in the current window
   // std::vector<double> m_effective_bandwidth_tracker;      // (try to) track the distribution of effective bandwidth
   
   void addItem(SubsecondTime pkt_time, SubsecondTime service_time);
   void removeItems(SubsecondTime earliest_time);

   void addItemUpdateBytes(SubsecondTime pkt_time, UInt64 num_bytes, SubsecondTime pkt_queue_delay);
   void removeItemsUpdateBytes(SubsecondTime earliest_time, SubsecondTime pkt_time, bool track_effective_bandwidth);
};

#endif /* __QUEUE_MODEL_WINDOWED_MG1_REMOTE_H__ */
