#include "compression_model_lz4.h"
#include <lz4.h>

CompressionModelLZ4::CompressionModelLZ4(String name, UInt32 page_size, UInt32 cache_line_size, int compression_latency_config, int decompression_latency_config)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
{
    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];

    // Set compression/decompression cycle latencies if configured
    if (compression_latency_config != -1)
        m_compression_latency = compression_latency_config;
    if (decompression_latency_config != -1)
        m_decompression_latency = decompression_latency_config;
}

SubsecondTime
CompressionModelLZ4::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    // Get Data
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    core->getApplicationData(Core::NONE, Core::READ, addr, m_data_buffer, data_size, Core::MEM_MODELED_NONE); // Assume addr already points to page or cache line

    // LZ4
    int total_bytes = LZ4_compress_default(m_data_buffer, m_compressed_data_buffer, m_page_size, m_page_size);
    assert(total_bytes <= m_page_size && "[LZ4] Wrong compression!\n");

    // Use total bytes instead of compressed cache lines for decompression
    *compressed_cache_lines = total_bytes;

    // Return compressed pages size in Bytes
    *compressed_page_size = total_bytes;

    // printf("[LZ4] Compressed Page Size: %u bytes\n", total_bytes);

    // 780 MB/s compression rate
    double compression_latency = 1 / (float)((780 * (UInt64)1000000) / m_page_size); // In seconds
    // printf("[LZ4] %f s\n", compression_latency);
    return SubsecondTime::NS(compression_latency * 1000000000);
}

CompressionModelLZ4::~CompressionModelLZ4()
{
}

SubsecondTime
CompressionModelLZ4::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    int compressed_size = compressed_cache_lines;
    // 4970 MB/s compression rate
    double decompression_latency = 1 / (float)((4970 * (UInt64)1000000) / compressed_size); // In seconds
    // printf("[LZ4] %f s\n", decompression_latency);
    return SubsecondTime::NS(decompression_latency * 1000000000);
}
