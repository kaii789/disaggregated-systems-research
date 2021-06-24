#include "compression_model_lz4.h"
#include <lz4.h>
#include "utils.h"
#include "config.hpp"

CompressionModelLZ4::CompressionModelLZ4(String name, UInt32 page_size, UInt32 cache_line_size, int compression_latency_config, int decompression_latency_config, double freq_norm)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
    , m_compression_granularity(Sim()->getCfg()->getInt("perf_model/dram/compression_model/compression_granularity"))
{
    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];

    // Set compression/decompression cycle latencies if configured
    if (compression_latency_config != -1)
        m_compression_latency = compression_latency_config;
    if (decompression_latency_config != -1)
        m_decompression_latency = decompression_latency_config;

    m_freq_norm = freq_norm;
}

SubsecondTime
CompressionModelLZ4::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    // Get Data
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    if (data_size == m_cache_line_size)  { // If we compress in cache_line granularity
        core->getApplicationData(Core::NONE, Core::READ, addr, m_data_buffer, data_size, Core::MEM_MODELED_NONE); // Assume addr already points to page or cache line
    } else { // If we compress in page_size granularity, we shift to move to the start_addr of the corresponding page
        UInt64 page = addr & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
        core->getApplicationData(Core::NONE, Core::READ, page, m_data_buffer, data_size, Core::MEM_MODELED_NONE);
    }

    // LZ4
    int total_bytes = 0;
    double compression_latency = 0;
    if (m_compression_granularity == -1) {
        clock_t begin = clock();
        total_bytes = LZ4_compress_default(m_data_buffer, m_compressed_data_buffer, m_page_size, m_page_size);
        clock_t end = clock();
        compression_latency = (double)(end - begin) / CLOCKS_PER_SEC;
    } else {
        for (int i = 0; i < m_page_size / (UInt32)m_compression_granularity; i++) {
            clock_t begin = clock();
            total_bytes += LZ4_compress_default(&m_data_buffer[m_compression_granularity * i], &m_compressed_data_buffer[total_bytes], m_compression_granularity, m_page_size - total_bytes);
            clock_t end = clock();
            compression_latency += (double)(end - begin) / CLOCKS_PER_SEC;
        }
    }
    // printf("[LZ4] Compression latency: %f ns\n", compression_latency * 1000000000);

    // Normalize latency
    compression_latency *= m_freq_norm;

    assert(total_bytes <= m_page_size && "[LZ4] Wrong compression!\n");

    // Use total bytes instead of compressed cache lines for decompression
    *compressed_cache_lines = total_bytes;

    // Return compressed pages size in Bytes
    *compressed_page_size = total_bytes;

    // printf("[LZ4] Compressed Page Size: %u bytes\n", total_bytes);

    // 780 MB/s compression rate
    // double compression_latency = 1 / (float)((780 * (UInt64)1000000) / m_page_size); // In seconds
    // printf("[LZ4] %f s\n", compression_latency);
    if (m_compression_latency == 0)
    {
        return SubsecondTime::Zero();
    }
    return SubsecondTime::NS(compression_latency * 1000000000);
}

CompressionModelLZ4::~CompressionModelLZ4()
{
}

SubsecondTime
CompressionModelLZ4::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    // Need to get compressed data in order to decompress
    UInt32 compressed_page_size;
    UInt32 compressed_cachelines;
    int total_bytes = 0;
    if (m_compression_granularity == -1) {
        total_bytes = LZ4_compress_default(m_data_buffer, m_compressed_data_buffer, m_page_size, m_page_size);
    } else {
        for (int i = 0; i < m_page_size / (UInt32)m_compression_granularity; i++) {
            total_bytes += LZ4_compress_default(&m_data_buffer[m_compression_granularity * i], &m_compressed_data_buffer[total_bytes], m_compression_granularity, m_page_size - total_bytes);
        }
    }

    clock_t begin = clock();
    LZ4_decompress_safe(m_compressed_data_buffer, m_data_buffer, compressed_page_size, m_page_size);
    clock_t end = clock();
    double decompression_latency = (double)(end - begin) / CLOCKS_PER_SEC;
    decompression_latency *= m_freq_norm;

    // TODO: orig
    // int compressed_size = compressed_cache_lines;
    // // 4970 MB/s compression rate
    // double decompression_latency = 1 / (float)((4970 * (UInt64)1000000) / compressed_size); // In seconds
    // // printf("[LZ4] %f s\n", decompression_latency);
    if (m_decompression_latency == 0)
    {
        return SubsecondTime::Zero();
    }
    return SubsecondTime::NS(decompression_latency * 1000000000);
}
