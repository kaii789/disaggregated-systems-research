#ifndef __COMPRESSION_MODEL_LZ78_H__
#define __COMPRESSION_MODEL_LZ78_H__

#include "compression_model.h"
#include "CAM_lz.h"
#include <string>
#include <map>
#include <vector>
#include <list>
#include <algorithm>


using namespace std;

class CompressionModelLZ78 : public CompressionModel
{
public:
   CompressionModelLZ78(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size);
   ~CompressionModelLZ78();

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
    UInt32 m_cacheline_count;
    char *multipage_data_buffer;
    char *multipage_compressed_buffer;

    // Compression latency per CAM access in cycles
    UInt32 m_compression_latency = 0;
    // Decompression latency per CAM access in cycles
    UInt32 m_decompression_latency = 0;
    // Fine-grain compression granularity within the page
    UInt8 m_word_size = 1;
    SInt32 m_compression_granularity;
    
    CAMLZ *compression_CAM; 
    bool m_size_limit;

    SInt64 readWord(void*, UInt32, UInt32);
    void writeWord(void*, UInt32, SInt64, UInt32);
    UInt32 compressData(void *, void *, UInt32, UInt32 *);

    // Statistics
    UInt64 m_num_compress_pages;
    UInt64 m_sum_dict_size;
    UInt64 m_avg_dict_size = 0;
    UInt64 m_max_dict_size;
    UInt64 m_sum_max_dict_entry;
    UInt64 m_avg_max_dict_entry = 0;
    UInt64 m_sum_avg_dict_entry;
    UInt64 m_avg_avg_dict_entry = 0;
    UInt64 m_max_dict_entry;
    UInt64 m_num_overflowed_pages;
    const UInt32 m_dictsize_saved_stats_num_points = 10;  // the number of percentiles (from above 0% to including 100%)
    std::map<UInt32, UInt64> m_dictsize_saved_map; // track number of bytes saved for each particular dictionary size
    std::map<UInt32, UInt64> m_dictsize_accesses_map; // track number of accesses for each particular dictionary size
    std::map<UInt32, UInt32> m_dictsize_max_entry_map; // track max_entry size in bytes for each particular dictionary size
    std::vector<UInt64> dictsize_count_stats;
    std::vector<UInt64> bytes_saved_count_stats;
    std::vector<UInt64> accesses_count_stats;
    std::vector<UInt64> max_entry_bytes_count_stats;

};

#endif /* __COMPRESSION_MODEL_LZ78_H__ */
