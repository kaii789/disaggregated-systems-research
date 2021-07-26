#include "compression_model_lz78_bdi.h"
#include "utils.h"
#include "config.hpp"
#include "stats.h"

CompressionModelLZ78BDI::CompressionModelLZ78BDI(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
    , m_compression_granularity(Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78_bdi/compression_granularity"))
    , m_num_compress_pages(0)
    , m_sum_dict_size(0)
    , m_max_dict_size(0)
    , m_sum_max_dict_entry(0)
    , m_sum_avg_dict_entry(0)
    , m_max_dict_entry(0)
{
    // Set compression/decompression cycle latencies if configured
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78_bdi/compression_latency") != -1)
        m_compression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78_bdi/compression_latency");
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78_bdi/decompression_latency") != -1)
        m_decompression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78_bdi/decompression_latency");

    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78_bdi/word_size") != -1)
        m_word_size = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78_bdi/word_size");
        
    if (m_compression_granularity == -1)
        m_compression_granularity = m_page_size;

    m_cacheline_buffer = new char[m_cache_line_size];
 

    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];

    // Compression Statistics
    registerStatsMetric("compression", id, "avg_dictionary_size", &m_avg_dict_size);
    registerStatsMetric("compression", id, "max_dictionary_size", &m_max_dict_size);
    registerStatsMetric("compression", id, "avg_max_dictionary_entry", &m_avg_max_dict_entry);
    registerStatsMetric("compression", id, "avg_avg_dictionary_entry", &m_avg_avg_dict_entry);
    registerStatsMetric("compression", id, "max_dictionary_entry", &m_max_dict_entry);
}

CompressionModelLZ78BDI::~CompressionModelLZ78BDI()
{
}

void
CompressionModelLZ78BDI::finalizeStats()
{
    m_avg_dict_size = m_sum_dict_size / m_num_compress_pages;
    m_avg_max_dict_entry = m_sum_max_dict_entry / m_num_compress_pages;
    m_avg_avg_dict_entry = m_sum_avg_dict_entry / m_num_compress_pages;
}

SubsecondTime
CompressionModelLZ78BDI::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    // Get Data
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    if (data_size == m_cache_line_size)  { // If we compress in cache_line granularity
        core->getApplicationData(Core::NONE, Core::READ, addr, m_data_buffer, data_size, Core::MEM_MODELED_NONE); // Assume addr already points to page or cache line
    } else { // If we compress in page_size granularity, we shift to move to the start_addr of the corresponding page
        UInt64 page = addr & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
        core->getApplicationData(Core::NONE, Core::READ, page, m_data_buffer, data_size, Core::MEM_MODELED_NONE);
    }

    UInt32 total_bytes = 0;
    UInt32 total_accesses;
    total_bytes = compressData(m_data_buffer, m_compressed_data_buffer, data_size, &total_accesses); 
    //assert(total_bytes <= m_page_size && "[LZ78] Wrong compression!\n");
    //printf("total accesses %d\n", total_accesses);

    // Use total accesses instead of compressed cache lines for decompression
    *compressed_cache_lines = total_accesses;

    // Return compressed pages size in Bytes
    *compressed_page_size = total_bytes;

    // Return compression latency
    ComponentLatency compress_latency(ComponentLatency(core->getDvfsDomain(), m_compression_latency * total_accesses));
    return compress_latency.getLatency();
}

SubsecondTime
CompressionModelLZ78BDI::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    // Decompression algorithm works exactly the same as compression algorith.
    // Thus, decompression latency is equal to decompression algorithm
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), m_decompression_latency * compressed_cache_lines));
    return decompress_latency.getLatency();

}


SInt64
CompressionModelLZ78BDI::readWord(void *ptr, UInt32 idx, UInt32 word_size) // idx: which word of input ptr to read 
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
CompressionModelLZ78BDI::writeWord(void *ptr, UInt32 idx, SInt64 word, UInt32 word_size)
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
CompressionModelLZ78BDI::checkDeltaLimits(SInt64 delta, UInt32 delta_size)
{
    bool within_limits = true;
    switch (delta_size)
    {
        case 4:
            if ((delta < INT_MIN) || (delta > INT_MAX)) within_limits = false;
            break;
        case 3:
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
CompressionModelLZ78BDI::zeroValues(void* in, m_compress_info *res, void* out)
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
        writeWord(out, 0, base, sizeof(char));
    } else {
        res->is_compressible = false;
        res->compressed_size = m_cache_line_size;
    }
    return;
}

void
CompressionModelLZ78BDI::repeatedValues(void* in, m_compress_info *res, void* out)
{
    //  Repeated value compression checks if a cache line has the same 1/2/4/8 byte value repeated. If so, it compresses the cache line to the corresponding value
    SInt64 base;
    bool repeated;
    UInt32 i;
    UInt32 k;
    for(k = 1; k <= 8; k*=2) {
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
    }

    assert(repeated == false && "[BDI] repeated_values() failed!");
    res->is_compressible = false;
    res->compressed_size = m_cache_line_size;

    return;
}

void
CompressionModelLZ78BDI::specializedCompress(void *in, m_compress_info *res, void *out, SInt32 k, SInt32 delta_size)
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
CompressionModelLZ78BDI::compressCacheLine(void* in, void* out)
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

    // Option 1: a single value repeated multiple times within the cache line (8-byte granularity) 
    repeatedValues(in, &(m_options_compress_info[cur_option]), (void*) m_options_data_buffer[cur_option]);
    cur_option++;


        // Original Options:
        // Option 2: base_size = 8 bytes, delta_size = 1 byte
        // Option 3: base_size = 8 bytes, delta_size = 2 bytes
        // Option 4: base_size = 8 bytes, delta_size = 4 bytes
        // Option 5: base_size = 4 bytes, delta_size = 1 byte
        // Option 6: base_size = 4 bytes, delta_size = 2 bytes
        // Option 7: base_size = 2 bytes, delta_size = 1 byte
        for (b = 8; b >= 2; b /= 2) {
            for(d = 1; d <= (b/2); d *= 2){
                specializedCompress(in, &(m_options_compress_info[cur_option]), (void*)m_options_data_buffer[cur_option], b, d);
                cur_option++;
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
    }

    /*
    ((char*)out)[0] = (char) chosen_option; // Store chosen_option in the first byte of out data buffer
    if (chosen_option == 42)
        memcpy((void*)(((char*)out) + sizeof(char)), in, m_cache_line_size); // Store data in uncompressed format
    else
        memcpy((void*)(((char*)out) + sizeof(char)), m_options_data_buffer[chosen_option], compressed_size); // Stored data using the chosen compressed format
    */


    for(i = 0; i < m_options; i++) {
        delete [] m_options_data_buffer[i];
    }
    delete [] m_options_compress_info;
    delete [] m_options_data_buffer;

    return compressed_size; 
}


UInt32 
CompressionModelLZ78BDI::compressData(void* in, void* out, UInt32 data_size, UInt32 *total_accesses)
{
    UInt32 compressed_size = 0;
    compression_CAM.clear(); // What is the cost of flushing/clearing the dictionary?

    // statistics
    m_num_compress_pages++; 
    UInt64 max_entry = 0;
    UInt64 sum_entry = 0;


    UInt32 accesses = 0;
    UInt32 dictionary_size = 0; 
    UInt32 k, j, i = 0;
    UInt32 bdi_compressed_size;
    UInt32 out_indx = 0;
    UInt32 inserts = 0;
    string s;
    SInt64 cur_word;
    SInt8 cur_byte;
    map<string, UInt32>::iterator it;
    while ((i * m_word_size) < data_size) {

        // Read 64-byte cache line
        for(k=0; k < m_cache_line_size; k++) {
            m_cacheline_buffer[k] = (UInt8) readWord(in, i+k, 1);
        }
        bdi_compressed_size = compressCacheLine(m_cacheline_buffer, m_cacheline_buffer);
        if(bdi_compressed_size != m_cache_line_size) {
            compressed_size += bdi_compressed_size;
            s.clear();
            i += m_cache_line_size;
        }

        // Read next word byte-by-byte
        cur_word = readWord(in, i, m_word_size);
        for(j = 0; j < m_word_size; j++) {     
            cur_byte = (cur_word >> (8*j)) & 0xff; // Get j-th byte from the word
            s.push_back(cur_byte); 
        }
        
        it = compression_CAM.find(s); 
        accesses++;

        if(it == compression_CAM.end()) { // If not found in dictionary, add it 
            dictionary_size++;
            inserts++;
            compression_CAM.insert(pair<string, UInt32>(s, dictionary_size));
            accesses++;
            //writeWord(out, out_indx, cur_word, m_word_size);
            //out_indx++; 
            compressed_size += m_word_size;
    
            // statistics 
            if (s.size() > m_max_dict_entry)
                m_max_dict_entry = s.size();
            if (s.size() > max_entry)
                max_entry = s.size();
            sum_entry += s.size();
            // statistics 


            s.clear();
        }
        
        i++; 
    }

    // Metadata needed for decompression
    UInt32 dictionary_size_log2 = floorLog2(dictionary_size); // bits needed to index an entry in the dictionary
    // additional bytes need for metadata related to index the corresponding entries in the dictionary
    UInt32 index_bytes = (inserts * dictionary_size_log2) / 8; // Convert bits to bytes
    if ((inserts * dictionary_size_log2) % 8 != 0)
        index_bytes++;
    compressed_size += index_bytes;

    *total_accesses = accesses;
    compression_CAM.clear();

    // statistics 
    if(dictionary_size > m_max_dict_size)
        m_max_dict_size = dictionary_size;
    m_sum_dict_size += dictionary_size;
    m_sum_max_dict_entry += max_entry;
    m_sum_avg_dict_entry += (sum_entry / inserts);

    //printf("Compressed Size %d Dictionary Table Size %d %d and Max Entry Size %d Total Size (KB) %d Accesses %d\n", compressed_size, dictionary_size, inserts, max_string_size, dictionary_size * max_string_size / 1024, accesses);
    // statistics - RemoveMe

    return compressed_size;
} 

SubsecondTime
CompressionModelLZ78BDI::compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    UInt32 total_compressed_size = 0;
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        UInt32 compressed_page_size;
        UInt32 compressed_cache_lines;
        total_compression_latency += CompressionModelLZ78BDI::compress(addr, m_page_size, core_id, &compressed_page_size, &compressed_cache_lines);
        total_compressed_size += compressed_page_size;
        (*address_to_num_cache_lines)[addr] = compressed_cache_lines;
    }
    *compressed_multipage_size = total_compressed_size;
    return total_compression_latency;
}


SubsecondTime
CompressionModelLZ78BDI::decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        total_compression_latency += CompressionModelLZ78BDI::decompress(addr, (*address_to_num_cache_lines)[addr], core_id);
    }
    return total_compression_latency;
}
