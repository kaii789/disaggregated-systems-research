#include "compression_model_lzw.h"
#include "utils.h"
#include "config.hpp"
#include <math.h>

CompressionModelLZW::CompressionModelLZW(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
    , m_compression_granularity(Sim()->getCfg()->getInt("perf_model/dram/compression_model/lzW/compression_granularity"))
{
    // Set compression/decompression cycle latencies if configured
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lzW/compression_latency") != -1)
        m_compression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lzW/compression_latency");
    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lzW/decompression_latency") != -1)
        m_decompression_latency = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lzW/decompression_latency");

    if (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lzW/word_size") != -1)
        m_word_size = Sim()->getCfg()->getInt("perf_model/dram/compression_model/lzW/word_size");
        
    if (m_compression_granularity == -1)
        m_compression_granularity = m_page_size;

    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];
}

CompressionModelLZW::~CompressionModelLZW()
{
}

void
CompressionModelLZW::finalizeStats()
{
}

SubsecondTime
CompressionModelLZW::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
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
    //assert(total_bytes <= m_page_size && "[LZW] Wrong compression!\n");
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
CompressionModelLZW::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    // Decompression algorithm works exactly the same as compression algorith.
    // Thus, decompression latency is equal to decompression algorithm
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), m_decompression_latency * compressed_cache_lines));
    return decompress_latency.getLatency();

}


SInt64
CompressionModelLZW::readWord(void *ptr, UInt32 idx, UInt32 word_size) // idx: which word of input ptr to read 
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
CompressionModelLZW::writeWord(void *ptr, UInt32 idx, SInt64 word, UInt32 word_size)
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
CompressionModelLZW::compressData(void* in, void* out, UInt32 data_size, UInt32 *total_accesses)
{
    UInt32 j;
    UInt32 dictionary_size = 0; 
    UInt32 compressed_size = 0;
    string s;
    UInt8 cur_byte;
    compression_CAM.clear(); // What is the cost of flushing/clearing the dictionary?
     
    for(j = 0; j < pow(2, m_word_size * 8); j++) {
        dictionary_size++;
        cur_byte = (UInt8) j; 
        s.push_back(cur_byte); 
        compression_CAM.insert(pair<string, UInt32>(s, dictionary_size));
        s.clear();
    }

    // statistics - RemoveMe
    UInt32 max_string_size = 0;
    // statistics - RemoveMe

    UInt32 accesses = 0;
    UInt32 i = 0;
    UInt32 out_indx = 0;
    UInt32 inserts = pow(2, m_word_size * 8);
    UInt8 last_byte;
    compression_CAM.clear(); // What is the cost of flushing/clearing the dictionary?
    SInt64 cur_word;
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

        if(it == compression_CAM.end()) { // If not found in dictionary, add it 
            dictionary_size++;
            inserts++;
            compression_CAM.insert(pair<string, UInt32>(s, dictionary_size));
            accesses++;
            //writeIndex to output

            // statistics - RemoveMe
            if (s.size() > max_string_size)
                max_string_size = s.size();
            // statistics - RemoveMe

            s.clear();
            for(j = 0; j < m_word_size; j++) {     
                cur_byte = (cur_word >> (8*j)) & 0xff; // Get j-th byte from the word
                s.push_back(cur_byte); 
            }
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

    // statistics - RemoveMe
    //printf("Compressed Size %d Dictionary Table Size %d %d and Max Entry Size %d Total Size (KB) %d Accesses %d\n", compressed_size, dictionary_size, inserts, max_string_size, dictionary_size * max_string_size / 1024, accesses);
    // statistics - RemoveMe

    return compressed_size;
} 

SubsecondTime
CompressionModelLZW::compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    UInt32 total_compressed_size = 0;
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        UInt32 compressed_page_size;
        UInt32 compressed_cache_lines;
        total_compression_latency += CompressionModelLZW::compress(addr, m_page_size, core_id, &compressed_page_size, &compressed_cache_lines);
        total_compressed_size += compressed_page_size;
        (*address_to_num_cache_lines)[addr] = compressed_cache_lines;
    }
    *compressed_multipage_size = total_compressed_size;
    return total_compression_latency;
}


SubsecondTime
CompressionModelLZW::decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        total_compression_latency += CompressionModelLZW::decompress(addr, (*address_to_num_cache_lines)[addr], core_id);
    }
    return total_compression_latency;
}
