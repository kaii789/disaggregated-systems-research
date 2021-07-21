#ifndef __COMPRESSION_MODEL_FPC_H__
#define __COMPRESSION_MODEL_FPC_H__

#include "compression_model.h"

class CompressionModelFPC : public CompressionModel
{
public:
   CompressionModelFPC(String name, UInt32 page_size, UInt32 cache_line_size);
   ~CompressionModelFPC();

   SubsecondTime compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines);
   SubsecondTime decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id);

   SubsecondTime compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines);
   SubsecondTime decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines);

   void finalizeStats();

private:
    String m_name;
    UInt32 m_page_size;
    UInt32 m_cache_line_size;
    char *m_data_buffer;
    char *m_compressed_data_buffer;
    UInt32 *m_compressed_cache_line_sizes;
    UInt32 m_cacheline_count;

    // Compression latency per cache line
    UInt32 m_compression_latency = 3;
    // Decompression latency per cache line
    UInt32 m_decompression_latency = 5;

    // FPC
    static const UInt32 mask[6];
    static const UInt32 neg_check[6];

    UInt32 compressCacheLine(void *in, void *out);
    UInt32 decompressCacheLine(void *in, void *out);

};

#endif /* __COMPRESSION_MODEL_FPC_H__ */
