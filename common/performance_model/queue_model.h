#ifndef __QUEUE_MODEL_H__
#define __QUEUE_MODEL_H__

#include "fixed_types.h"
#include "subsecond_time.h"

#include <iostream>

class QueueModel
{
public:
   QueueModel() {}
   virtual ~QueueModel() {}

   virtual SubsecondTime computeQueueDelay(SubsecondTime pkt_time, SubsecondTime processing_time, core_id_t requester = INVALID_CORE_ID) = 0;
   virtual SubsecondTime computeQueueDelayNoEffect(SubsecondTime pkt_time, SubsecondTime processing_time, core_id_t requester = INVALID_CORE_ID) {
      return SubsecondTime::Zero();  // placeholder since the method is currently only implemented in the windowed_mg1 QueueModel
   };
   virtual SubsecondTime computeQueueDelayTest(SubsecondTime pkt_time, SubsecondTime processing_time, UInt64 num_bytes, core_id_t requester = INVALID_CORE_ID) {
      return SubsecondTime::Zero();  // placeholder since the method is currently only implemented in the windowed_mg1_remote QueueModel
   };

   static QueueModel* create(String name, UInt32 id, String model_type, SubsecondTime min_processing_time);
};

#endif /* __QUEUE_MODEL_H__ */
