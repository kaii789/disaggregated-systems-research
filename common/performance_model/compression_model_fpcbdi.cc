#include "compression_model_fpcbdi.h"
#include "utils.h"
#include "stats.h"
#include "config.hpp"

// Assume 32 bit word
const UInt32 CompressionModelFPCBDI::mask[6]=
       {0x00000000, // Zero run
        0x00000007, // 4 Bit
        0x0000007f, // One byte
        0x00007fff, // Halfword
        0x7fff0000, // Halfword padded with a zero halfword
        0x007f007f}; // Two halfwords, each a byte

const UInt32 CompressionModelFPCBDI::neg_check[6]=
       {0xffffffff, // N/A
        0xfffffff8, // 4 Bit
        0xffffff80, // One byte
        0xffff8000, // Halfword
        0xffffffff, // N/A
        0xff80ff80}; // Two halfwords, each a byte


CompressionModelFPCBDI::CompressionModelFPCBDI(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
    , m_compression_granularity(Sim()->getCfg()->getInt("perf_model/dram/compression_model/fpcbdi/compression_granularity"))
    , use_additional_options(Sim()->getCfg()->getBool("perf_model/dram/compression_model/fpcbdi/use_additional_options"))
    , m_total_compressed(0)
{
    m_options = (use_additional_options) ? 23 : 18;
    m_prefix_len = 5; // 5 bits are needed to identify 17 (one more option to identify uncompressed data line) and 5 bits are needed to identify 23 options

    // Set compression/decompression cycle latencies if configured
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/fpcbdi/compression_latency") != -1)
        m_compression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/fpcbdi/compression_latency");
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/fpcbdi/decompression_latency") != -1)
        m_decompression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/fpcbdi/decompression_latency");

    if (m_compression_granularity != -1) {
        m_cache_line_size = m_compression_granularity;
    }

    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];
    m_compressed_cache_line_sizes = new UInt32[m_cacheline_count];

    // Register stats for compression_options
    registerStatsMetric("compression", id, "num_overflowed_pages", &m_num_overflowed_pages);
    m_num_overflowed_pages = 0;
    registerStatsMetric("compression", id, "fpcbdi_total_compressed", &(m_total_compressed));
    for (UInt32 i = 0; i < 24; i++) {
        String stat_name = "fpcbdi_usage_option-";
        stat_name += std::to_string(i).c_str();
        registerStatsMetric("compression", id, stat_name, &(m_compress_options[i]));
    }

    for (UInt32 i = 0; i < 24; i++) {
        String stat_name = "fpcbdi_bytes_saved_option-";
        stat_name += std::to_string(i).c_str();
        registerStatsMetric("compression", id, stat_name, &(m_bytes_saved_per_option[i]));
    }


}

CompressionModelFPCBDI::~CompressionModelFPCBDI()
{
    delete [] m_data_buffer;
    delete [] m_compressed_data_buffer;
    delete [] m_compressed_cache_line_sizes;
}

void
CompressionModelFPCBDI::finalizeStats()
{
    for (UInt32 i = 0; i < 24; i++) {
        m_total_compressed += m_compress_options[i];
        m_bytes_saved_per_option[i] += m_bits_saved_per_option[i] / 8;
    }
}

SubsecondTime
CompressionModelFPCBDI::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
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
    UInt32 total_bits = 0;
    UInt32 total_bytes = 0;
    UInt32 total_compressed_cache_lines = 0;
    for (UInt32 i = 0; i < m_cacheline_count; i++)
    {
        m_compressed_cache_line_sizes[i] = compressCacheLine(m_data_buffer + i * m_cache_line_size, m_compressed_data_buffer + i * m_cache_line_size);
        total_bits += m_compressed_cache_line_sizes[i];
        if ((m_compressed_cache_line_sizes[i] != ((m_cache_line_size * 8) + m_prefix_len)) && (m_compressed_cache_line_sizes[i] < ((m_cache_line_size * 8) + ((m_cache_line_size * 8) / 32) * m_prefix_len)) )
            total_compressed_cache_lines++;
    }

    total_bytes = total_bits / 8;
    if (total_bits % 8 != 0)
        total_bytes++;

    if (total_bytes > m_page_size) {
        m_num_overflowed_pages++;
        total_bytes = m_page_size; // if compressed data is larger than the page_size, we sent the page in uncompressed format
        total_compressed_cache_lines = 0; // if page is sent uncompressed, the decompression latency is 0
    }
    assert(total_bytes <= m_page_size && "[FPCBDI] Wrong compression!");
  
    // Return compressed cache lines
    *compressed_cache_lines = total_compressed_cache_lines;

    // Return compressed pages size in Bytes
    *compressed_page_size = total_bytes;

    // Return compression latency - All lines go over the compression pipeline
    ComponentLatency compress_latency(ComponentLatency(core->getDvfsDomain(), m_cacheline_count  * m_compression_latency));
    // Even though page might be sent uncompressed, we still need to add the compression latency
    return compress_latency.getLatency();

}

SubsecondTime
CompressionModelFPCBDI::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), compressed_cache_lines * m_decompression_latency));
    return decompress_latency.getLatency();

}

SInt64
CompressionModelFPCBDI::readWord(void *ptr, UInt32 idx, UInt32 word_size) // idx: which word of input ptr to read 
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
CompressionModelFPCBDI::writeWord(void *ptr, UInt32 idx, SInt64 word, UInt32 word_size)
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
CompressionModelFPCBDI::checkDeltaLimits(SInt64 delta, UInt32 delta_size)
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
CompressionModelFPCBDI::zeroValues(void* in, m_compress_info *res, void* out)
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
CompressionModelFPCBDI::repeatedValues(void* in, m_compress_info *res, void* out, UInt32 k)
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
CompressionModelFPCBDI::specializedCompress(void *in, m_compress_info *res, void *out, SInt32 k, SInt32 delta_size)
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
CompressionModelFPCBDI::compressCacheLine(void* in, void* out)
{
    UInt32 i;
    SInt32 b, d, cur_option;

    // Initial compression info
    m_compress_info *m_options_compress_info;
    char **m_options_data_buffer;
    m_options_compress_info = new m_compress_info[m_options];
    m_options_data_buffer = new char*[m_options];
    for(i = 0; i < m_options; i++) {
        m_options_compress_info[i].is_compressible = false;
        m_options_compress_info[i].compressed_size = m_cache_line_size * 8; // bytes to bits
        m_options_data_buffer[i] = new char[m_cache_line_size];
    }

    cur_option = 0;
    // FPC Compression - Starts at 0
	UInt32 *cache_line = (UInt32*)in;
	UInt32 fpc_compressed_size_bits = 0;
	UInt32 mask_to_bits[6] = {3, 4, 8, 16, 16, 16};
    UInt8 *fpc_chosen_options = new UInt8[(m_cache_line_size * 8) / 32];

	for (int i = 0; i < (m_cache_line_size * 8) / 32; i++)
	{
		UInt32 word = cache_line[i];
        fpc_chosen_options[i] = 42;

        bool is_pattern_matched = false;
		for (int j = 0; j < 6; j++)
		{
            // Pattern match and handle
            // Starting with the highest compressibility option - We include an early break if pattern is found
			if (((word | mask[j]) == mask[j]) || ((int)word < 0 && word >= neg_check[j]))
			{
                fpc_compressed_size_bits += m_prefix_len;
				fpc_compressed_size_bits += mask_to_bits[j];
                is_pattern_matched = true;
                fpc_chosen_options[i] = j;
                //m_compress_option[j] += 1;
                //m_bits_saved_per_option[j] += 32 - m_prefix_len - mask_to_bits[j];
                // printf("[FPC] %d %x\n", j, word);
				break;
			}
		}

        if (!is_pattern_matched)
        {
            // Handle words consisting of repeated bytes
            UInt32 repeated_mask = 0x000000ff;
            bool repeated = true;
            SInt8 base = word & repeated_mask;
            for (int j = 1; j < 4; j++)
                if ((word & (repeated_mask << (j * 8))) >> (j * 8) != base) {
                    repeated = false;
                    break;
                }
            if (repeated)
            {
                fpc_compressed_size_bits += m_prefix_len;
                fpc_compressed_size_bits += 8;
                is_pattern_matched = true;
                fpc_chosen_options[i] = 6;
                //m_compress_ption[6] += 1;
                //m_bits_saved_per_option[6] += 32 - m_prefix_len - 8;
                // printf("[FPC] pattern match %x\n", word);
            }
        }

        // None of the patterns match, so can't compress
        if (!is_pattern_matched)
        {
            fpc_compressed_size_bits += (32 + m_prefix_len);
            fpc_chosen_options[i] = 42;
            // printf("[FPC] uncompressed %x\n", word);
        }
	}


    // BDI Compression - Starting at option 7
    cur_option = 7;
    // BDI-Option 0: all bytes within the cache line are equal to 0
    zeroValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option]);
    cur_option++;



    // BDI-Option 1: a single value with 1-byte size granularity repeated through the cache line 
    repeatedValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option], 1);
    cur_option++;

    // BDI-Option 2: a single value with 2-byte size granularity repeated through the cache line 
    repeatedValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option], 2);
    cur_option++;

    // BDI-Option 3: a single value with 4-byte size granularity repeated through the cache line 
    repeatedValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option], 4);
    cur_option++;

    // BDI-Option 4: a single value with 8-byte size granularity repeated through the cache line 
    repeatedValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option], 8);
    cur_option++;


    if (use_additional_options) {
        // Additional Options:
        // BDI-Option 5: base_size = 8 bytes, delta_size = 1 byte
        // BDI-Option 6: base_size = 8 bytes, delta_size = 2 bytes
        // BDI-Option 7: base_size = 8 bytes, delta_size = 3 bytes
        // BDI-Option 8: base_size = 8 bytes, delta_size = 4 bytes
        // BDI-Option 9: base_size = 8 bytes, delta_size = 5 bytes
        // BDI-Option 10: base_size = 8 bytes, delta_size = 6 bytes
        // BDI-Option 11: base_size = 8 bytes, delta_size = 7 bytes
        // BDI-Option 12: base_size = 4 bytes, delta_size = 1 byte
        // BDI-Option 13: base_size = 4 bytes, delta_size = 2 bytes
        // BDI-Option 14: base_size = 4 bytes, delta_size = 3 bytes
        // BDI-Option 15: base_size = 2 bytes, delta_size = 1 byte
        for (b = 8; b >= 2; b /= 2) {
            for(d = 1; d < b; d++){
                assert(cur_option < m_options);
                specializedCompress(in, &(m_options_compress_info[cur_option]), (void*)m_options_data_buffer[cur_option], b, d);
                cur_option++;
            }
        }
    } else {
        // Original Options:
        // BDI-Option 5: base_size = 8 bytes, delta_size = 1 byte
        // BDI-Option 6: base_size = 8 bytes, delta_size = 2 bytes
        // BDI-Option 7: base_size = 8 bytes, delta_size = 4 bytes
        // BDI-Option 8: base_size = 4 bytes, delta_size = 1 byte
        // BDI-Option 9: base_size = 4 bytes, delta_size = 2 bytes
        // BDI-Option 10: base_size = 2 bytes, delta_size = 1 byte
        for (b = 8; b >= 2; b /= 2) {
            for(d = 1; d <= (b/2); d *= 2){
                assert(cur_option < m_options);
                specializedCompress(in, &(m_options_compress_info[cur_option]), (void*)m_options_data_buffer[cur_option], b, d);
                cur_option++;
            }
        }
    }

    UInt32 bdi_compressed_size_bits = (UInt32) m_cache_line_size * 8;
    UInt8 bdi_chosen_option = 42; // If chosen_option == 42, cache line is not compressible (leave it uncompressed)
    for(i = 7; i < m_options; i++) {
        if(m_options_compress_info[i].is_compressible == true){
            if((m_options_compress_info[i].compressed_size * 8) < bdi_compressed_size_bits){
                bdi_compressed_size_bits = (m_options_compress_info[i].compressed_size * 8);
                bdi_chosen_option = i; // Update chosen option
            }
        }
    }
    // Add prefix len needed for decompression
    bdi_compressed_size_bits += m_prefix_len;

    UInt32 compressed_size_bits = 0;
    // Select best option between BDI and FPC
    if(fpc_compressed_size_bits < bdi_compressed_size_bits) { // FPC is selected
        compressed_size_bits = fpc_compressed_size_bits;
	    for (int i = 0; i < (m_cache_line_size * 8) / 32; i++) {
            if(fpc_chosen_options[i] < 6) {
                m_compress_options[fpc_chosen_options[i]]++;
                m_bits_saved_per_option[fpc_chosen_options[i]] += 32 - m_prefix_len - mask_to_bits[fpc_chosen_options[i]]; 
            } else if (fpc_chosen_options[i] == 6) {
                m_compress_options[fpc_chosen_options[i]]++;
                m_bits_saved_per_option[fpc_chosen_options[i]] += 32 - m_prefix_len - 8; 
            } else {
                assert(fpc_chosen_options[i] == 42); // Uncompressed word
            }
        }
    } else { // BDI is selected
        compressed_size_bits = bdi_compressed_size_bits;
        // Statistics
        if(bdi_chosen_option != 42) {
            assert(bdi_chosen_option >= 7);
            m_compress_options[bdi_chosen_option]++;
            m_bits_saved_per_option[bdi_chosen_option] += ((m_cache_line_size * 8) - bdi_compressed_size_bits); 
        }
    }


    for(i = 0; i < m_options; i++) {
        delete [] m_options_data_buffer[i];
    }
    delete [] m_options_compress_info;
    delete [] m_options_data_buffer;
    delete [] fpc_chosen_options;

    return compressed_size_bits; 
}



// UInt32 
// CompressionModelFPCBDI::decompressCacheLine(void *in, void *out)
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
CompressionModelFPCBDI::compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    UInt32 total_compressed_size = 0;
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        UInt32 compressed_page_size;
        UInt32 compressed_cache_lines;
        total_compression_latency += CompressionModelFPCBDI::compress(addr, m_page_size, core_id, &compressed_page_size, &compressed_cache_lines);
        total_compressed_size += compressed_page_size;
        (*address_to_num_cache_lines)[addr] = compressed_cache_lines;
    }
    *compressed_multipage_size = total_compressed_size;
    return total_compression_latency;
}


SubsecondTime
CompressionModelFPCBDI::decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        total_compression_latency += CompressionModelFPCBDI::decompress(addr, (*address_to_num_cache_lines)[addr], core_id);
    }
    return total_compression_latency;
}
