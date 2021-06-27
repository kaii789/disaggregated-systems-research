#ifndef __COMPRESSION_MODEL_FVECounter_H__
#define __COMPRESSION_MODEL_FVECounter_H__

#include "compression_model.h"
#include "CAM_counter.h"
#include "bitstream.h"

class CompressionModelFVECounter : public CompressionModel
{
public:
   CompressionModelFVECounter(String name, UInt32 page_size, UInt32 cache_line_size);
   ~CompressionModelFVECounter();

   SubsecondTime compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines);
   SubsecondTime decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id);

private:
void InitBitstream(bitstream*, void*, unsigned int);
unsigned long int ReadBit(bitstream*);
void WriteBit(bitstream*, unsigned long int);
void EncodeWord( bitstream*,unsigned long int,unsigned int);
unsigned long int DecodeWord(bitstream*,unsigned int);
unsigned long int ReadWord( void*, unsigned int);
void WriteWord(void*, unsigned int,unsigned long int);
Byte* MakeCompBuf();

unsigned char _wordsize;
unsigned char _cam_size;
CAM_counter* CAM_C;
CAM_counter* CAM_D;

    UInt32 compressCacheLine(void *in, void *out);
    UInt32 decompressCacheLine(void *in, void *out);

    String m_name;
    UInt32 m_page_size;
    UInt32 m_cache_line_size;
    char *m_data_buffer;
    char *m_compressed_data_buffer;
    UInt32 *m_compressed_cache_line_sizes;
    UInt32 m_cacheline_count;

    // Compression latency per cache line
    UInt32 m_compression_latency = 10;
    // Decompression latency per cache line
    UInt32 m_decompression_latency = 10;

};

#endif /* __COMPRESSION_MODEL_FVE_H__ */
