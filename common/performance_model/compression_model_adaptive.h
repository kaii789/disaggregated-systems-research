#ifndef __COMPRESSION_MODEL_ADAPTIVE_H__
#define __COMPRESSION_MODEL_ADAPTIVE_H__

#include "compression_model.h"
#include <map>

class CompressionModelAdaptive : public CompressionModel
{
public:
   CompressionModelAdaptive(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size);
   ~CompressionModelAdaptive();

   SubsecondTime compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines);
   SubsecondTime decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id);

   SubsecondTime compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines);
   SubsecondTime decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines);

   void finalizeStats();
   void update_bandwidth_utilization(double bandwidth_utilization);
   void update_queue_model(QueueModel *queue_model, SubsecondTime t_now, ComponentBandwidth *bandwidth, core_id_t requester);

private:
    String m_name;
    UInt32 m_page_size;
    UInt32 m_cache_line_size;
    UInt32 m_cacheline_count;

    int m_type;
    String m_low_compression_scheme;
    String m_high_compression_scheme;
    CompressionModel *m_low_compression_model;
    CompressionModel *m_high_compression_model;
    double m_bandwidth_utilization;
    double m_lower_bandwidth_threshold;
    double m_upper_bandwidth_threshold;
    std::map<UInt64, String> m_addr_to_scheme;

    UInt64 m_low_compression_count = 0;
    SubsecondTime m_low_total_compression_latency = SubsecondTime::Zero();
    SubsecondTime m_low_total_decompression_latency = SubsecondTime::Zero();
    UInt64 m_low_bytes_saved = 0;

    UInt64 m_high_compression_count = 0;
    SubsecondTime m_high_total_compression_latency = SubsecondTime::Zero();
    SubsecondTime m_high_total_decompression_latency = SubsecondTime::Zero();
    UInt64 m_high_bytes_saved = 0;

    QueueModel* m_queue_model;
    SubsecondTime m_t_now;
    ComponentBandwidth *m_r_bandwidth;
    core_id_t m_requester;

    // Estimator
    int m_type_switch_threshold;

    // Dynamic BW Threshold
    double m_high_compression_rate; // GB/s

    // Placeholder
    UInt32 m_compression_latency = 10;
    UInt32 m_decompression_latency = 10;

    void update_bw_utilization_count();
    UInt64 m_bw_utilization_decile_to_count[10];
};

#endif /* __COMPRESSION_MODEL_ADAPTIVE_H__ */