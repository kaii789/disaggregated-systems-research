#include "compression_model_ideal.h"
#include "utils.h"

CompressionModelIdeal::CompressionModelIdeal(String name, UInt32 page_size, UInt32 cache_line_size, int compression_latency_config, int decompression_latency_config)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
{
    m_cacheline_count = m_page_size / m_cache_line_size;

    // Set compression/decompression cycle latencies if configured
    if (compression_latency_config != -1)
        m_compression_latency = compression_latency_config;
    if (decompression_latency_config != -1)
        m_decompression_latency = decompression_latency_config;
}

CompressionModelIdeal::~CompressionModelIdeal()
{
}

SubsecondTime
CompressionModelIdeal::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);

    // Return compressed cache lines
    *compressed_cache_lines = m_cacheline_count;

    // Return compressed pages size in Bytes
    *compressed_page_size = 1; // compress all data to 1 byte

    // Return compression latency
    ComponentLatency compress_latency(ComponentLatency(core->getDvfsDomain(), m_cacheline_count  * m_compression_latency));
    return compress_latency.getLatency();

}

SubsecondTime
CompressionModelIdeal::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), compressed_cache_lines * m_decompression_latency));
    return decompress_latency.getLatency();

}

