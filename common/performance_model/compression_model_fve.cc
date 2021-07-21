#include "compression_model_fve.h"
#include "utils.h"
#include "config.hpp"


CompressionModelFVE::CompressionModelFVE(String name, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
      , m_cache_line_size(cache_line_size)
{
    // Set compression/decompression cycle latencies if configured
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/fve/compression_latency") != -1)
        m_compression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/fve/compression_latency");
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/fve/decompression_latency") != -1)
        m_decompression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/fve/decompression_latency");

    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];
    m_compressed_cache_line_sizes = new UInt32[m_cacheline_count];

    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/fve/word_size_bits") != -1) {
        m_word_size_bits = Sim()->getCfg()->getInt("perf_model/dram/compression_model/fve/word_size_bits");
        m_word_size_bytes = m_word_size_bits / 8;
    }

    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/fve/dict_table_entries") != -1) {
        m_cam_size = (UInt8) Sim()->getCfg()->getInt("perf_model/dram/compression_model/fve/dict_table_entries");
    }

    compression_CAM = new CAM(m_cam_size);
    decompression_CAM = new CAM(m_cam_size);
}

CompressionModelFVE::~CompressionModelFVE()
{
    delete compression_CAM;
    delete decompression_CAM;
}

void CompressionModelFVE::finalizeStats()
{

}


SubsecondTime
CompressionModelFVE::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    // Get Data
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    if (data_size == m_cache_line_size)  { // If we compress in cache_line granularity
        core->getApplicationData(Core::NONE, Core::READ, addr, m_data_buffer, data_size, Core::MEM_MODELED_NONE); // Assume addr already points to page or cache line
    } else { // If we compress in page_size granularity, we shift to move to the start_addr of the corresponding page
        UInt64 page = addr & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
        core->getApplicationData(Core::NONE, Core::READ, page, m_data_buffer, data_size, Core::MEM_MODELED_NONE);
    }

    // 
    UInt32 total_bytes = 0;
    UInt32 total_compressed_cache_lines = 0;
    for (UInt32 i = 0; i < m_cacheline_count; i++)
    {
        m_compressed_cache_line_sizes[i] = compressCacheLine(m_data_buffer + i * m_cache_line_size, m_compressed_data_buffer + i * m_cache_line_size);
        total_bytes += m_compressed_cache_line_sizes[i];
        if (m_compressed_cache_line_sizes[i] < m_cache_line_size)
            total_compressed_cache_lines++;
    }
    //assert(total_bytes <= m_page_size && "[FVE] Wrong compression!"); 

    // Return compressed cache lines
    *compressed_cache_lines = total_compressed_cache_lines;

    // Return compressed pages size in Bytes
    *compressed_page_size = total_bytes;
    // printf("[FVE Compression] Compressed Page Size: %u bytes", total_bytes);

    // Return compression latency
    ComponentLatency compress_latency(ComponentLatency(core->getDvfsDomain(), m_cacheline_count * m_compression_latency));
    return compress_latency.getLatency();
}


SubsecondTime
CompressionModelFVE::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), compressed_cache_lines * m_decompression_latency));
    return decompress_latency.getLatency();
}

void 
CompressionModelFVE::initBitstream(bitstream *stream, void *buf, UInt32 bytes)
{
    stream->byte_ptr = (UInt8 *)buf;
    stream->bit_pos = 0;
    stream->num_bytes = bytes;
    return;
}

UInt64 
CompressionModelFVE::readBit(bitstream *stream)
{
    UInt32 idx;
    UInt64 word, bit;

    idx = stream->bit_pos / 8;
    if(idx < stream->num_bytes)
    {
        bit = (stream->bit_pos & 7);
        word = (stream->byte_ptr[idx] >> bit) & 1UL;
        stream->bit_pos++;
    }
    else
    {
        word = 0;
    }
    return word;
}

void 
CompressionModelFVE::writeBit(bitstream *stream, UInt64 x) 
{
    UInt32 bit, idx, mask;
    UInt64 set;

    idx = stream->bit_pos / 8;	// bit to byte
    if(idx < stream->num_bytes) 
    {
        bit  = (stream->bit_pos & 7); // find bit inside a specific byte 
        mask = 0xff ^ (1 << bit); // mask has 0 in the desired bit
        set  = (x & 1UL) << bit; // set has 1 or 0 only in the desired bit
        stream->byte_ptr[idx] = (stream->byte_ptr[idx] & mask) | set; 
        stream->bit_pos++;
    }
}

void 
CompressionModelFVE::encodeWord(bitstream *stream, UInt64 word, UInt32 indx)
{
    UInt64 bit=0, mask2=0;
    UInt8 i=0, mask=0;
    dictionary_info res; 

    res = compression_CAM->search_value(word);

    LOG_PRINT("%ith word %lu was found in CAM: %i and in place %i with BitPos %d\n",indx, word, res.found, res.indx, stream->bit_pos);

    if(res.found) // Found in dictionary table 
    { 
        /*
         * Set the corresponding bit in compr header to indicate a compressed format 
         */
        mask = 0x01 << (indx % 8); // bits 0->7, for the different wordsizes we move to different bytes using the indx of the next line
        stream->byte_ptr[indx/8] |= mask;
        mask = 0x01;
        /*
         * Write the index that was found in the dictionary table in output stream
         */
        for(i=0; i<floorLog2(m_cam_size); i++)
        {
            bit = (res.indx >> i) & mask;
            writeBit(stream, bit);
        }
    } 
    else
    {
        /*
         * Write the (uncompressed) word in the output 
         */
        mask2=0x0000000000000001;
        for(i=0; i<(m_word_size_bits); i++)
        {
            bit = (word>>i) & mask2;
            writeBit(stream,bit);
        } 
    }

}

UInt64 
CompressionModelFVE::decodeWord(bitstream *stream, UInt32 indx)
{
    UInt64 bit=0, word=0;
    UInt8 mask, i, compressed, cam_indx=0;

    /*
     * Read a specific bit from the header to find if the corresponding word is compressed format or not
     */
    mask = 0x01 << (indx%8); // bits 0->7, for the different wordsizes we move to different bytes using the indx of the next line
    compressed = stream->byte_ptr[indx/8] & mask;
    LOG_PRINT("%ith word recieved for decode is compressed: %i\n", indx, compressed);


    if(compressed != 0)
    {
        for(i=0;i<floorLog2(m_cam_size);i++)
        {
            bit = readBit(stream);
            bit <<= i;
            cam_indx |= (UInt8)bit;
        }
        word = decompression_CAM->read_value(cam_indx);
        decompression_CAM->update_LRU(cam_indx);
    }
    else
    {
        /*
         * Read the (uncompressed) word from the input
         */
        for(i=0;i<m_word_size_bits;i++)
        {
            bit = readBit(stream);
            bit <<= i;
            word |= bit;
        }
        cam_indx=decompression_CAM->replace_value(word);
        decompression_CAM->update_LRU(cam_indx);
    }

    return word;
}

SInt64
CompressionModelFVE::readWord(void *ptr, UInt32 idx, UInt32 word_size_bytes) 
{
    SInt64 word;
    switch (word_size_bytes)
    {
        case 8:
            word = ((SInt64 *)ptr)[idx];
            break;
        case 4:
            word = ((SInt32 *)ptr)[idx];
            break;    
        case 2:
            word = ((SInt16 *)ptr)[idx];
            break;
        case 1:
            word = ((SInt8 *)ptr)[idx];
            break;
        default:
            fprintf(stderr,"Unknown Base Size\n");
            exit(1);
    }

    return word;
}

void 
CompressionModelFVE::writeWord(void *ptr, UInt32 idx, SInt64 word, UInt32 word_size_bytes)
{
    switch(word_size_bytes)
    {
        case 8:   
            ((SInt64 *)ptr)[idx] = (SInt64)word;
            break;          
        case 4:   
            ((SInt32 *)ptr)[idx] = (SInt32)word;
            break;
        case 2:
            ((SInt16*)ptr)[idx] = (SInt16)word;
            break;
        case 1:
            ((SInt8*)ptr)[idx] = (SInt8)word;
            break;
        default:
            fprintf(stderr,"Unknown Base Size\n");
            exit(1);
    }      
}

UInt32 
CompressionModelFVE::compressCacheLine(void* _inbuf, void* _outbuf)
{
    bitstream stream;
    UInt32 i, word_count;
    UInt64 word;

    word_count = m_cache_line_size / (m_word_size_bytes);
    if(word_count == 0)
    {
        return 0;
    }

    /* 
     * Outstream pointer shows after the compr/decompr header
     */
    switch(m_word_size_bits)
    {
        case 32:
            initBitstream(&stream, _outbuf, m_cache_line_size + 2); // +2 bytes = 16-bits for compr/decompr header
            stream.bit_pos = 16;
            break;

        case 64:
            initBitstream(&stream, _outbuf, m_cache_line_size + 1); // +1 bytes = 8-bits for compr/decompr header
            stream.bit_pos = 8;
            break;

        default:
            return 0;	
    }


    /*
     * Encode the words from the input and store them in bitstream
     */
    for(i=0; i<word_count; i++)
    { 
        word = readWord(_inbuf, i, m_word_size_bytes);
        LOG_PRINT("%ith word is: %lu\n", i, word);
        encodeWord(&stream, word, i);
    }

    return (UInt32) ((stream.bit_pos + 7) / 8);  
};


UInt32
CompressionModelFVE::decompressCacheLine(void *in, void *out)
{
    bitstream stream;
    UInt32 i, word_count;
    UInt64 word;

    word_count = m_cache_line_size / (m_word_size_bytes);

    /* Do we have anything to decompress? */
    if(word_count == 0)
    {
        return 0;
    }

    /* 
     * Outstream pointer shows after the compr/decompr header
     */
    switch(m_word_size_bits)
    {
        case 32:
            initBitstream(&stream, in, m_cache_line_size + 2); // +2 bytes = 16-bits for compr/decompr header
            stream.bit_pos = 16;
            break;

        case 64:
            initBitstream(&stream, in, m_cache_line_size + 1); // +1 byte = 8-bits for compr/decompr header
            stream.bit_pos = 8;
            break;

        default:
            return 0;	
    }

    for(i=0; i<word_count; i++)
    {
        word = decodeWord(&stream, i);
        LOG_PRINT("%ith decoded word: %lu\n", i, word);
        writeWord(out, i, word, m_word_size_bytes);
    } 

    return 0;
} 

SubsecondTime
CompressionModelFVE::compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    UInt32 total_compressed_size = 0;
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        UInt32 compressed_page_size;
        UInt32 compressed_cache_lines;
        total_compression_latency += CompressionModelFVE::compress(addr, m_page_size, core_id, &compressed_page_size, &compressed_cache_lines);
        total_compressed_size += compressed_page_size;
        (*address_to_num_cache_lines)[addr] = compressed_cache_lines;
    }
    *compressed_multipage_size = total_compressed_size;
    return total_compression_latency;
}


SubsecondTime
CompressionModelFVE::decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        total_compression_latency += CompressionModelFVE::decompress(addr, (*address_to_num_cache_lines)[addr], core_id);
    }
    return total_compression_latency;
}
