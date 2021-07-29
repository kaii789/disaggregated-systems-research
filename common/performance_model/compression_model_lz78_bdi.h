#ifndef __COMPRESSION_MODEL_LZ78_BDI_H__
#define __COMPRESSION_MODEL_LZ78_BDI_H__

#include "compression_model.h"
#include <string>
#include <map>
#include <climits>
#include <cstdio>
#include <cstring>
#include <boost/tuple/tuple.hpp>


using namespace std;

class CompressionModelLZ78BDI : public CompressionModel
{
public:
   CompressionModelLZ78BDI(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size);
   ~CompressionModelLZ78BDI();

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

    // Compression latency per CAM access
    UInt32 m_compression_latency = 0;
    // Decompression latency per CAM access
    UInt32 m_decompression_latency = 0;
    // Fine-grain compression granularity within the page
    UInt8 m_word_size = 1;
    SInt32 m_compression_granularity;
    UInt8 m_cam_size = 256;
    UInt8 m_cam_size_log2 = 8;
    
    std::map<string, UInt32> compression_CAM; 

    char *m_cacheline_buffer;
    UInt32 m_options = 8;
    UInt64 m_compress_options[12] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    struct m_compress_info {
       bool is_compressible; 
       UInt32 compressed_size; // In bytes
    } ;
    void zeroValues(void *, m_compress_info *, void *);
    void repeatedValues(void *, m_compress_info *, void *);
    void specializedCompress(void *, m_compress_info *, void *, SInt32, SInt32);
    bool checkDeltaLimits(SInt64, UInt32);
    UInt32 compressCacheLine(void *in, void *out);


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

};

#endif /* __COMPRESSION_MODEL_LZ78_BDI_H__ */
