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

    m_low_compression_scheme = Sim()->getCfg()->getString("perf_model/dram/compression_model/adaptive/low_compression_scheme");
    m_high_compression_scheme = Sim()->getCfg()->getString("perf_model/dram/compression_model/adaptive/high_compression_scheme");
    m_low_compression_model = CompressionModel::create("Low-latency Compression Model", id, m_page_size, m_cache_line_size, m_low_compression_scheme);
    m_high_compression_model = CompressionModel::create("High-latency Compression Model", id, m_page_size, m_cache_line_size, m_high_compression_scheme);

    m_lower_bandwidth_threshold = Sim()->getCfg()->getFloat("perf_model/dram/compression_model/adaptive/lower_bandwidth_threshold");
    m_upper_bandwidth_threshold = Sim()->getCfg()->getFloat("perf_model/dram/compression_model/adaptive/upper_bandwidth_threshold");

    registerStatsMetric("compression", id, "adaptive-low-compression-count", &m_low_compression_count);
    registerStatsMetric("compression", id, "adaptive-low-total-compression-latency", &m_low_total_compression_latency);
    registerStatsMetric("compression", id, "adaptive-low-total-decompression-latency", &m_low_total_decompression_latency);
    registerStatsMetric("compression", id, "adaptive-low-bytes-saved", &m_low_bytes_saved);

    registerStatsMetric("compression", id, "adaptive-high-compression-count", &m_high_compression_count);
    registerStatsMetric("compression", id, "adaptive-high-total-compression-latency", &m_high_total_compression_latency);
    registerStatsMetric("compression", id, "adaptive-high-total-decompression-latency", &m_high_total_decompression_latency);
    registerStatsMetric("compression", id, "adaptive-high-bytes-saved", &m_high_bytes_saved);

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
        total_compression_latency = m_low_compression_model->compress(addr, data_size, core_id, &compressed_size, &compressed_cachelines);
        m_addr_to_scheme[addr] = m_low_compression_scheme;
        m_low_compression_count += 1;
        if (m_compression_latency != 0)
            m_low_total_compression_latency += total_compression_latency;
        m_low_bytes_saved += data_size - compressed_size;
    }
    else if (m_bandwidth_utilization >= m_upper_bandwidth_threshold) {
        total_compression_latency = m_high_compression_model->compress(addr, data_size, core_id, &compressed_size, &compressed_cachelines);
        m_addr_to_scheme[addr] = m_high_compression_scheme;
        m_high_compression_count += 1;
        if (m_compression_latency != 0)
            m_high_total_compression_latency += total_compression_latency;
        m_high_bytes_saved += data_size - compressed_size;
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
    SubsecondTime latency = SubsecondTime::Zero();
    if (m_addr_to_scheme[addr] == m_low_compression_scheme) {
        latency = m_low_compression_model->decompress(addr, compressed_cache_lines, core_id);
        if (m_decompression_latency != 0)
            m_low_total_decompression_latency += latency;
    }
    else if (m_addr_to_scheme[addr] == m_high_compression_scheme) {
        latency = m_high_compression_model->decompress(addr, compressed_cache_lines, core_id);
        if (m_decompression_latency != 0)
            m_high_total_decompression_latency += latency;
    }

    if (m_decompression_latency == 0)
        return SubsecondTime::Zero();
    return latency;
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
