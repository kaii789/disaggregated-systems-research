#ifndef __COMPRESSION_MODEL_LZ4_H__
#define __COMPRESSION_MODEL_LZ4_H__

#include "compression_model.h"

class CompressionModelLZ4 : public CompressionModel
{
public:
   CompressionModelLZ4(String name, UInt32 page_size, UInt32 cache_line_size, int compression_latency_config, int decompression_latency_config, double freq_norm);
   ~CompressionModelLZ4();

   SubsecondTime compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines);
   SubsecondTime decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id);

private:
    String m_name;
    UInt32 m_page_size;
    UInt32 m_cache_line_size;
    char *m_data_buffer;
    char *m_compressed_data_buffer;
    UInt32 m_cacheline_count;

    // Compression latency per cache line
    UInt32 m_compression_latency = 3;
    // Decompression latency per cache line
    UInt32 m_decompression_latency = 5;

    double m_freq_norm;

};

#endif /* __COMPRESSION_MODEL_LZ4_H__ */