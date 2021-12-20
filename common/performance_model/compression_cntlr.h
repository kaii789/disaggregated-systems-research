#ifndef __COMPRESSION_CNTLR_H__
#define __COMPRESSION_CNTLR_H__

#include "compression_model.h"
#include "fixed_types.h"
#include "subsecond_time.h"

class CompressionController
{
    private:
        core_id_t m_core_id;
        bool m_r_cacheline_gran;
        UInt32 m_cache_line_size;
        UInt32 m_page_size;

        bool m_use_compression;
        bool m_use_cacheline_compression;
        bool m_use_r_compressed_pages;

        UInt64 bytes_saved = 0;
        SubsecondTime m_total_compression_latency = SubsecondTime::Zero();
        SubsecondTime m_total_decompression_latency = SubsecondTime::Zero();

        UInt64 cacheline_bytes_saved = 0;
        SubsecondTime m_total_cacheline_compression_latency = SubsecondTime::Zero();
        SubsecondTime m_total_cacheline_decompression_latency = SubsecondTime::Zero();

    public:
        CompressionModel *m_compression_model;
        CompressionModel *m_cacheline_compression_model;

        std::map<IntPtr, UInt32> address_to_compressed_size;
        std::map<IntPtr, UInt32> address_to_num_cache_lines;

        CompressionController(core_id_t core_id, bool m_r_cacheline_gran, UInt32 m_cache_line_size, UInt32 m_page_size);
        SubsecondTime compress(bool is_cacheline_compression, UInt64 address, size_t size_to_compress, UInt32 *size);
        SubsecondTime decompress(bool is_cacheline_compression, UInt64 address);
};

#endif