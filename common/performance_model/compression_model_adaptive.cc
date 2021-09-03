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

    m_type = Sim()->getCfg()->getInt("perf_model/dram/compression_model/adaptive/type");
    m_low_compression_scheme = Sim()->getCfg()->getString("perf_model/dram/compression_model/adaptive/low_compression_scheme");
    m_high_compression_scheme = Sim()->getCfg()->getString("perf_model/dram/compression_model/adaptive/high_compression_scheme");
    m_low_compression_model = CompressionModel::create("Low-latency Compression Model", id, m_page_size, m_cache_line_size, m_low_compression_scheme);
    m_high_compression_model = CompressionModel::create("High-latency Compression Model", id, m_page_size, m_cache_line_size, m_high_compression_scheme);

    // Fixed BW Threshold
    m_lower_bandwidth_threshold = Sim()->getCfg()->getFloat("perf_model/dram/compression_model/adaptive/lower_bandwidth_threshold");
    m_upper_bandwidth_threshold = Sim()->getCfg()->getFloat("perf_model/dram/compression_model/adaptive/upper_bandwidth_threshold");

    // Estimator
    m_type_switch_threshold = Sim()->getCfg()->getInt("perf_model/dram/compression_model/adaptive/latency_estimator/type_switch_threshold");

    // Dynamic BW Threshold
    m_high_compression_rate = Sim()->getCfg()->getFloat("perf_model/dram/compression_model/adaptive/dynamic_bw_threshold/high_compression_rate");

    registerStatsMetric("compression", id, "adaptive-low-compression-count", &m_low_compression_count);
    registerStatsMetric("compression", id, "adaptive-low-total-compression-latency", &m_low_total_compression_latency);
    registerStatsMetric("compression", id, "adaptive-low-total-decompression-latency", &m_low_total_decompression_latency);
    registerStatsMetric("compression", id, "adaptive-low-bytes-saved", &m_low_bytes_saved);

    registerStatsMetric("compression", id, "adaptive-high-compression-count", &m_high_compression_count);
    registerStatsMetric("compression", id, "adaptive-high-total-compression-latency", &m_high_total_compression_latency);
    registerStatsMetric("compression", id, "adaptive-high-total-decompression-latency", &m_high_total_decompression_latency);
    registerStatsMetric("compression", id, "adaptive-high-bytes-saved", &m_high_bytes_saved);

    // Stats for BW utilization
    for (int i = 0; i < 10; i++) {
        m_bw_utilization_decile_to_count[i] = 0;
        registerStatsMetric("compression", id, ("adaptive-bw-utilization-decile-" + std::to_string(i)).c_str(), &m_bw_utilization_decile_to_count[i]);
    }

    m_cacheline_count = m_page_size / m_cache_line_size;
}

CompressionModelAdaptive::~CompressionModelAdaptive()
{
}

void
CompressionModelAdaptive::finalizeStats()
{
}

void
CompressionModelAdaptive::update_bw_utilization_count()
{
    int decile = (int)(m_bandwidth_utilization * 10);
    m_bw_utilization_decile_to_count[decile] += 1;
}

// TODO:
SubsecondTime
CompressionModelAdaptive::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    update_bw_utilization_count();

    UInt32 high_compressed_cachelines = 0;
    UInt32 high_compressed_size = data_size;
    SubsecondTime high_compression_latency = SubsecondTime::Zero();

    UInt32 low_compressed_cachelines = 0;
    UInt32 low_compressed_size = data_size;
    SubsecondTime low_compression_latency = SubsecondTime::Zero();

    SubsecondTime compression_latency = SubsecondTime::Zero();

    int type = m_type;
    if ((type == 1 || type == 3) && (m_low_compression_count < m_type_switch_threshold || m_high_compression_count < m_type_switch_threshold))
        type = 2;

    bool use_low_compression;
    bool use_high_compression;
    if (type == 0) {
        // Fixed BW Threshold
        use_low_compression = m_bandwidth_utilization >= m_lower_bandwidth_threshold && m_bandwidth_utilization < m_upper_bandwidth_threshold;
        use_high_compression = m_bandwidth_utilization >= m_upper_bandwidth_threshold;
    } else if (type == 1) {
        // Compression latency + queuing latency predictor
        // use_low_compression
        // use_high_compression

        SubsecondTime estimate_low_compression_latency = SubsecondTime::NS((double)m_low_total_compression_latency.getNS() / (double)m_low_compression_count);
        UInt32 estimate_low_compressed_size = (m_low_compression_count * m_page_size - m_low_bytes_saved) / m_low_compression_count;
        SubsecondTime estimate_low_queuing_delay = m_queue_model->computeQueueDelayAfterAddNoEffect(m_t_now, m_r_bandwidth->getRoundedLatency(8*estimate_low_compressed_size), m_requester);

        SubsecondTime estimate_high_compression_latency = SubsecondTime::NS((double)m_high_total_compression_latency.getNS() / (double)m_high_compression_count);
        UInt32 estimate_high_compressed_size = (m_high_compression_count * m_page_size - m_high_bytes_saved) / m_high_compression_count;
        SubsecondTime estimate_high_queuing_delay = m_queue_model->computeQueueDelayAfterAddNoEffect(m_t_now, m_r_bandwidth->getRoundedLatency(8*estimate_high_compressed_size), m_requester);

        // printf("[Adaptive] lcl: %lu, lqd: %lu, hcl: %lu, hqd: %lu\n", estimate_low_compression_latency.getNS(), estimate_low_queuing_delay.getNS(), estimate_high_compression_latency.getNS(), estimate_high_queuing_delay.getNS());

        use_low_compression = estimate_low_compression_latency + estimate_low_queuing_delay < estimate_high_compression_latency + estimate_high_queuing_delay;
        use_high_compression = !use_low_compression;
    } else if (type == 2) {
        double dynamic_bw_threshold = 0.8;
        if (m_high_compression_rate >= 5) {
            dynamic_bw_threshold = 0.6;
        } else if (m_high_compression_rate >= 2) {
            dynamic_bw_threshold = 0.7;
        }
        m_upper_bandwidth_threshold = dynamic_bw_threshold;
        use_low_compression = m_bandwidth_utilization >= m_lower_bandwidth_threshold && m_bandwidth_utilization < m_upper_bandwidth_threshold;
        use_high_compression = m_bandwidth_utilization >= m_upper_bandwidth_threshold;
    } else if (type == 3) {
        // Encourage low compression at lower bandwidth saturation
        double weight_low = 1;
        if (m_bandwidth_utilization < 0.2) {
            weight_low = 4;
        } else if (m_bandwidth_utilization < 0.4) {
            weight_low = 2;
        } else if (m_bandwidth_utilization < 0.6) {
            weight_low = 1.5;
        }

        int window_capacity = m_type_switch_threshold;

        // double estimate_low_compression_ratio = (double)(m_low_compression_count * m_page_size) / (double)(m_low_compression_count * m_page_size - m_low_bytes_saved);
        double estimate_low_compression_ratio = low_compression_ratio_sum / window_capacity;
        double estimate_low_compression_latency = m_low_total_compression_latency.getNS() / (double)m_low_compression_count;
        double estimate_low_compression_rate = ((double)4000) / estimate_low_compression_latency; // GB/s
        double bandwidth = (double)(m_r_bandwidth->getBandwidthBitsPerUs()) / 8000; // GB/s
        double effective_low_data_rate = std::min(estimate_low_compression_rate, weight_low * estimate_low_compression_ratio * (1 - m_bandwidth_utilization) * bandwidth);

        // Encourage high compression at higher bandwidth saturation
        double weight_high = 1;
        if (m_bandwidth_utilization >= 0.8) {
            weight_high = 2;
        } else if (m_bandwidth_utilization >= 0.7) {
            weight_high = 1.5;
        }
        // else if (m_bandwidth_utilization >= 0.6) {
        //     weight_high = 1.5;
        // }

        // It is possible that the compression ratio of high compression improves later on, but
        // we don't catch this if the compression ratio of high compression isn't so good early on
        // double compression_weight_high = 1;
        // if (m_bandwidth_utilization >= 0.6) {
        //     compression_weight_high = 1.5;
        // }

        // double estimate_high_compression_ratio = (double)(m_high_compression_count * m_page_size) / (double)(m_high_compression_count * m_page_size - m_high_bytes_saved);
        double estimate_high_compression_ratio = high_compression_ratio_sum / window_capacity;
        double estimate_high_compression_latency = m_high_total_compression_latency.getNS() / (double)m_high_compression_count;
        double estimate_high_compression_rate = ((double)4000) / estimate_high_compression_latency;
        double effective_high_data_rate = std::min(weight_high * estimate_high_compression_rate, estimate_high_compression_ratio * (1 - m_bandwidth_utilization) * bandwidth);

        use_low_compression = effective_low_data_rate > effective_high_data_rate;
        use_high_compression = !use_low_compression;

        // printf("[Adaptive] low latency: %f, low compression ratio: %f, low compression rate: %f, bandwidth: %f\n", estimate_low_compression_latency, estimate_low_compression_ratio, estimate_low_compression_rate, bandwidth);
        // printf("[Adaptive] high compression ratio: %f, high compression rate: %f, bandwidth: %f\n", estimate_high_compression_ratio, estimate_high_compression_rate, bandwidth);
    }

    // Compress
    low_compression_latency = m_low_compression_model->compress(addr, data_size, core_id, &low_compressed_size, &low_compressed_cachelines);
    m_addr_to_scheme[addr] = m_low_compression_scheme;
    m_low_compression_count += 1;
    if (m_compression_latency != 0)
        m_low_total_compression_latency += low_compression_latency;
    m_low_bytes_saved += data_size - low_compressed_size;

    high_compression_latency = m_high_compression_model->compress(addr, data_size, core_id, &high_compressed_size, &high_compressed_cachelines);
    m_addr_to_scheme[addr] = m_high_compression_scheme;
    m_high_compression_count += 1;
    if (m_compression_latency != 0)
        m_high_total_compression_latency += high_compression_latency;
    m_high_bytes_saved += data_size - high_compressed_size;

    // assert(compressed_size <= m_page_size && "[Adaptive] Wrong compression!");

    if (use_low_compression) {
        *compressed_page_size = low_compressed_size;
        *compressed_cache_lines = low_compressed_cachelines;
        compression_latency = low_compression_latency;
    } else if (use_high_compression) {
        *compressed_page_size = high_compressed_size;
        *compressed_cache_lines = high_compressed_cachelines;
        compression_latency = high_compression_latency;
    }

    // Update compression ratio window for type 3
    if (type == 3) {
        int window_capacity = m_type_switch_threshold;

        double high_compression_ratio = (double)m_page_size / (double)high_compressed_size;
        high_compression_ratio_window.push(high_compression_ratio);
        high_compression_ratio_sum += high_compression_ratio;
        if (high_compression_ratio_window.size() > window_capacity) {
            high_compression_ratio_sum -= high_compression_ratio_window.front();
            high_compression_ratio_window.pop();
        }

        double low_compression_ratio = (double)m_page_size / (double)low_compressed_size;
        low_compression_ratio_window.push(low_compression_ratio);
        low_compression_ratio_sum += low_compression_ratio;
        if (low_compression_ratio_window.size() > window_capacity) {
            low_compression_ratio_sum -= low_compression_ratio_window.front();
            low_compression_ratio_window.pop();
        }
    }

    // Return compression latency
    if (m_compression_latency == 0)
        return SubsecondTime::Zero();
    return compression_latency;
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

void
CompressionModelAdaptive::update_queue_model(QueueModel* queue_model, SubsecondTime t_now, ComponentBandwidth *bandwidth, core_id_t requester)
{
    m_queue_model = queue_model;
    m_t_now = t_now;
    m_r_bandwidth = bandwidth;
    m_requester = requester;
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
