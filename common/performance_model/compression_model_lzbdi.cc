#include "compression_model_lzbdi.h"
#include "utils.h"
#include "stats.h"
#include "config.hpp"

CompressionModelLZBDI::CompressionModelLZBDI(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
    , m_compression_granularity(Sim()->getCfg()->getInt("perf_model/dram/compression_model/lzbdi/compression_granularity"))
    , use_additional_options(Sim()->getCfg()->getBool("perf_model/dram/compression_model/lzbdi/use_additional_options"))
    , m_total_compressed(0)
{
    m_options = (use_additional_options) ? 16 : 11;
    m_index_bits = 4;

    // Set compression/decompression cycle latencies if configured
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lzbdi/compression_latency") != -1)
        m_compression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lzbdi/compression_latency");
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lzbdi/decompression_latency") != -1)
        m_decompression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lzbdi/decompression_latency");

    if (m_compression_granularity != -1) {
        m_cache_line_size = m_compression_granularity;
    }

    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];
    m_compressed_cache_line_sizes = new UInt32[m_cacheline_count];

    // Register stats for compression_options
    registerStatsMetric("compression", id, "lzbdi_num_overflowed_pages", &m_num_overflowed_pages);
    registerStatsMetric("compression", id, "bdi_total_compressed", &(m_total_compressed));
    for (UInt32 i = 0; i < 13; i++) {
        String stat_name = "bdi_usage_option-";
        stat_name += std::to_string(i).c_str();
        registerStatsMetric("compression", id, stat_name, &(m_compress_options[i]));
    }

    for (UInt32 i = 0; i < 13; i++) {
        String stat_name = "bdi_bytes_saved_option-";
        stat_name += std::to_string(i).c_str();
        registerStatsMetric("compression", id, stat_name, &(m_bytes_saved_per_option[i]));
    }


}

CompressionModelLZBDI::~CompressionModelLZBDI()
{
    delete [] m_data_buffer;
    delete [] m_compressed_data_buffer;
    delete [] m_compressed_cache_line_sizes;
}

void
CompressionModelLZBDI::finalizeStats()
{
    for (UInt32 i = 0; i < 16; i++) {
        m_total_compressed += m_compress_options[i];
    }
}

SubsecondTime
CompressionModelLZBDI::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    // Get Data
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    // UInt64 page = addr & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
    // core->getApplicationData(Core::NONE, Core::READ, page, m_data_buffer, data_size, Core::MEM_MODELED_NONE);
    if (data_size == m_cache_line_size)  { // If we compress in cache_line granularity
        core->getApplicationData(Core::NONE, Core::READ, addr, m_data_buffer, data_size, Core::MEM_MODELED_NONE); // Assume addr already points to page or cache line
    } else { // If we compress in page_size granularity, we shift to move to the start_addr of the corresponding page
        UInt64 page = addr & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
        core->getApplicationData(Core::NONE, Core::READ, page, m_data_buffer, data_size, Core::MEM_MODELED_NONE);
    }

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
    UInt32 index_bytes = (m_index_bits * m_cacheline_count) / 8;
    total_bytes  += index_bytes; // add indexing bytes to find the compresison pattern used
    if (total_bytes > m_page_size) {
        m_num_overflowed_pages++;
        total_bytes = m_page_size; // if compressed data is larger than the page_size, we sent the page in uncompressed format
    }
    assert(total_bytes <= m_page_size && "[LZBDI] Wrong compression!");
  
    // Return compressed cache lines
    *compressed_cache_lines = total_compressed_cache_lines;

    // Return compressed pages size in Bytes
    *compressed_page_size = total_bytes;

    // Return compression latency
    ComponentLatency compress_latency(ComponentLatency(core->getDvfsDomain(), m_cacheline_count  * m_compression_latency));
    return compress_latency.getLatency();

}

SubsecondTime
CompressionModelLZBDI::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), compressed_cache_lines * m_decompression_latency));
    return decompress_latency.getLatency();

}

SInt64
CompressionModelLZBDI::readWord(void *ptr, UInt32 idx, UInt32 word_size) // idx: which word of input ptr to read 
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
CompressionModelLZBDI::writeWord(void *ptr, UInt32 idx, SInt64 word, UInt32 word_size)
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

bool
CompressionModelLZBDI::checkDeltaLimits(SInt64 delta, UInt32 delta_size)
{
    bool within_limits = true;
    SInt8 cur_byte;
    for(SInt8 j = delta_size; j < sizeof(SInt64); j++) {     
        cur_byte = (delta >> (8*j)) & 0xff; // Get j-th byte from the word
        if (cur_byte != 0)
            within_limits = false;
    }
    return within_limits;
}

void
CompressionModelLZBDI::zeroValues(void* in, m_compress_info *res, void* out)
{
    // Zero compression compresses an all-zero cache line into a bit that just indicates that the cache line is all-zero.
    char base;
    UInt32 i = 0;
    base = ((char*)in)[0];
    if (base == 0) { 
        for (i = 1; i < m_cache_line_size; i++)
            if((base - (((char*)in)[i])) != 0)
                break;
    } 

    if (i == m_cache_line_size) {
        res->is_compressible = true;
        res->compressed_size = 1;
        writeWord(out, 0, base, sizeof(char));
    } else {
        res->is_compressible = false;
        res->compressed_size = m_cache_line_size;
    }
    return;
}

void
CompressionModelLZBDI::repeatedValues(void* in, m_compress_info *res, void* out, UInt32 k)
{
    //  Repeated value compression checks if a cache line has the same 1/2/4/8 byte value repeated. If so, it compresses the cache line to the corresponding value
    SInt64 base;
    bool repeated;
    UInt32 i;
    repeated = true;
    switch(k)
    {
        case 8:   
            base = ((SInt64*)in)[0];
            for (i = 1; i < (m_cache_line_size / k); i++) 
                if ((base - ((SInt64*)in)[i]) != 0) {
                    repeated = false;
                    break;
                }
            break;          
        case 4:   
            base = ((SInt32*)in)[0];
            for (i = 1; i < (m_cache_line_size / k); i++) 
                if ((base - ((SInt32*)in)[i]) != 0) {
                    repeated = false;
                    break;
                }
            break;
        case 2:
            base = ((SInt16*)in)[0];
            for (i = 1; i < (m_cache_line_size / k); i++) 
                if ((base - ((SInt16*)in)[i]) != 0) {
                    repeated = false;
                    break;
                }
            break;
        case 1:
            base = ((SInt8*)in)[0];
            for (i = 1; i < (m_cache_line_size / k); i++) 
                if ((base - ((SInt8*)in)[i]) != 0) {
                    repeated = false;
                    break;
                }
            break;
        default:
            fprintf(stderr,"Unknown Base Size\n");
            exit(1);


    }      

    if (repeated == true) {
        res->is_compressible = true;
        res->compressed_size = k;
        writeWord(out, 0, k, sizeof(char));
        out = (void*)(((char*)out)+1); // Move out pointer by one byte
        writeWord(out, 0, base, k * sizeof(char));
        return;
    } 

    assert(repeated == false && "[LZBDI] repeated_values() failed!");
    res->is_compressible = false;
    res->compressed_size = m_cache_line_size;

    return;
}

void
CompressionModelLZBDI::specializedCompress(void *in, m_compress_info *res, void *out, SInt32 k, SInt32 delta_size)
{
 
    UInt32 i;
    SInt64 base, word, delta;
    bool within_limits = true;

    base = readWord(in, 0, k);
    writeWord(out, 0, base, k);
    for(i = 0; i < (m_cache_line_size / k); i++){
       word = readWord((void*)((char*)in), i, k);
       delta = base - word;

       within_limits = checkDeltaLimits(delta, delta_size);
       if (within_limits == false)
           break;
    //    else
    //        writeWord((void*) (((char*)out) + k * sizeof(char)), i, delta, delta_size);
    }
    
    if(within_limits == true) {
        res->is_compressible = within_limits; 
        res->compressed_size = (UInt32) (k + (m_cache_line_size / k) * delta_size);
    } else {
        res->is_compressible = within_limits; 
    }
    return; 
}

UInt32 
CompressionModelLZBDI::compressCacheLine(void* in, void* out)
{
    UInt32 i;
    SInt32 b, d, cur_option = 0;

    m_compress_info *m_options_compress_info;
    char **m_options_data_buffer;
    m_options_compress_info = new m_compress_info[m_options];
    m_options_data_buffer = new char*[m_options];
    for(i = 0; i < m_options; i++) {
        m_options_compress_info[i].is_compressible = false;
        m_options_compress_info[i].compressed_size = m_cache_line_size;
        m_options_data_buffer[i] = new char[m_cache_line_size];
    }


    // Option 0: all bytes within the cache line are equal to 0
    zeroValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option]);
    cur_option++;



    // Option 1: a single value with 1-byte size granularity repeated through the cache line 
    repeatedValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option], 1);
    cur_option++;

    // Option 2: a single value with 2-byte size granularity repeated through the cache line 
    repeatedValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option], 2);
    cur_option++;

    // Option 3: a single value with 4-byte size granularity repeated through the cache line 
    repeatedValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option], 4);
    cur_option++;

    // Option 4: a single value with 8-byte size granularity repeated through the cache line 
    repeatedValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option], 8);
    cur_option++;


    if (use_additional_options) {
        // Additional Options:
        // Option 5: base_size = 8 bytes, delta_size = 1 byte
        // Option 6: base_size = 8 bytes, delta_size = 2 bytes
        // Option 7: base_size = 8 bytes, delta_size = 3 bytes
        // Option 8: base_size = 8 bytes, delta_size = 4 bytes
        // Option 9: base_size = 8 bytes, delta_size = 5 bytes
        // Option 10: base_size = 8 bytes, delta_size = 6 bytes
        // Option 11: base_size = 8 bytes, delta_size = 7 bytes
        // Option 12: base_size = 4 bytes, delta_size = 1 byte
        // Option 13: base_size = 4 bytes, delta_size = 2 bytes
        // Option 14: base_size = 4 bytes, delta_size = 3 bytes
        // Option 15: base_size = 2 bytes, delta_size = 1 byte
        for (b = 8; b >= 2; b /= 2) {
            for(d = 1; d < b; d++){
                specializedCompress(in, &(m_options_compress_info[cur_option]), (void*)m_options_data_buffer[cur_option], b, d);
                cur_option++;
            }
        }
    } else {
        // Original Options:
        // Option 5: base_size = 8 bytes, delta_size = 1 byte
        // Option 6: base_size = 8 bytes, delta_size = 2 bytes
        // Option 7: base_size = 8 bytes, delta_size = 4 bytes
        // Option 8: base_size = 4 bytes, delta_size = 1 byte
        // Option 9: base_size = 4 bytes, delta_size = 2 bytes
        // Option 10: base_size = 2 bytes, delta_size = 1 byte
        for (b = 8; b >= 2; b /= 2) {
            for(d = 1; d <= (b/2); d *= 2){
                specializedCompress(in, &(m_options_compress_info[cur_option]), (void*)m_options_data_buffer[cur_option], b, d);
                cur_option++;
            }
        }
    }

    UInt32 compressed_size = (UInt32) m_cache_line_size;
    UInt8 chosen_option = 42; // If chosen_option == 42, cache line is not compressible (leave it uncompressed)
    for(i = 0; i < m_options; i++) {
        if(m_options_compress_info[i].is_compressible == true){
            if(m_options_compress_info[i].compressed_size < compressed_size){
                compressed_size = m_options_compress_info[i].compressed_size;
                chosen_option = i; // Update chosen option
            }
        }
    }

    // Statistics
    if(chosen_option != 42) {
        m_compress_options[chosen_option]++;
        m_bytes_saved_per_option[chosen_option] += (m_cache_line_size - compressed_size); 
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



// UInt32 
// CompressionModelLZBDI::decompressCacheLine(void *in, void *out)
// {
//     char chosen_option;
//     UInt32 i;
//     SInt64 base, delta, word;

//     chosen_option = ((char*)in)[0];
//     in = (void*)(((char*)in)+1);

//     switch (chosen_option)
//     {
//         case 0:
//             // Option 0: all bytes within the cache line are equal to 0
//             base = readWord(in, 0, sizeof(char));
//             memset(out, base, m_cache_line_size);       
//             break;
//         case 1:
//             // Option 1: a single value repeated multiple times within the cache line (8-byte granularity) 
//             UInt32 k;
//             k = ((char*)in)[0];
//             in = (void*)(((char*)in)+1);
//             base = readWord(in, 0, k * sizeof(char));
//             for (i = 0; i < (m_cache_line_size / k); i++) {
//                 writeWord(out, i, base, k * sizeof(char));   
//             }
//             break;
//        case 2:
//             // Option 2: base_size = 8 bytes, delta_size = 1 byte
//             base = readWord(in, 0, sizeof(SInt64));
//             writeWord(out, 0, base, sizeof(SInt64));
//             in = (void*) (((char*)in) + sizeof(SInt64));
//             out = (void*) (((char*)out) + sizeof(SInt64));
//             for (i = 1; i < (m_cache_line_size / sizeof(SInt64)); i++) {
//                 delta = readWord(in, i, sizeof(SInt8));
//                 word = base - delta;
//                 writeWord(out, i, word, sizeof(SInt64));   
//             }
//             break;
//         case 3:
//             // Option 3: base_size = 8 bytes, delta_size = 2 bytes
//             base = readWord(in, 0, sizeof(SInt64));
//             writeWord(out, 0, base, sizeof(SInt64));
//             in = (void*) (((char*)in) + sizeof(SInt64));
//             out = (void*)(((char*)out) + sizeof(SInt64));
//             for (i = 1; i < (m_cache_line_size / sizeof(SInt64)); i++){
//                 delta = readWord(in, i, sizeof(SInt16));
//                 word = base - delta;
//                 writeWord(out, i, word, sizeof(SInt64));   
//             }
//             break;
//         case 4:
//             // Option 4: base_size = 8 bytes, delta_size = 4 bytes
//             base = readWord(in, 0, sizeof(SInt64));
//             writeWord(out, 0, base, sizeof(SInt64));
//             in = (void*) (((char*)in) + sizeof(SInt64));
//             out = (void*) (((char*)out) + sizeof(SInt64));
//             for (i=1; i< (m_cache_line_size / sizeof(SInt64)); i++){
//                 delta = readWord(in, i, sizeof(SInt32));
//                 word = base - delta;
//                 writeWord(out, i, word, sizeof(SInt64));   
//             }
//             break;
//         case 5:
//             // Option 5: base_size = 4 bytes, delta_size = 1 byte
//             base = readWord(in, 0, sizeof(SInt32));
//             writeWord(out, 0, base, sizeof(SInt32));
//             in = (void*)(((char*)in) + sizeof(SInt32));
//             out = (void*)(((char*)out) + sizeof(SInt32));
//             for (i = 0; i < (m_cache_line_size / sizeof(SInt32)); i++){
//                 delta = readWord(in, i, sizeof(SInt8));
//                 word = base - delta;
//                 writeWord(out, i, word, sizeof(SInt32));   
//             }
//             break;
//         case 6:
//             // Option 6: base_size = 4 bytes, delta_size = 2 bytes
//             base = readWord(in, 0, sizeof(SInt32));
//             writeWord(out, 0, base, sizeof(SInt32));
//             in = (void*) (((char*)in) + sizeof(SInt32));
//             out = (void*) (((char*)out) + sizeof(SInt32));
//             for(i = 0; i < (m_cache_line_size / sizeof(SInt32)); i++){
//                 delta = readWord(in, i, sizeof(SInt16));
//                 word = base - delta;
//                 writeWord(out, i, word, sizeof(SInt32));   
//             }
//             break;
//         case 7:
//             // Option 7: base_size = 2 bytes, delta_size = 1 byte
//             base = readWord(in, 0, sizeof(SInt16));
//             writeWord(out, 0, base, sizeof(SInt16));
//             in = (void*) (((char*)in) + sizeof(SInt16));
//             out = (void*)(((char*)out) + sizeof(SInt16));
//             for (i = 0; i < (m_cache_line_size / sizeof(SInt16)); i++){
//                 delta = readWord(in, i, sizeof(SInt8));
//                 word = base - delta;
//                 writeWord(out, i, word, sizeof(SInt16));   
//             }
//             break;
//         case 42: // Uncompressed cache line
//             memcpy(out, in, m_cache_line_size);
//             break;
//         default:
//             fprintf(stderr,"Unknown code\n");
//             exit(1);
//     }
//     return 0;

// }


SubsecondTime
CompressionModelLZBDI::compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    UInt32 total_compressed_size = 0;
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        UInt32 compressed_page_size;
        UInt32 compressed_cache_lines;
        total_compression_latency += CompressionModelLZBDI::compress(addr, m_page_size, core_id, &compressed_page_size, &compressed_cache_lines);
        total_compressed_size += compressed_page_size;
        (*address_to_num_cache_lines)[addr] = compressed_cache_lines;
    }
    *compressed_multipage_size = total_compressed_size;
    return total_compression_latency;
}


SubsecondTime
CompressionModelLZBDI::decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        total_compression_latency += CompressionModelLZBDI::decompress(addr, (*address_to_num_cache_lines)[addr], core_id);
    }
    return total_compression_latency;
}
