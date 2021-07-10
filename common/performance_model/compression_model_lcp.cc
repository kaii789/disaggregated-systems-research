#include "compression_model_lcp.h"
#include "utils.h"
#include "config.hpp"

CompressionModelLCP::CompressionModelLCP(String name, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
{
    // Set compression/decompression cycle latencies if configured
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lcp/compression_latency") != -1)
        m_compression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/fpc/compression_latency");
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lcp/decompression_latency") != -1)
        m_decompression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/fpc/decompression_latency");

    String compression_scheme = Sim()->getCfg()->getString("perf_model/dram/compression_model/lcp/compression_scheme");
    m_compression_model = CompressionModel::create("Cacheline Compression Model", m_cache_line_size, m_cache_line_size, compression_scheme);

    m_cacheline_count = m_page_size / m_cache_line_size;
    m_compressed_cache_line_sizes = new UInt32[m_cacheline_count];

}

SubsecondTime
CompressionModelLCP::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    UInt32 total_bytes_check = 0;
    SubsecondTime total_compression_latency = SubsecondTime::Zero();

    // Step 1: Compress using cacheline compression algo
    for (UInt32 i = 0; i < m_cacheline_count; i++)
    {
        UInt32 compressed_cache_lines; // Dummy var
        total_compression_latency += m_compression_model->compress(addr + i * m_cache_line_size, m_cache_line_size, core_id, &m_compressed_cache_line_sizes[i], &compressed_cache_lines);

        total_bytes_check += m_compressed_cache_line_sizes[i];
    }
    assert(total_bytes_check <= m_page_size && "[LCP] Wrong compression!");

    // Step 2: Check for each target compressed cache line size the smallest total compressed page size
    UInt32 total_compressed_cache_lines = 0;
    UInt32 total_bytes = UINT32_MAX;
    for (int i = 0; i < 4; i++) {
        UInt32 target = m_target_compressed_cacheline_size[i];
        UInt32 compressed_cache_lines = 0;
        UInt32 compressed_size = target * m_cacheline_count + 64; // Init w/ compressed data region + metadata region size

        // Account for exception storage region
        for (int j = 0; j < m_cacheline_count; j++) {
            if (m_compressed_cache_line_sizes[j] > target) {
                compressed_size += m_compressed_cache_line_sizes[j];
            } else {
                compressed_cache_lines += 1;
            }
        }

        // Choose current target when compressed size is smaller or no bigger and has less to compress
        if ((compressed_size < total_bytes) || (compressed_size <= total_bytes && compressed_cache_lines < total_compressed_cache_lines)) {
            total_bytes = compressed_size;
            total_compressed_cache_lines = compressed_cache_lines;
        }
    }
    assert(total_bytes <= m_page_size && "[LCP] Wrong compression!");

    // Return compressed cache lines
    *compressed_cache_lines = total_compressed_cache_lines;

    // Return compressed pages size in Bytes
    *compressed_page_size = total_bytes;

    // printf("[LCP Compression] Compressed Page Size: %u bytes", total_bytes);

    // Return compression latency
    if (m_compression_latency == 0)
        return SubsecondTime::Zero();
    return total_compression_latency;
}

CompressionModelLCP::~CompressionModelLCP()
{
    delete [] m_compressed_cache_line_sizes;
}

SubsecondTime
CompressionModelLCP::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    return m_compression_model->decompress(addr, compressed_cache_lines, core_id);
}

SubsecondTime
CompressionModelLCP::compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    UInt32 total_compressed_size = 0;
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        UInt32 compressed_page_size;
        UInt32 compressed_cache_lines;
        total_compression_latency += CompressionModelLCP::compress(addr, m_page_size, core_id, &compressed_page_size, &compressed_cache_lines);
        total_compressed_size += compressed_page_size;
        (*address_to_num_cache_lines)[addr] = compressed_cache_lines;
    }
    *compressed_multipage_size = total_compressed_size;
    return total_compression_latency;
}


SubsecondTime
CompressionModelLCP::decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        total_compression_latency += CompressionModelLCP::decompress(addr, (*address_to_num_cache_lines)[addr], core_id);
    }
    return total_compression_latency;
}