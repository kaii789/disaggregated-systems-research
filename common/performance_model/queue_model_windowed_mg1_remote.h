#ifndef __QUEUE_MODEL_WINDOWED_MG1_REMOTE_H__
#define __QUEUE_MODEL_WINDOWED_MG1_REMOTE_H__

#include "queue_model.h"
#include "fixed_types.h"
#include "contention_model.h"

#include <map>

class QueueModelWindowedMG1Remote : public QueueModel
{
public:
   QueueModelWindowedMG1Remote(String name, UInt32 id);
   ~QueueModelWindowedMG1Remote();

   SubsecondTime computeQueueDelay(SubsecondTime pkt_time, SubsecondTime processing_time, core_id_t requester = INVALID_CORE_ID);
   SubsecondTime computeQueueDelayNoEffect(SubsecondTime pkt_time, SubsecondTime processing_time, core_id_t requester = INVALID_CORE_ID);

   SubsecondTime computeQueueDelayTest(SubsecondTime pkt_time, SubsecondTime processing_time, UInt64 num_bytes, core_id_t requester = INVALID_CORE_ID);


private:
   const SubsecondTime m_window_size;

   UInt64 m_total_requests;
   UInt64 m_total_requests_queue_full;
   UInt64 m_total_requests_capped_by_window_size;
   SubsecondTime m_total_utilized_time;
   SubsecondTime m_total_queue_delay;

   std::multimap<SubsecondTime, SubsecondTime> m_window;
   UInt64 m_num_arrivals;
   UInt64 m_service_time_sum; // In ps
   UInt64 m_service_time_sum2; // In ps^2

   const SubsecondTime m_r_added_latency; // Additional network latency from remote access

   String m_name;  // temporary, for debugging

   UInt64 m_bytes_tracking;                                // track the total number of bytes being transferred in the current window
   double m_max_effective_bandwidth;                       // in bytes / ps
   // The following two variables are to register stats
   UInt64 m_max_effective_bandwidth_bytes;
   UInt64 m_max_effective_bandwidth_ps;
   std::multimap<SubsecondTime, UInt64> m_packet_bytes;    // track the number of bytes of each packet being transferred in the current window
   std::vector<double> m_effective_bandwidth_tracker;      // (try to) track the distribution of effective bandwidth
   
   // Testing: divide these to get GB/s (NOT bytes/ps)
   // UInt64 m_975_percentile_effective_bandwidth_numerator;   // can use 97.5% percentile instead of max
   // UInt64 m_975_percentile_effective_bandwidth_denominator;
   // UInt64 m_95_percentile_effective_bandwidth_numerator;
   // UInt64 m_95_percentile_effective_bandwidth_denominator;


   void addItem(SubsecondTime pkt_time, SubsecondTime service_time);
   void removeItems(SubsecondTime earliest_time);

   void addItemUpdateBytes(SubsecondTime pkt_time, UInt64 num_bytes, SubsecondTime pkt_queue_delay);
   void removeItemsUpdateBytes(SubsecondTime earliest_time, SubsecondTime pkt_time);
};

#endif /* __QUEUE_MODEL_WINDOWED_MG1_REMOTE_H__ */
