#include "compression_cntlr.h"
#include "utils.h"
#include "config.hpp"
#include "stats.h"

CompressionController::CompressionController(core_id_t core_id, bool r_cacheline_gran, UInt32 cache_line_size, UInt32 page_size)
{
    m_core_id = core_id;
    m_r_cacheline_gran = r_cacheline_gran;
    m_cache_line_size = cache_line_size;
    m_page_size = page_size;

    m_use_compression = Sim()->getCfg()->getBool("perf_model/dram/compression_model/use_compression");
    m_use_cacheline_compression = Sim()->getCfg()->getBool("perf_model/dram/compression_model/cacheline/use_cacheline_compression");
    m_use_r_compressed_pages = Sim()->getCfg()->getBool("perf_model/dram/compression_model/use_r_compressed_pages");
    if (m_use_compression) {
        String compression_scheme = Sim()->getCfg()->getString("perf_model/dram/compression_model/compression_scheme");
        UInt32 gran_size = (m_r_cacheline_gran) ? m_cache_line_size : m_page_size;

        m_compression_model = CompressionModel::create("Link Compression Model", core_id, gran_size, m_cache_line_size, compression_scheme);
        registerStatsMetric("compression", core_id, "bytes-saved", &bytes_saved);
        registerStatsMetric("compression", core_id, "total-compression-latency", &m_total_compression_latency);
        registerStatsMetric("compression", core_id, "total-decompression-latency", &m_total_decompression_latency);

        // Cacheline Compression
        if (m_use_cacheline_compression) {
            String cacheline_compression_scheme = Sim()->getCfg()->getString("perf_model/dram/compression_model/cacheline/compression_scheme");
            m_cacheline_compression_model = CompressionModel::create("Cacheline Link Compression Model", core_id, m_cache_line_size, m_cache_line_size, cacheline_compression_scheme);
            registerStatsMetric("compression", core_id, "cacheline-bytes-saved", &cacheline_bytes_saved);
            registerStatsMetric("compression", core_id, "total-cacheline-compression-latency", &m_total_cacheline_compression_latency);
            registerStatsMetric("compression", core_id, "total-cacheline-decompression-latency", &m_total_cacheline_decompression_latency);
        }
    }

    //     // Compression Stats
    // if (m_use_compression) {
    //     m_compression_model->finalizeStats();
    //     // if (m_use_cacheline_compression)
    //     //     m_cacheline_compression_model->finalizeStats();
    // }
}

SubsecondTime
CompressionController::compress(bool is_cacheline_compression, UInt64 address, size_t size_to_compress, UInt32 *size)
{
    CompressionModel *compression_model = (is_cacheline_compression) ? m_cacheline_compression_model : m_compression_model;

    UInt32 compressed_cache_lines;
    SubsecondTime compression_latency = compression_model->compress(address, size_to_compress, m_core_id, size, &compressed_cache_lines);
    UInt32 size_val = *size;
    if (size_to_compress > size_val) {
        if (!is_cacheline_compression)
            bytes_saved += size_to_compress - size_val;
        else
            cacheline_bytes_saved += size_to_compress - size_val;
    }
    else {
        if (!is_cacheline_compression)
            bytes_saved -= size_val - size_to_compress;
        else
            cacheline_bytes_saved -= size_val - size_to_compress;
    }

    if (!is_cacheline_compression)
        address_to_compressed_size[address] = size_val;
    address_to_num_cache_lines[address] = compressed_cache_lines;

    if (!is_cacheline_compression)
        m_total_compression_latency += compression_latency;
    else
        m_total_cacheline_compression_latency += compression_latency;

    return compression_latency;
}

SubsecondTime
CompressionController::decompress(bool is_cacheline_compression, UInt64 address)
{
    CompressionModel *compression_model = (is_cacheline_compression) ? m_cacheline_compression_model : m_compression_model;

    SubsecondTime decompression_latency = compression_model->decompress(address, address_to_num_cache_lines[address], m_core_id);
    if (!is_cacheline_compression)
        m_total_decompression_latency += decompression_latency;
    else
        m_total_cacheline_decompression_latency += decompression_latency;

    return decompression_latency;
}