#ifndef __COMPRESSION_MODEL_FVE_H__
#define __COMPRESSION_MODEL_FVE_H__

#include "compression_model.h"
#include "CAM.h"

class CompressionModelFVE : public CompressionModel
{
    public:
        CompressionModelFVE(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size);
        ~CompressionModelFVE();

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
        UInt32 m_compression_latency = 10;
        // Decompression latency per cache line
        UInt32 m_decompression_latency = 10;

        UInt8 m_word_size_bits = 32;
        UInt32 m_word_size_bytes = 4;
        UInt8 m_cam_size = 64;
        CAM* compression_CAM;
        CAM* decompression_CAM;

        typedef struct {
            UInt8 *byte_ptr;
            UInt32  bit_pos;
            UInt32  num_bytes;
        } bitstream;

        void initBitstream(bitstream*, void*, UInt32);
        UInt64 readBit(bitstream*);
        void writeBit(bitstream*, UInt64);
        void encodeWord(bitstream*, UInt64, UInt32);
        UInt64 decodeWord(bitstream*, UInt32);
        SInt64 readWord(void*, UInt32, UInt32);
        void writeWord(void*, UInt32, SInt64, UInt32);

        UInt32 compressCacheLine(void *in, void *out);
        UInt32 decompressCacheLine(void *in, void *out);
};

#endif /* __COMPRESSION_MODEL_FVE_H__ */
