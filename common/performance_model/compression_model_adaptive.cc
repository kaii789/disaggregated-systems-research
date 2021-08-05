#include "compression_model_adaptive.h"
#include "utils.h"
#include "config.hpp"
#include "stats.h"

CompressionModelAdaptive::CompressionModelAdaptive(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
{
    // Set compression/decompression cycle latencies if configured
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/adaptive/compression_latency") != -1)
        m_compression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/adaptive/compression_latency");
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/adaptive/decompression_latency") != -1)
        m_decompression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/adaptive/decompression_latency");

    m_cacheline_compression_scheme = Sim()->getCfg()->getString("perf_model/dram/compression_model/adaptive/cacheline_compression_scheme");
    m_dict_compression_scheme = Sim()->getCfg()->getString("perf_model/dram/compression_model/adaptive/dict_compression_scheme");
    m_cacheline_compression_model = CompressionModel::create("Cacheline Compression Model", id, m_page_size, m_cache_line_size, m_cacheline_compression_scheme);
    m_dict_compression_model = CompressionModel::create("Dictionary Compression Model", id, m_page_size, m_cache_line_size, m_dict_compression_scheme);

    m_lower_bandwidth_threshold = Sim()->getCfg()->getFloat("perf_model/dram/compression_model/adaptive/lower_bandwidth_threshold");
    m_upper_bandwidth_threshold = Sim()->getCfg()->getFloat("perf_model/dram/compression_model/adaptive/upper_bandwidth_threshold");

    registerStatsMetric("compression", id, "adaptive-cacheline-compression-count", &m_cacheline_compression_count);
    registerStatsMetric("compression", id, "adaptive-dict-compression-count", &m_dict_compression_count);

    m_cacheline_count = m_page_size / m_cache_line_size;
}

CompressionModelAdaptive::~CompressionModelAdaptive()
{
}

void
CompressionModelAdaptive::finalizeStats()
{
}

// TODO:
SubsecondTime
CompressionModelAdaptive::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    UInt32 compressed_cachelines = 0;
    UInt32 compressed_size = data_size;
    SubsecondTime total_compression_latency = SubsecondTime::Zero();

    // Compress depending on bandwidth
    if (m_bandwidth_utilization >= m_lower_bandwidth_threshold && m_bandwidth_utilization < m_upper_bandwidth_threshold) {
        total_compression_latency = m_cacheline_compression_model->compress(addr, data_size, core_id, &compressed_size, &compressed_cachelines);
        m_addr_to_scheme[addr] = m_cacheline_compression_scheme;
        m_cacheline_compression_count += 1;
    }
    else if (m_bandwidth_utilization >= m_upper_bandwidth_threshold) {
        total_compression_latency = m_dict_compression_model->compress(addr, data_size, core_id, &compressed_size, &compressed_cachelines);
        m_addr_to_scheme[addr] = m_dict_compression_scheme;
        m_dict_compression_count += 1;
    }

    // assert(compressed_size <= m_page_size && "[Adaptive] Wrong compression!");

    *compressed_page_size = compressed_size;
    *compressed_cache_lines = compressed_cachelines;

    // Return compression latency
    if (m_compression_latency == 0)
        return SubsecondTime::Zero();
    return total_compression_latency;
}

// TODO:
SubsecondTime
CompressionModelAdaptive::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    if (m_addr_to_scheme[addr] == m_cacheline_compression_scheme)
        return m_cacheline_compression_model->decompress(addr, compressed_cache_lines, core_id);
    else if (m_addr_to_scheme[addr] == m_dict_compression_scheme)
        return m_dict_compression_model->decompress(addr, compressed_cache_lines, core_id);

    return SubsecondTime::Zero();
}

void
CompressionModelAdaptive::update_bandwidth_utilization(double bandwidth_utilization)
{
    m_bandwidth_utilization = bandwidth_utilization;
    // printf("[Adaptive] %f\n", m_bandwidth_utilization);
}

SubsecondTime
CompressionModelAdaptive::compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    UInt32 total_compressed_size = 0;
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        UInt32 compressed_page_size;
        UInt32 compressed_cache_lines;
        total_compression_latency += CompressionModelAdaptive::compress(addr, m_page_size, core_id, &compressed_page_size, &compressed_cache_lines);
        total_compressed_size += compressed_page_size;
        (*address_to_num_cache_lines)[addr] = compressed_cache_lines;
    }
    *compressed_multipage_size = total_compressed_size;
    return total_compression_latency;
}

SubsecondTime
CompressionModelAdaptive::decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        total_compression_latency += CompressionModelAdaptive::decompress(addr, (*address_to_num_cache_lines)[addr], core_id);
    }
    return total_compression_latency;
}