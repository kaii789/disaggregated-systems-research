#ifndef __COMPRESSION_MODEL_FPC_H__
#define __COMPRESSION_MODEL_FPC_H__

#include "compression_model.h"
// #include "moving_average.h"
// #include "fixed_types.h"
// #include "subsecond_time.h"

class CompressionModelFPC : public CompressionModel
{
public:
   CompressionModelFPC(String name, UInt32 page_size, UInt32 cache_line_size);
   ~CompressionModelFPC();

   SubsecondTime compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines);
   SubsecondTime decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id);

private:
    String m_name;
    UInt32 m_page_size;
    UInt32 m_cache_line_size;
    char *m_data_buffer;
    char *m_compressed_data_buffer;
    UInt32 *m_compressed_cache_line_sizes;
    UInt32 m_cacheline_count;

    // Compression latency per cache line TODO: fix
    UInt32 m_compression_latency = 3;
    // Decompression latency per cache line TODO: fix
    UInt32 m_decompression_latency = 3;

    UInt32 compressCacheLine(void *in, void *out);
    UInt32 decompressCacheLine(void *in, void *out);

    // FPC
    int insize;
    long predsizem1,c_hash,d_hash,c_dhash,d_dhash;
    long long c_pred1,c_pred2,d_pred1,d_pred2,c_lastval,d_lastval;
    long long *c_fcm,*d_fcm,*c_dfcm,*d_dfcm;
    static const long long unsigned mask[8];
};

#endif /* __COMPRESSION_MODEL_FPC_H__ */