#ifndef __QUEUE_MODEL_WINDOWED_MG1_REMOTE_COMBINED_H__
#define __QUEUE_MODEL_WINDOWED_MG1_REMOTE_COMBINED_H__

#include "queue_model.h"
#include "fixed_types.h"
#include "contention_model.h"

#include <map>
#include <set>

class QueueModelWindowedMG1RemoteCombined : public QueueModel
{
public:
   QueueModelWindowedMG1RemoteCombined(String name, UInt32 id, UInt64 bw_bits_per_us, SubsecondTime baseline_page_processing_time, SubsecondTime baseline_cacheline_processing_time);
   ~QueueModelWindowedMG1RemoteCombined();

   SubsecondTime computeQueueDelay(SubsecondTime pkt_time, SubsecondTime processing_time, core_id_t requester = INVALID_CORE_ID);
   SubsecondTime computeQueueDelayNoEffect(SubsecondTime pkt_time, SubsecondTime processing_time, request_t request_type, core_id_t requester = INVALID_CORE_ID);

   // SubsecondTime computeQueueDelayTrackBytes(SubsecondTime pkt_time, SubsecondTime processing_time, UInt64 num_bytes, request_t request_type, core_id_t requester = INVALID_CORE_ID);
   SubsecondTime computeQueueDelayTrackBytes(SubsecondTime pkt_time, SubsecondTime processing_time, UInt64 num_bytes, request_t request_type, core_id_t requester = INVALID_CORE_ID, bool is_inflight_page = false, UInt64 phys_page = 0);

   double getTotalQueueUtilizationPercentage(SubsecondTime pkt_time);

   double getPageQueueUtilizationPercentage(SubsecondTime pkt_time);
   double getCachelineQueueUtilizationPercentage(SubsecondTime pkt_time);


private:
   const SubsecondTime m_window_size;
   SubsecondTime m_queue_delay_cap;      // Only considered if m_use_separate_queue_delay_cap is true; cap applied before network additional latency
   bool m_use_separate_queue_delay_cap;  // Whether to use a separate queue delay cap

   // std::multimap<SubsecondTime, SubsecondTime> m_window;
   std::multimap<SubsecondTime, SubsecondTime> m_window_page_requests;
   std::multimap<SubsecondTime, SubsecondTime> m_window_cacheline_requests;
   UInt64 m_num_arrivals;
   // UInt64 m_service_time_sum; // In ps; can be calculated by adding together m_page_service_time_sum and m_cacheline_service_time_sum
   UInt64 m_service_time_sum2; // In ps^2
   UInt64 m_page_service_time_sum; // In ps
   UInt64 m_cacheline_service_time_sum; // In ps

   const SubsecondTime m_r_added_latency; // Additional network latency from remote access
   double m_r_cacheline_queue_fraction;   // The fraction of remote bandwidth used for the cacheline queue (decimal between 0 and 1) 

   SubsecondTime m_page_processing_time;            // For injecting requests to calculate more accurate queuing delays
   SubsecondTime m_cacheline_processing_time;       // For injecting requests to calculate more accurate queuing delays
   UInt64 m_imbalanced_page_requests;       // Number of page requests not yet "cancelled out" by cacheline requests according to cacheline queue ratio   
   double m_imbalanced_cacheline_requests;  // Number of cacheline requests not yet "cancelled out" by page requests according to cacheline queue ratio
   UInt64 m_max_imbalanced_page_requests;
   UInt64 m_max_imbalanced_cacheline_requests_rounded;
   std::multiset<SubsecondTime> m_page_requests;       // Map to keep track of requests made within a window size
   std::multiset<SubsecondTime> m_cacheline_requests;  // Map to keep track of requests made within a window size
   UInt64 m_page_request_dropped_window_size;       // Number of times page queue request tracker stops tracking a page request in imbalance because of window size
   UInt64 m_cacheline_request_dropped_window_size;  // Number of times cacheline queue request tracker stops tracking a cacheline request in imbalance because of window size
   SubsecondTime m_request_tracking_window_size;       // Window size for maps tracking requests
   double m_cacheline_tracking_fractional_part;

   String m_name;  // temporary, for debugging
   
   double m_specified_bw_GB_per_s;                         // The specified bandwidth this queue model is supposed to have, in GB/s
   double m_max_bandwidth_allowable_excess_ratio;          // Allow effective bandwidth to exceed the specified bandwidth by at most this ratio
   UInt64 m_effective_bandwidth_exceeded_allowable_max;    // The number of actual queue requests for which the effective bandwidth in the window exceeded m_specified_bw_GB_per_s * m_max_bandwidth_allowable_excess_ratio
   UInt64 m_page_effective_bandwidth_exceeded_allowable_max;       // The number of actual queue requests for which the effective page bandwidth in the window exceeded m_specified_bw_GB_per_s * (1 - m_r_cacheline_queue_fraction) * m_max_bandwidth_allowable_excess_ratio
   UInt64 m_cacheline_effective_bandwidth_exceeded_allowable_max;  // The number of actual queue requests for which the effective cacheline bandwidth in the window exceeded m_specified_bw_GB_per_s * m_r_cacheline_queue_fraction * m_max_bandwidth_allowable_excess_ratio

   // UInt64 m_bytes_tracking;                                // track the total number of bytes being transferred in the current window
   double m_max_effective_bandwidth;                       // in bytes / ps
   // The following two variables are to register stats
   UInt64 m_max_effective_bandwidth_bytes;
   UInt64 m_max_effective_bandwidth_ps;
   // std::multimap<SubsecondTime, UInt64> m_packet_bytes;    // track the number of bytes of each packet being transferred in the current window
   // std::vector<double> m_effective_bandwidth_tracker;      // (try to) track the distribution of effective bandwidth

   UInt64 m_page_bytes_tracking;                                // track the total number of bytes being transferred in the current window
   UInt64 m_cacheline_bytes_tracking;                                // track the total number of bytes being transferred in the current window
   double m_page_max_effective_bandwidth;                       // in bytes / ps
   double m_cacheline_max_effective_bandwidth;                  // in bytes / ps
   // The following four variables are to register stats
   UInt64 m_page_max_effective_bandwidth_bytes;
   UInt64 m_page_max_effective_bandwidth_ps;
   UInt64 m_cacheline_max_effective_bandwidth_bytes;
   UInt64 m_cacheline_max_effective_bandwidth_ps;
   std::multimap<SubsecondTime, UInt64> m_page_packet_bytes;    // track the number of bytes of each packet being transferred in the current window
   std::multimap<SubsecondTime, UInt64> m_cacheline_packet_bytes;    // track the number of bytes of each packet being transferred in the current window
   
   // For stats
   UInt64 m_total_requests;
   UInt64 m_total_page_requests;
   UInt64 m_total_cacheline_requests;
   UInt64 m_total_requests_queue_full;                 // The number of requests where queue utilization was full
   UInt64 m_total_requests_capped_by_window_size;      // Note: When m_use_separate_queue_delay_cap is true, this counts requests with calculated queue delay larger than window_size, but weren't actually capped
   UInt64 m_total_requests_capped_by_queue_delay_cap;  // The number of requests where the returned queue delay was capped by the separate m_queue_delay_cap
   SubsecondTime m_total_utilized_time;
   SubsecondTime m_total_queue_delay;
   SubsecondTime m_total_page_queue_delay;
   SubsecondTime m_total_cacheline_queue_delay;
   
   SubsecondTime m_total_page_request_injected_time;       // Total amount of time injected in cacheline queue requests
   SubsecondTime m_total_cacheline_request_injected_time;  // Total amount of time injected in cacheline queue requests

   void addItem(SubsecondTime pkt_time, SubsecondTime service_time, request_t request_type);
   void removeItems(SubsecondTime earliest_time);

   void addItemUpdateBytes(SubsecondTime pkt_time, UInt64 num_bytes, SubsecondTime pkt_queue_delay, request_t request_type);
   void removeItemsUpdateBytes(SubsecondTime earliest_time, SubsecondTime pkt_time, bool track_effective_bandwidth);
};

#endif /* __QUEUE_MODEL_WINDOWED_MG1_REMOTE_COMBINED_H__ */
