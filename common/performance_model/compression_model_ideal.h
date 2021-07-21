#ifndef __COMPRESSION_MODEL_IDEAL_H__
#define __COMPRESSION_MODEL_IDEAL_H__

#include "compression_model.h"
#include "moving_average.h"
#include "fixed_types.h"
#include "subsecond_time.h"


class CompressionModelIdeal : public CompressionModel
{
public:
   CompressionModelIdeal(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size);
   ~CompressionModelIdeal();

   SubsecondTime compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines);
   SubsecondTime decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id);

   SubsecondTime compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines);
   SubsecondTime decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines);

   void finalizeStats();

private:
    String m_name; 
    UInt32 m_page_size; 
    UInt32 m_cache_line_size;
    UInt32 m_cacheline_count;
    UInt32 m_compressed_page_size;

    // Compression latency per cache line
    UInt32 m_compression_latency = 1; 
    // Decompression latency per cache line
    UInt32 m_decompression_latency = 1; 

};

#endif /* __COMPRESSION_MODEL_IDEAL_H__ */
