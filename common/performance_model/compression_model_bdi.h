#ifndef __COMPRESSION_MODEL_BDI_H__
#define __COMPRESSION_MODEL_BDI_H__

#include "compression_model.h"
#include "moving_average.h"
#include "fixed_types.h"
#include "subsecond_time.h"

// BDI.cc
#include <climits>
#include <cstdio>
#include <cstring>
#include <boost/tuple/tuple.hpp>

class CompressionModelBDI : public CompressionModel
{
public:
   CompressionModelBDI(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size);
   ~CompressionModelBDI();

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
    UInt32 m_options;
    struct m_compress_info {
       bool is_compressible; 
       UInt32 compressed_size; // In bytes
    } ;

    // Compression latency per cache line 
    UInt32 m_compression_latency = 3; 
    // Decompression latency per cache line
    UInt32 m_decompression_latency = 3; 
    SInt32 m_compression_granularity;

    bool use_additional_options;


    SInt64 readWord(void*, UInt32, UInt32);
    void writeWord(void*, UInt32, SInt64, UInt32);
    void zeroValues(void *, m_compress_info *, void *);
    void repeatedValues(void *, m_compress_info *, void *, UInt32);
    void specializedCompress(void *, m_compress_info *, void *, SInt32, SInt32);
    bool checkDeltaLimits(SInt64, UInt32);
    UInt32 compressCacheLine(void *in, void *out);
    //UInt32 decompressCacheLine(void *in, void *out);

    // Statistics
    UInt64 m_total_compressed;
    UInt64 m_compress_options[13] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    UInt64 m_bytes_saved_per_option[13] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};

};

#endif /* __COMPRESSION_MODEL_BDI_H__ */
