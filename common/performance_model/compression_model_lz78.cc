#include "compression_model_lz78.h"
#include "utils.h"
#include "config.hpp"

CompressionModelLZ78::CompressionModelLZ78(String name, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
    , m_compression_granularity(Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/compression_granularity"))
{
    // Set compression/decompression cycle latencies if configured
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/compression_latency") != -1)
        m_compression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/compression_latency");
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/decompression_latency") != -1)
        m_decompression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/decompression_latency");

    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/word_size") != -1)
        m_word_size = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/word_size");
        
    if (m_compression_granularity == -1)
        m_compression_granularity = m_page_size;

    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];
}

CompressionModelLZ78::~CompressionModelLZ78()
{
}

SubsecondTime
CompressionModelLZ78::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
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
    assert(total_bytes <= m_page_size && "[LZ78] Wrong compression!\n");
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
CompressionModelLZ78::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), compressed_cache_lines * m_decompression_latency));
    return decompress_latency.getLatency();

}


SInt64
CompressionModelLZ78::readWord(void *ptr, UInt32 idx, UInt32 word_size) // idx: which word of input ptr to read 
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
CompressionModelLZ78::writeWord(void *ptr, UInt32 idx, SInt64 word, UInt32 word_size)
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


UInt32 
CompressionModelLZ78::compressData(void* in, void* out, UInt32 data_size, UInt32 *total_accesses)
{
    UInt32 compressed_size = 0;
    compression_CAM.clear(); // What is the cost of flushing/clearing the dictionary?

    // statistics - RemoveMe
    UInt32 max_string_size = 0;
    UInt32 accesses = 0;
    // statistics - RemoveMe

    UInt32 dictionary_size = 0; 
    UInt32 j, i = 0;
    UInt32 out_indx = 0;
    UInt32 inserts = 0;
    string s;
    SInt64 cur_word;
    SInt8 cur_byte;
    map<string, UInt32>::iterator it;
    while ((i * m_word_size) < data_size) {
        // Read next word byte-by-byte
        cur_word = readWord(in, i, m_word_size);
        for(j = 0; j < m_word_size; j++) {     
            cur_byte = (cur_word >> (8*j)) & 0xff; // Get j-th byte from the word
            s.push_back(cur_byte); 
        }
        
        it = compression_CAM.find(s); 
        accesses++;

        if(it == compression_CAM.end()) { // If not found in dictionary
            dictionary_size++;
            inserts++;
            compression_CAM.insert(pair<string, UInt32>(s, dictionary_size));
            writeWord(out, out_indx, cur_word, m_word_size);
            out_indx++; 
            compressed_size += m_word_size;
    
            // statistics - RemoveMe
            if (s.size() > max_string_size)
                max_string_size = s.size();
            // statistics - RemoveMe

            accesses++;
            s.clear();
        }
        
        i++; 
    }

    // Metadata needed for decompression
    UInt32 dictionary_size_log2 = floorLog2(dictionary_size); // bits needed to index an entry in the dictionary
    // additional bytes need for metadata related to index the corresponding entries in the dictionary
    UInt32 index_bytes = (inserts * dictionary_size_log2) / 8 + 1; // Convert bits to bytes
    compressed_size += index_bytes;
    *total_accesses = accesses;
    compression_CAM.clear();

    // statistics - RemoveMe
    //printf("Compressed Size %d Dictionary Table Size %d %d and Max Entry Size %d Total Size (KB) %d Accesses %d\n", compressed_size, dictionary_size, inserts, max_string_size, dictionary_size * max_string_size / 1024, accesses);
    // statistics - RemoveMe

    return compressed_size;
} 

/*
UInt32
CompressionModelLZ78::decompressData(void* in, void* out, UInt32 data_size)
{

    decompression_CAM.clear(); // What is the cost of flushing/clearing the dictionary?

    // statistics - RemoveMe
    UInt32 max_string_size = 0;
    UInt32 accesses = 0;
    // statistics - RemoveMe

    UInt32 dictionary_size = 0; 
    UInt32 j, i = 0;
    UInt32 out_indx = 0;
    UInt32 inserts = 0;
    string s;
    SInt64 cur_word;
    SInt8 cur_byte;
    map<string, UInt32>::iterator it;
    while ((i * m_word_size) < data_size) {
        // Read next word byte-by-byte
        cur_word = readWord(in, i, m_word_size);
        for(j = 0; j < m_word_size; j++) {     
            cur_byte = (cur_word >> (8*j)) & 0xff; // Get j-th byte from the word
            s.push_back(cur_byte); 
        }
        
        it = compression_CAM.find(s); 
        
        // statistics - RemoveMe
        accesses++;
        // statistics - RemoveMe

        if(it == compression_CAM.end()) { // If not found in dictionary
            dictionary_size++;
            inserts++;
            compression_CAM.insert(pair<string, UInt32>(s, dictionary_size));
            writeWord(out, out_indx, cur_word, m_word_size);
            out_indx++; 
            compressed_size += m_word_size;
    
            // statistics - RemoveMe
            if (s.size() > max_string_size)
                max_string_size = s.size();
            accesses++;
            // statistics - RemoveMe

            s.clear();
        }
        
        i++; 
    }

    // Metadata needed for decompression
    UInt32 dictionary_size_log2 = floorLog2(dictionary_size); // bits needed to index an entry in the dictionary
    // additional bytes need for metadata related to index the corresponding entries in the dictionary
    UInt32 index_bytes = (inserts * dictionary_size_log2) / 8 + 1; // Convert bits to bytes
    compressed_size += index_bytes;

    decompression_CAM.clear();

    // statistics - RemoveMe
    printf("Decompressed Size %d Dictionary Table Size %d %d and Max Entry Size %d Total Size (KB) %d Accesses %d\n", compressed_size, dictionary_size, inserts, max_string_size, dictionary_size * max_string_size / 1024, accesses);
    // statistics - RemoveMe

    return 0;
}
*/

SubsecondTime
CompressionModelLZ78::compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    // TODO
    return SubsecondTime::Zero();
}


SubsecondTime
CompressionModelLZ78::decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    // TODO
    return SubsecondTime::Zero();
}
