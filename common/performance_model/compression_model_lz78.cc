#include "compression_model_lz78.h"
#include "utils.h"
#include "config.hpp"

CompressionModelLZ78::CompressionModelLZ78(String name, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
    , m_compression_granularity(Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/compression_granularity"))
{
    // Set compression/decompression cycle latencies if configured
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/compression_latency") != -1)
        m_compression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/compression_latency");
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/decompression_latency") != -1)
        m_decompression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/decompression_latency");

    if (m_compression_granularity == -1)
        m_compression_granularity = m_page_size;

    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];
}

SubsecondTime
CompressionModelLZ78::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    // Get Data
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    if (data_size == m_cache_line_size)  { // If we compress in cache_line granularity
        core->getApplicationData(Core::NONE, Core::READ, addr, m_data_buffer, data_size, Core::MEM_MODELED_NONE); // Assume addr already points to page or cache line
    } else { // If we compress in page_size granularity, we shift to move to the start_addr of the corresponding page
        UInt64 page = addr & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
        core->getApplicationData(Core::NONE, Core::READ, page, m_data_buffer, data_size, Core::MEM_MODELED_NONE);
    }

    int total_bytes = 0;
    double compression_latency = 0;
    // TODO
    total_bytes = 64;

    assert(total_bytes <= m_page_size && "[LZ78] Wrong compression!\n");

    // Use total bytes instead of compressed cache lines for decompression
    *compressed_cache_lines = total_bytes;

    // Return compressed pages size in Bytes
    *compressed_page_size = total_bytes;

    //printf("[LZ78] Compressed Page Size: %u bytes\n", *compressed_page_size);
    if (m_compression_latency == 0)
    {
        return SubsecondTime::Zero();
    }
    return SubsecondTime::NS(compression_latency * 1000000000);
}

CompressionModelLZ78::~CompressionModelLZ78()
{
}

SubsecondTime
CompressionModelLZ78::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    // Need to get compressed data in order to decompress
    int total_bytes = 0;
    if (m_compression_granularity == -1) {
        //total_bytes = LZ4_compress_default(m_data_buffer, m_compressed_data_buffer, m_page_size, m_page_size);
    } else {
        for (int i = 0; i < m_page_size / (UInt32)m_compression_granularity; i++) {
            ;//total_bytes += LZ4_compress_default(&m_data_buffer[m_compression_granularity * i], &m_compressed_data_buffer[total_bytes], m_compression_granularity, m_page_size - total_bytes);
        }
    }

    //LZ4_decompress_safe(m_compressed_data_buffer, m_data_buffer, total_bytes, m_page_size);
    double decompression_latency = 0;

    // printf("[LZ78] %f s\n", decompression_latency);
    // FIXME
    if (m_decompression_latency == 0)
    {
        return SubsecondTime::Zero();
    }
    return SubsecondTime::NS(decompression_latency * 1000000000);
}

SubsecondTime
CompressionModelLZ78::compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    // TODO
    return SubsecondTime::Zero();
}


SubsecondTime
CompressionModelLZ78::decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    // TODO
    return SubsecondTime::Zero();
}
