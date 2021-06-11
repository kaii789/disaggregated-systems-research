#include "compression_model_bdi.h"
#include "utils.h"

CompressionModelBDI::CompressionModelBDI(String name, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
{
    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];
    m_compressed_cache_line_sizes = new UInt32[m_cacheline_count];
}

CompressionModelBDI::~CompressionModelBDI()
{
    delete [] m_data_buffer;
    delete [] m_compressed_data_buffer;
    delete [] m_compressed_cache_line_sizes;
}

SubsecondTime
CompressionModelBDI::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    // Get Data
    UInt64 page = addr & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    core->getApplicationData(Core::NONE, Core::READ, page, m_data_buffer, data_size, Core::MEM_MODELED_NONE);
    
    // BDI
    UInt32 total_bytes = 0;
    UInt32 total_compressed_cache_lines = 0;
    for (UInt32 i = 0; i < m_cacheline_count; i++)
    {
        m_compressed_cache_line_sizes[i] = compressCacheLine(m_data_buffer + i * m_cache_line_size, m_compressed_data_buffer + i * m_cache_line_size);
        total_bytes += m_compressed_cache_line_sizes[i];
        if (m_compressed_cache_line_sizes[i] < m_cache_line_size)
            total_compressed_cache_lines++;
    }
    assert(total_bytes <= m_page_size && "[BDI] Wrong compression!");
   
    /*
     * Log for compressed data
    // Log
    FILE *fp;
    fp = fopen("compression.log", "a");
    // for (int i = 0; i < (int)data_size; i++) {
    //     fprintf(fp, "%c ", buffer[i]);
    // }
    fprintf(fp, "##########################%s#############################\n", "PAGE START");
    for (int i = 0; i < cacheline_count; i++)
    {
        // Orig
        fprintf(fp, "Uncompressed: ");
        for (int j = 0; j < m_cache_line_size; j++)
        {
            fprintf(fp, "%hhu ", (uint8_t)buffer[i * m_cache_line_size + j]);
        }
        // Compressed
        fprintf(fp, "\nCompressed: ");
        int size = compressed_size[i];
        for (int j = 0; j < size; j++)
        {
            fprintf(fp, "%hhu ", (uint8_t)compressed_buffer[i * m_cache_line_size + j]);
        }
        fprintf(fp, "\n\n");
    }
    fprintf(fp, "##########################%s#############################\n", "PAGE END");

    free(buffer);
    free(compressed_buffer);
    *
    */

    // Return compressed cache lines
    *compressed_cache_lines = total_compressed_cache_lines;

    // Return compressed pages size in Bytes
    *compressed_page_size = total_bytes;

    // Return compression latency
    ComponentLatency compress_latency(ComponentLatency(core->getDvfsDomain(), total_compressed_cache_lines * m_compression_latency));
    return compress_latency.getLatency();

}

SubsecondTime
CompressionModelBDI::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), compressed_cache_lines * m_decompression_latency));
    return decompress_latency.getLatency();

}

SInt64
CompressionModelBDI::readWord(void *ptr, UInt32 idx, UInt32 word_size) // idx: which word of input ptr to read 
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
            fprintf(stderr,"Unknown base size\n");
            exit(1);
    }

    return word;
}


void 
CompressionModelBDI::writeWord(void *ptr, UInt32 idx, SInt64 word, UInt32 word_size)
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
            fprintf(stderr,"Unknown Delta size\n");
            exit(1);
    }      
}

bool 
CompressionModelBDI::checkDeltaLimits(SInt64 delta, UInt32 delta_size)
{
    bool within_limits = true;
    switch (delta_size)
    {          
        case 4:   
            if ((delta < INT_MIN) || (delta > INT_MAX)) within_limits = false;
            break;
        case 2:
            if ((delta < SHRT_MIN) || (delta > SHRT_MAX)) within_limits = false;
            break;
        case 1:
            if ((delta < SCHAR_MIN) || (delta > SCHAR_MAX)) within_limits = false;
            break;
        default:
            fprintf(stderr,"Unknown Delta Size\n");
            exit(1);
    }      
    return within_limits;
}

void
CompressionModelBDI::zeroValues(void* in, m_compress_info *res, void* out)
{
    // Zero compression compresses an all-zero cache line into a bit that just indicates that the cache line is all-zero.
    char base;
    UInt32 i;
    base = ((char*)in)[0];
    for (i = 1; i < m_cache_line_size; i++)
        if((base - (((char*)in)[i])) != 0)
            break;
    
    if (i == m_cache_line_size) {
        res->is_compressible = true;
        res->compressed_size = 1;
        //result=boost::make_tuple(1,1);
        writeWord(out, 0, base, sizeof(char));
    } else {
        res->is_compressible = false;
        res->compressed_size = m_cache_line_size;
        //result=boost::make_tuple(0,m_cache_line_size);
    }
    return;
}

void
CompressionModelBDI::repeatedValues(void* in, m_compress_info *res, void* out)
{
    //  Repeated value compression checks if a cache line has the same 1/2/4/8 byte value repeated. If so, it compresses the cache line to the corresponding value
    //  FIXME cgiannoula - now it only works with 8-byte granularity
    SInt64 base;
    UInt32 i;
    base = ((SInt64*)in)[0];
    for (i=1; i < (m_cache_line_size / 8); i++) 
        if ((base - ((SInt64*)in)[i]) !=0)
            break;
    
    if (i == m_cache_line_size) {
        res->is_compressible = true;
        res->compressed_size = 8;
        writeWord(out, 0, base, 8);
    } else {
        res->is_compressible = false;
        res->compressed_size = m_cache_line_size;
    }
    return;
}

void
CompressionModelBDI::specializedCompress(void *in, m_compress_info *res, void *out, SInt32 k, SInt32 delta_size)
{
 
    UInt32 i;
    SInt64 base, word, delta;
    bool within_limits = true;

    base = readWord(in, 0, k);
    writeWord(out, 0, base, k);
    //for(i = 0; i < ((m_cache_line_size / k) - 1); i++){
    for(i = 0; i < (m_cache_line_size / k); i++){
       //word = readWord((void*)(((char*)in) + k * sizeof(char)), i, k);
       word = readWord((void*)((char*)in), i, k);
       delta = base - word;

       within_limits = checkDeltaLimits(delta, delta_size);
       if (within_limits == false) 
           break;
       else 
           writeWord((void*) (((char*)out) + k * sizeof(char)), i, delta, delta_size);
    }
    
    if(within_limits == true) {
        res->is_compressible = within_limits; 
        res->compressed_size = (UInt32) (k + (m_cache_line_size / k) * delta_size);
    } else {
        res->is_compressible = within_limits; 
    }
    //result = boost::make_tuple(within_limits, ((m_cache_line_size / k) - 1) * delta_size + k);
    return; 
}

UInt32 
CompressionModelBDI::compressCacheLine(void* in, void* out)
{
    UInt32 i;
    SInt32 b, d, cur_option = 0;

    m_compress_info *m_options_compress_info;
    char **m_options_data_buffer;
    m_options_compress_info = new m_compress_info[8];
    m_options_data_buffer = new char*[8];
    for(i = 0; i < m_options; i++) {
        m_options_compress_info[i].is_compressible = false;
        m_options_compress_info[i].compressed_size = m_cache_line_size;
        m_options_data_buffer[i] = new char[m_cache_line_size];
    }


    // Option 0: all bytes within the cache line are equal to 0
    zeroValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option]);
    cur_option++;

    // Option 1: a single value repeated multiple times within the cache line (8-byte granularity) 
    repeatedValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option]);
    cur_option++;

    //std::cout << "Start" << std::endl;
    for (b = 8; b >= 2; b /= 2) {
        for(d = 1; d <= (b/2); d *= 2){
            // Option 2: base_size = 8 bytes, delta_size = 1 byte
            // Option 3: base_size = 8 bytes, delta_size = 2 bytes
            // Option 4: base_size = 8 bytes, delta_size = 4 bytes
            // Option 5: base_size = 4 bytes, delta_size = 1 byte
            // Option 6: base_size = 4 bytes, delta_size = 2 bytes
            // Option 7: base_size = 2 bytes, delta_size = 1 byte
            specializedCompress(in, &(m_options_compress_info[cur_option]), (void*)m_options_data_buffer[cur_option], b, d);
            //std::cout << " b " << b << " d " << d << " compressed " << m_options_compress_info[cur_option].is_compressible << " " << m_options_compress_info[cur_option].compressed_size << std::endl;
            cur_option++;
        }
    }
    //std::cout << "End" << std::endl;
    
    UInt32 compressed_size = (UInt32) m_cache_line_size;
    UInt32 chosen_option = 42; // If chosen_option == 42 (should be smaller than pow(2,8), cache line is not compressible (leave it uncompressed)
    for(i = 0; i < m_options; i++) {
        if(m_options_compress_info[i].is_compressible == true){
            if(m_options_compress_info[i].compressed_size < compressed_size){
                compressed_size = m_options_compress_info[i].compressed_size;
                chosen_option = i; // Update chosen option
            }            
        }
    }

    ((char*)out)[0] = (char) chosen_option; // Store chosen_option in the first byte of out data buffer
    if (chosen_option == 42)
        memcpy((void*)(((char*)out) + sizeof(char)), in, m_cache_line_size); // Store data in uncompressed format
    else
        memcpy((void*)(((char*)out) + sizeof(char)), m_options_data_buffer[chosen_option], compressed_size); // Stored data using the chosen compressed format


    for(i = 0; i < m_options; i++) {
        delete [] m_options_data_buffer[i];
    }
    delete [] m_options_compress_info;
    delete [] m_options_data_buffer;

    return compressed_size; 
}



UInt32 
CompressionModelBDI::decompressCacheLine(void *in, void *out)
{
    char chosen_option;
    UInt32 i;
    SInt64 base, delta, word;

    chosen_option = ((char*)in)[0];
    in = (void*)(((char*)in)+1);

    switch (chosen_option)
    {
        case 0:
            // Option 0: all bytes within the cache line are equal to 0
            base = readWord(in, 0, sizeof(char));
            memset(out, base, m_cache_line_size);       
            break;
        case 1:
            // Option 1: a single value repeated multiple times within the cache line (8-byte granularity) 
            base = readWord(in, 0, 8);
            for (i = 0; i < (m_cache_line_size / 8); i++)
                ((long int*)out)[i] = base;
            break;
       case 2:
            // Option 2: base_size = 8 bytes, delta_size = 1 byte
            base = readWord(in, 0, sizeof(SInt64));
            writeWord(out, 0, base, sizeof(SInt64));
            in = (void*) (((char*)in) + sizeof(SInt64));
            out = (void*) (((char*)out) + sizeof(SInt64));
            //for (i=0;i<(m_cache_line_size/sizeof(long int)-1);i++){
            for (i = 1; i < (m_cache_line_size / sizeof(SInt64)); i++){
                delta = readWord(in, i, sizeof(SInt8));
                word = base - delta;
                writeWord(out, i, word, sizeof(SInt64));   
            }
            break;
        case 3:
            // Option 3: base_size = 8 bytes, delta_size = 2 bytes
            base = readWord(in, 0, sizeof(SInt64));
            writeWord(out, 0, base, sizeof(SInt64));
            in = (void*) (((char*)in) + sizeof(SInt64));
            out = (void*)(((char*)out) + sizeof(SInt64));
            //for (i=0;i<(m_cache_line_size/sizeof(long int)-1);i++){
            for (i = 1; i < (m_cache_line_size / sizeof(SInt64)); i++){
                delta = readWord(in, i, sizeof(SInt16));
                word = base - delta;
                writeWord(out, i, word, sizeof(SInt64));   
            }
            break;
        case 4:
            // Option 4: base_size = 8 bytes, delta_size = 4 bytes
            base = readWord(in, 0, sizeof(SInt64));
            writeWord(out, 0, base, sizeof(SInt64));
            in = (void*) (((char*)in) + sizeof(SInt64));
            out = (void*) (((char*)out) + sizeof(SInt64));
            //for (i=0;i<(m_cache_line_size/sizeof(long int)-1);i++){
            for (i=1; i< (m_cache_line_size / sizeof(SInt64)); i++){
                delta = readWord(in, i, sizeof(SInt32));
                word = base - delta;
                writeWord(out, i, word, sizeof(SInt64));   
            }
            break;
        case 5:
            // Option 5: base_size = 4 bytes, delta_size = 1 byte
            base = readWord(in, 0, sizeof(SInt32));
            writeWord(out, 0, base, sizeof(SInt32));
            in = (void*)(((char*)in) + sizeof(SInt32));
            out = (void*)(((char*)out) + sizeof(SInt32));
            //for (i=0;i<(m_cache_line_size/sizeof(int)-1);i++){
            for (i = 0; i < (m_cache_line_size / sizeof(SInt32)); i++){
                delta = readWord(in, i, sizeof(SInt8));
                word = base - delta;
                writeWord(out, i, word, sizeof(SInt32));   
            }
            break;
        case 6:
            // Option 6: base_size = 4 bytes, delta_size = 2 bytes
            base = readWord(in, 0, sizeof(SInt32));
            writeWord(out, 0, base, sizeof(SInt32));
            in = (void*) (((char*)in) + sizeof(SInt32));
            out = (void*) (((char*)out) + sizeof(SInt32));
            //for(i = 0; i <(m_cache_line_size/sizeof(int)-1);i++){
            for(i = 0; i < (m_cache_line_size / sizeof(SInt32)); i++){
                delta = readWord(in, i, sizeof(SInt16));
                word = base - delta;
                writeWord(out, i, word, sizeof(SInt32));   
            }
            break;
        case 7:
            // Option 7: base_size = 2 bytes, delta_size = 1 byte
            base = readWord(in, 0, sizeof(SInt16));
            writeWord(out, 0, base, sizeof(SInt16));
            in = (void*) (((char*)in) + sizeof(SInt16));
            out = (void*)(((char*)out) + sizeof(SInt16));
            //for (i =0;i<(m_cache_line_size/sizeof(short int)-1);i++){
            for (i = 0; i < (m_cache_line_size / sizeof(SInt16)); i++){
                delta = readWord(in, i, sizeof(SInt8));
                word = base - delta;
                writeWord(out, i, word, sizeof(SInt16));   
            }
            break;
        case 42: // Uncompressed cache line
            memcpy(out, in, m_cache_line_size);
            break;
        default:
            fprintf(stderr,"Unknown code\n");
            exit(1);
    }
    return 0;

}
