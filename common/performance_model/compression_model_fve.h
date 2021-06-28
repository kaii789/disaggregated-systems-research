#ifndef __COMPRESSION_MODEL_FVE_H__
#define __COMPRESSION_MODEL_FVE_H__

#include "compression_model.h"
#include "CAM.h"
#include "bitstream.h"



class CompressionModelFVE : public CompressionModel
{
    public:
        CompressionModelFVE(String name, UInt32 page_size, UInt32 cache_line_size);
        ~CompressionModelFVE();

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

        // Compression latency per cache line
        UInt32 m_compression_latency = 10;
        // Decompression latency per cache line
        UInt32 m_decompression_latency = 10;

        UInt32 compressCacheLine(void *in, void *out);
        UInt32 decompressCacheLine(void *in, void *out);

        SInt64 readWord(void*, UInt32, UInt32);
        void writeWord(void*, UInt32, SInt64, UInt32);
 
        void InitBitstream(bitstream*, void*, unsigned int);
        unsigned long int ReadBit(bitstream*);
        void WriteBit(bitstream*, unsigned long int);
        void EncodeWord( bitstream*,unsigned long int,unsigned int);
        unsigned long int DecodeWord(bitstream*,unsigned int);

        unsigned char _wordsize;
        UInt32 m_word_size;
        unsigned char _cam_size;
        CAM* CAM_C;
        CAM* CAM_D;
        Byte* MakeCompBuf();


};

#endif /* __COMPRESSION_MODEL_FVE_H__ */
