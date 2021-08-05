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

private:
    String m_name;
    UInt32 m_page_size;
    UInt32 m_cache_line_size;
    UInt32 m_cacheline_count;

    String m_cacheline_compression_scheme;
    String m_dict_compression_scheme;
    CompressionModel *m_cacheline_compression_model;
    CompressionModel *m_dict_compression_model;
    double m_bandwidth_utilization;
    double m_lower_bandwidth_threshold;
    double m_upper_bandwidth_threshold;
    std::map<UInt64, String> m_addr_to_scheme;

    UInt64 m_cacheline_compression_count = 0;
    UInt64 m_dict_compression_count = 0;

    // Placeholder
    UInt32 m_compression_latency = 10;
    UInt32 m_decompression_latency = 10;
};

#endif /* __COMPRESSION_MODEL_ADAPTIVE_H__ */