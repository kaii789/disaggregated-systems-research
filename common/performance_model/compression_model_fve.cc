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

    _wordsize = 32;
    m_word_size = 4;
    CAM_C = new CAM(64);
    CAM_D = new CAM(64);
    _cam_size = 64;
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
        printf("total bytes %d\n", total_bytes);
    }
    if (total_bytes > m_page_size) // FIXME
        total_bytes = m_page_size;
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

CompressionModelFVE::~CompressionModelFVE()
{
    delete CAM_C;
    delete CAM_D;
}

UInt32 CompressionModelFVE::compressCacheLine(void* _inbuf, void* _outbuf)
{
    bitstream stream;
    unsigned int  i,incount;
    unsigned long int x;

    unsigned int insize=m_cache_line_size;

    incount = insize / (_wordsize>>3);	// right sift bits to bytes conversion,incount has the number of words of my input buf

    /* Do we have anything to compress? */
    if( incount == 0 )
    {
        return 0;
    }

    /* Initialize output bitsream && Change the outstream pointer to show after the compr/decom header*/

    switch(_wordsize)
    {
        case 32:
            InitBitstream(&stream, _outbuf, insize+2); //stream pointer to chr=out,stram bitpos=0 stream bytes=insize+1
            stream.BitPos=16;
            break;

        case 64:
            InitBitstream(&stream, _outbuf, insize+1);
            stream.BitPos=8;
            break;

        default:
            return 0;	
    }


    /*Encode words of input and store them in bitstream*/
    for(i=0;i<incount;i++)
    { 
        x = readWord(_inbuf, i, m_word_size);
        LOG_PRINT("%ith word is:%lu\n",i,x);
        EncodeWord(&stream, x, i);

    }

    return (UInt32) ((stream.BitPos+7)>>3); // +7 γιατί αν το BitPos είναι μέσα στο 6ο ας πούμε byte επειδή μετράμε από το 0, το index του byte θα είναι το 5 και όχι το 6, και επειδή εδώ θέλουμε να στείλουμε αριθμό bytes με το +7 προσθέτουμε ένα byte. 

};

SubsecondTime
CompressionModelFVE::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), compressed_cache_lines * m_decompression_latency));
    return decompress_latency.getLatency();
}


Byte* CompressionModelFVE::MakeCompBuf()
{
    Byte* buf = new Byte[m_cache_line_size+2]();
    return buf; 
}


void CompressionModelFVE::InitBitstream( bitstream *stream,
        void *buf, unsigned int bytes )
{
    stream->BytePtr  = (unsigned char *) buf;
    stream->BitPos   = 0;
    stream->NumBytes = bytes;
}




unsigned long int CompressionModelFVE::ReadBit(bitstream *stream )
{
    unsigned int idx;
    unsigned long int x, bit;

    idx = stream->BitPos >> 3;
    if( idx < stream->NumBytes )
    {
        bit = (stream->BitPos & 7);
        x = (stream->BytePtr[ idx ] >> bit) & 1UL;
        ++ stream->BitPos;
    }
    else
    {
        x = 0;
    }
    return x;
}




void CompressionModelFVE::WriteBit( bitstream *stream, unsigned  long int x  ) /*Αλλάζω, για φορά LSB->MSB από rice όπου ήταν MSB->LSB*/ 
{
    unsigned int bit, idx, mask;
    unsigned long int set;

    idx = stream->BitPos >> 3;	//idx pointing to byte
    if( idx < stream->NumBytes ) 
    {
        bit  = (stream->BitPos & 7);// σε ποιο bit μεσα στο byte είμαι
        mask = 0xff ^ (1 << bit); //η μασκα έχει 0 μόνο στο πολυπόθητο bit
        set  = (x & 1UL) << bit;// το set έχει x (1 ή 0) μόνο στο πολυπόθητο bit
        stream->BytePtr[ idx ] = (stream->BytePtr[ idx ] & mask) | set; //???? types?
        ++ stream->BitPos;
    }
}




void CompressionModelFVE::EncodeWord(bitstream *stream, unsigned long int x, unsigned int indx)
{
    unsigned long int bit=0,mask2=0;
    unsigned char i=0,mask=0;
    std::pair <bool,unsigned char> result; 


    /*Search CAM*/
    result = CAM_C->Search(x);

    LOG_PRINT("%ith word %lu was found in CAM: %i and in place: %i floor %d BitPos %d\n",indx,x,result.first,result.second, floorLog2(_cam_size), stream->BitPos);

    if(result.first) // found in FV table
    { 
        /*Write in header that this is in compressed form*/
        mask=0x01<<(indx%8); // div because bits 0->7, for different wordsizes though it responds to different bytes, solved below
        stream->BytePtr[indx>>3]|=mask;

        mask=0x01;
        /*Write the index that was found in FV table in output stream->encoding*/
        for(i=0;i<floorLog2(_cam_size);i++)
        {
            bit=(result.second>>i)&mask;
            WriteBit(stream,bit);
        }
    } 

    else
    {
        /*Write the whole word in the output */
        mask2=0x0000000000000001;
        for(i=0;i<(_wordsize);i++)
        {
            bit=(x>>i)&mask2;
            WriteBit(stream,bit);
        } 

    }



}




unsigned long int CompressionModelFVE::DecodeWord(bitstream *stream, unsigned int indx)
{
    unsigned long int bit=0,x=0;
    unsigned char mask,i,compressed,cam_indx=0;

    /*Read from header if this is compressed or not*/
    mask=0x01<<(indx%8); // div because bits 0->7, for different wordsizes though it responds to different bytes, solved below
    compressed=stream->BytePtr[indx>>3]&mask;

    LOG_PRINT("%ith word recieved for decode is compressed: %i",indx,compressed);


    if(compressed!=0)
    {
        /*Read indx*/
        for(i=0;i<floorLog2(_cam_size);i++)
        {
            bit=ReadBit(stream);
            bit<<=i;
            cam_indx|=(unsigned char)bit;
        }
        x=CAM_D->Read(cam_indx);
        CAM_D->Update_Lru(cam_indx);

    }

    else
    {
        /*Read the whole word from input*/
        for(i=0;i<_wordsize;i++)
        {
            bit=ReadBit(stream);
            bit<<=i;
            x|=bit;
        }
        cam_indx=CAM_D->Replace(x);
        CAM_D->Update_Lru(cam_indx);

    }

    return x;
}


SInt64
CompressionModelFVE::readWord(void *ptr, UInt32 idx, UInt32 word_size) // idx: which word of input ptr to read 
{
    SInt64 word;
    switch (word_size)
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
CompressionModelFVE::writeWord(void *ptr, UInt32 idx, SInt64 word, UInt32 word_size)
{
    switch(word_size)
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


UInt32 CompressionModelFVE::decompressCacheLine(void *in, void *out)
{
    bitstream stream;
    unsigned int     i,outcount;
    unsigned long int x;

    unsigned int outsize=m_cache_line_size;

    outcount = outsize / (_wordsize>>3);

    /* Do we have anything to decompress? */
    if( outcount == 0 )
    {
        return 0;
    }

    /* Initialize input bitsream - compressed buffer*/
    switch(_wordsize)
    {
        case 32:
            InitBitstream( &stream, in, outsize+2 ); //stream pointer to chr=out,stram bitpos=0 stream bytes=insize+1
            stream.BitPos=16;
            break;

        case 64:
            InitBitstream( &stream, in, outsize+1);
            stream.BitPos=8;
            break;

        default:
            return 0;	
    }

    /*main decoding loop*/
    for(i=0;i<outcount;i++)
    {
        x=DecodeWord(&stream,i);
        LOG_PRINT("%ith decoded word: %lu",i,x);
        writeWord(out, i, x, m_word_size);
    } 

    return 0;

} 
