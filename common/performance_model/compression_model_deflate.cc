#include "compression_model_deflate.h"
#include <zlib.h>
#include "utils.h"
#include "config.hpp"

CompressionModelDeflate::CompressionModelDeflate(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
    , m_compression_granularity(Sim()->getCfg()->getInt("perf_model/dram/compression_model/deflate/compression_granularity"))
{
    // Set compression/decompression cycle latencies if configured
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/deflate/compression_latency") != -1)
        m_compression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/deflate/compression_latency");
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/deflate/decompression_latency") != -1)
        m_decompression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/deflate/decompression_latency");

    if (m_compression_granularity == -1)
        m_compression_granularity = m_page_size;

    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size];
}

CompressionModelDeflate::~CompressionModelDeflate()
{
}

void
CompressionModelDeflate::finalizeStats()
{
}

SubsecondTime
CompressionModelDeflate::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    // Get Data
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    if (data_size == m_cache_line_size)  { // If we compress in cache_line granularity
        core->getApplicationData(Core::NONE, Core::READ, addr, m_data_buffer, data_size, Core::MEM_MODELED_NONE); // Assume addr already points to page or cache line
    } else { // If we compress in page_size granularity, we shift to move to the start_addr of the corresponding page
        UInt64 page = addr & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
        core->getApplicationData(Core::NONE, Core::READ, page, m_data_buffer, data_size, Core::MEM_MODELED_NONE);
    }

    // Deflate
    int total_bytes = 0;
    uLongf compressed_size = m_compression_granularity;
    for (int i = 0; i < m_page_size / (UInt32)m_compression_granularity; i++) {
        compress2((Bytef*)&m_compressed_data_buffer[total_bytes], &compressed_size, (Bytef*)&m_data_buffer[m_compression_granularity * i], (uLongf)m_compression_granularity, Z_DEFAULT_COMPRESSION);
        total_bytes += compressed_size;
    }

    // Use total bytes instead of compressed cache lines for decompression
    *compressed_cache_lines = total_bytes;

    // Return compressed pages size in Bytes
    *compressed_page_size = total_bytes;


    if (m_compression_latency == 0)
    {
        return SubsecondTime::Zero();
    }

    // 10 GB/s compression rate
    double compression_latency = 1 / (double)((10 * (UInt64)1000000000) / (double)m_page_size); // In seconds

    // printf("[Deflate] Compression latency: %f ns\n", compression_latency * 1000000000);
    //assert(total_bytes <= m_page_size && "[Deflate] Wrong compression!\n");
    // printf("[Deflate] Compressed Page Size: %u bytes\n", total_bytes);

    return SubsecondTime::NS(compression_latency * 1000000000);
}


SubsecondTime
CompressionModelDeflate::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    int compressed_size = compressed_cache_lines;
    // 10 GB/s decompression rate
    double decompression_latency = 1 / (double)((10 * (UInt64)1000000000) / (double)compressed_size); // In seconds
    // printf("[Deflate] %f ns\n", decompression_latency * 1000000000);

    if (m_decompression_latency == 0)
    {
        return SubsecondTime::Zero();
    }
    return SubsecondTime::NS(decompression_latency * 1000000000);
}

SubsecondTime
CompressionModelDeflate::compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    if (!multipage_data_buffer)
        multipage_data_buffer = new char[m_page_size * num_pages];
    if (!multipage_compressed_buffer) {
        multipage_compressed_buffer = new char[m_page_size * num_pages];
    }
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);

    // Get data into data buffer
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        core->getApplicationData(Core::NONE, Core::READ, addr, &multipage_data_buffer[m_page_size * i], m_page_size, Core::MEM_MODELED_NONE);
    }

    // Deflate
    uLongf compressed_size = 0;
    compress2((Bytef*)&multipage_compressed_buffer, &compressed_size, (Bytef*)&multipage_data_buffer, (uLongf)m_compression_granularity, Z_DEFAULT_COMPRESSION);
    // 10 GB/s compression rate
    double compression_latency = 1 / (double)((10 * (UInt64)1000000000) / (double)(m_page_size * num_pages)); // In seconds

    *compressed_multipage_size = compressed_size;

    if (m_compression_latency == 0)
    {
        return SubsecondTime::Zero();
    }
    return SubsecondTime::NS(compression_latency * 1000000000);
}


SubsecondTime
CompressionModelDeflate::decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    // 10 GB/s decompression rate
    double decompression_latency = 1 / (double)((10 * (UInt64)1000000000) / (double)(m_page_size * num_pages)); // In seconds

    if (m_decompression_latency == 0)
    {
        return SubsecondTime::Zero();
    }
    return SubsecondTime::NS(decompression_latency * 1000000000);
}