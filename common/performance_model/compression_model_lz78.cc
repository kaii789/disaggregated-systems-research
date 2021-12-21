#include "compression_model_lz78.h"
#include "utils.h"
#include "config.hpp"
#include "stats.h"

CompressionModelLZ78::CompressionModelLZ78(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
    , m_compression_granularity(Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/compression_granularity"))
    , m_num_compress_pages(0)
    , m_sum_dict_size(0)
    , m_max_dict_size(0)
    , m_sum_max_dict_entry(0)
    , m_sum_avg_dict_entry(0)
    , m_max_dict_entry(0)
    , m_num_overflowed_pages(0)
    , dictsize_count_stats(m_dictsize_saved_stats_num_points, 0)
    , bytes_saved_count_stats(m_dictsize_saved_stats_num_points, 0)
    , accesses_count_stats(m_dictsize_saved_stats_num_points, 0)
    , max_entry_bytes_count_stats(m_dictsize_saved_stats_num_points, 0)
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
  
    m_size_limit = Sim()->getCfg()->getBool("perf_model/dram/compression_model/lz78/size_limit");
    if ((Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/dictionary_size") != -1) && (Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/entry_size") != -1)) {
        compression_CAM = new CAMLZ("lz78_dictionary", Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/dictionary_size"),  Sim()->getCfg()->getInt("perf_model/dram/compression_model/lz78/entry_size"), Sim()->getCfg()->getBool("perf_model/dram/compression_model/lz78/size_limit"));
    } else {
        compression_CAM = new CAMLZ("lz78_dictionary",  Sim()->getCfg()->getBool("perf_model/dram/compression_model/lz78/size_limit"));
    }

    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];

    // Compression Statistics
    registerStatsMetric("compression", id, "avg_dictionary_size", &m_avg_dict_size);
    registerStatsMetric("compression", id, "max_dictionary_size", &m_max_dict_size);
    registerStatsMetric("compression", id, "avg_max_dictionary_entry", &m_avg_max_dict_entry);
    registerStatsMetric("compression", id, "avg_avg_dictionary_entry", &m_avg_avg_dict_entry);
    registerStatsMetric("compression", id, "max_dictionary_entry", &m_max_dict_entry);
    registerStatsMetric("compression", id, "num_overflowed_pages", &m_num_overflowed_pages);

    // Register stats for dictionary table
    for (UInt32 i = 0; i < m_dictsize_saved_stats_num_points - 1; ++i) {
        UInt32 percentile = (UInt32)(100.0 / m_dictsize_saved_stats_num_points) * (i + 1);
        String stat_name = "lz-dictsize-count-p";
        stat_name += std::to_string(percentile).c_str();
        registerStatsMetric("compression", id, stat_name, &(dictsize_count_stats[i]));
        stat_name = "lz-bytes_saved-count-p";
        stat_name += std::to_string(percentile).c_str();
        registerStatsMetric("compression", id, stat_name, &(bytes_saved_count_stats[i]));
        stat_name = "lz-accesses-count-p";
        stat_name += std::to_string(percentile).c_str();
        registerStatsMetric("compression", id, stat_name, &(accesses_count_stats[i]));
        stat_name = "lz-max_entry_bytes-count-p";
        stat_name += std::to_string(percentile).c_str();
        registerStatsMetric("compression", id, stat_name, &(max_entry_bytes_count_stats[i]));
 
    }
    // Make sure last one is p100
    registerStatsMetric("compression", id, "lz-dictsize-count-p100", &(dictsize_count_stats[m_dictsize_saved_stats_num_points - 1]));
    registerStatsMetric("compression", id, "lz-bytes_saved-count-p100", &(bytes_saved_count_stats[m_dictsize_saved_stats_num_points - 1]));
    registerStatsMetric("compression", id, "lz-accesses-count-p100", &(accesses_count_stats[m_dictsize_saved_stats_num_points - 1]));
    registerStatsMetric("compression", id, "lz-max_entry_bytes-count-p100", &(max_entry_bytes_count_stats[m_dictsize_saved_stats_num_points - 1]));

}

CompressionModelLZ78::~CompressionModelLZ78()
{
    delete compression_CAM;
}

void
CompressionModelLZ78::finalizeStats()
{
    if (m_num_compress_pages == 0) {
        return;
    }
    m_avg_dict_size = m_sum_dict_size / m_num_compress_pages;
    m_avg_max_dict_entry = m_sum_max_dict_entry / m_num_compress_pages;
    m_avg_avg_dict_entry = m_sum_avg_dict_entry / m_num_compress_pages;

    if(m_dictsize_saved_map.size() > 0) {
        std::vector<std::pair<UInt32, UInt64>> dictsize_saved_counts;  // first is the dictionary size, second is the bytes saved
        for (auto it = m_dictsize_saved_map.begin(); it != m_dictsize_saved_map.end(); ++it) {
            dictsize_saved_counts.push_back(std::pair<UInt32, UInt64>(it->first, it->second));
        }
        std::sort(dictsize_saved_counts.begin(), dictsize_saved_counts.end());  // sort by dictionary size

        std::vector<std::pair<UInt32, UInt64>> dictsize_accesses_counts;  // first is the dictionary size, second is the number of accesses
        for (auto it = m_dictsize_accesses_map.begin(); it != m_dictsize_accesses_map.end(); ++it) {
            dictsize_accesses_counts.push_back(std::pair<UInt32, UInt64>(it->first, it->second));
        }
        std::sort(dictsize_accesses_counts.begin(), dictsize_accesses_counts.end());  // sort by dictionary size

        std::vector<std::pair<UInt32, UInt32>> dictsize_max_entry_counts;  // first is the dictionary size, second is the number of bytes for the maximum entry
        for (auto it = m_dictsize_max_entry_map.begin(); it != m_dictsize_max_entry_map.end(); ++it) {
            dictsize_max_entry_counts.push_back(std::pair<UInt32, UInt32>(it->first, it->second));
        }
        std::sort(dictsize_max_entry_counts.begin(), dictsize_max_entry_counts.end());  // sort by dictionary size


        // Update stats vector
        UInt64 total_bytes_saved = 0;
        SInt32 prev_index = -1;
        UInt64 bytes_saved = 0;
        UInt64 accesses = 0;
        UInt32 max_entry = 0;        
        for (UInt32 i = 0; i < m_dictsize_saved_stats_num_points - 1; ++i) {
            UInt64 index = (UInt64)((double)(i + 1) / m_dictsize_saved_stats_num_points * (dictsize_saved_counts.size() - 1));
            dictsize_count_stats[i] = (UInt64) dictsize_saved_counts[index].first; // Store the dictionary size
            for(SInt32 j = prev_index + 1; j <= (SInt32)index; j++) 
                bytes_saved += dictsize_saved_counts[j].second;
            bytes_saved_count_stats[i] = bytes_saved; // Store the number of bytes saved for that range of dictionary size

            for(SInt32 j = prev_index + 1; j <= (SInt32)index; j++) 
                accesses += dictsize_accesses_counts[j].second;
            accesses_count_stats[i] = accesses; // Store the number of accesses for that range of dictionary size


            for(SInt32 j = prev_index + 1; j <= (SInt32)index; j++) 
                if(dictsize_max_entry_counts[j].second > max_entry)
                    max_entry = dictsize_max_entry_counts[j].second;
            max_entry_bytes_count_stats[i] = (UInt64) max_entry;

            prev_index = index;
            total_bytes_saved += bytes_saved;
            bytes_saved = 0;
            accesses = 0;
            max_entry = 0;
        }

        // Make sure last one is p100
        dictsize_count_stats[m_dictsize_saved_stats_num_points - 1] = (UInt64) dictsize_saved_counts[dictsize_saved_counts.size() - 1].first;
        for(SInt32 j = prev_index + 1; j <= (SInt32)dictsize_saved_counts.size() - 1; j++) 
            bytes_saved += dictsize_saved_counts[j].second;
        total_bytes_saved += bytes_saved;
        bytes_saved_count_stats[m_dictsize_saved_stats_num_points - 1] = bytes_saved; // Store the number of bytes saved for that range of dictionary size
        std::cout << "Total bytes saved: " << total_bytes_saved << std::endl;
        for(SInt32 j = prev_index + 1; j <= (SInt32)dictsize_accesses_counts.size() - 1; j++) 
            accesses += dictsize_accesses_counts[j].second;
        accesses_count_stats[m_dictsize_saved_stats_num_points - 1] = accesses; // Store the number of accesses for that range of dictionary size
        for(SInt32 j = prev_index + 1; j <= (SInt32)dictsize_max_entry_counts.size() - 1; j++) 
            if(dictsize_max_entry_counts[j].second > max_entry)
                max_entry = dictsize_max_entry_counts[j].second;
        max_entry_bytes_count_stats[m_dictsize_saved_stats_num_points - 1] = (UInt64) max_entry;

        
        /*
        // Print detailed statistics
        UInt32 num_bins = 20;
        double percentage;
        UInt32 dictsize;
        UInt64 total_bytes_saved = 0;
        UInt64 bytes_saved = 0;
        int prev_index = - 1;
        int index = 0;
        for(int bin = 0; bin < num_bins; bin++) {
            percentage = (double) bin / num_bins;
            index = (int) (percentage * (dictsize_saved_counts.size() - 1));
            dictsize = dictsize_saved_counts[index].first;
            for(int j = prev_index + 1; j <= index; j++) 
                bytes_saved += dictsize_saved_counts[j].second;
            std::cout << "percentage: " << percentage << ", vector index: " << index << ", dictsize: " << dictsize << ", bytes_saved: " << bytes_saved << std::endl;

            prev_index = index;
            total_bytes_saved += bytes_saved;
            bytes_saved = 0;
        }
    
        dictsize = dictsize_saved_counts[dictsize_saved_counts.size() - 1].first;
        for(int j = prev_index + 1; j <= dictsize_saved_counts.size() - 1; j++) 
            bytes_saved += dictsize_saved_counts[j].second;
        total_bytes_saved += bytes_saved;
        std::cout << "percentage: 1.0, vector index: " << dictsize_saved_counts.size() - 1 << ", dictsize: " << dictsize << ", bytes_saved: " << bytes_saved << std::endl;
        std::cout << "Total bytes saved: " << total_bytes_saved << std::endl;
        // Print detailed statistics
        */

    }
    
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

    // If the page has been overflowed and is about to be sent in an uncompressed format (i.e., its size is m_page_size),
    // fix the compressed_cache_lines to be 0, such that the decompression latency to be added will be 0 (page is left uncompresed)
    if (total_bytes == m_page_size)
        *compressed_cache_lines = 0;


    // Return compression latency
    if (m_size_limit == false) {
        ComponentLatency compress_latency(ComponentLatency(core->getDvfsDomain(), m_compression_latency * total_accesses));
        return compress_latency.getLatency();
    } else {
        double compression_latency =  1.1 * total_accesses; // In nanoseconds - Assuming 1.1nsec per access in Dictionary table of 768 entries and 64 bytes each entry
        return SubsecondTime::NS(compression_latency);
    }
    
    // Never reaches here
    return SubsecondTime::Zero();
}

SubsecondTime
CompressionModelLZ78::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    // Decompression algorithm works exactly the same as compression algorith.
    // Thus, decompression latency is equal to decompression algorithm
    if (m_size_limit == false) {
        ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), m_decompression_latency * compressed_cache_lines));
        return decompress_latency.getLatency();
    } else {
        double decompression_latency =  1.1 * compressed_cache_lines; // In nanoseconds - Assuming 1.1nsec per access in Dictionary table of 768 entries and 64 bytes each entry
        return SubsecondTime::NS(decompression_latency);
    }
 
    // Never reaches here
    return SubsecondTime::Zero();
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
    bool overflow = false;
    compression_CAM->clear(); // What is the cost of flushing/clearing the dictionary?

    // statistics
    m_num_compress_pages++; 
    UInt64 max_entry = 0;
    UInt64 sum_entry = 0;


    UInt32 accesses = 0;
    UInt32 dictionary_size = 0; 
    UInt32 j, i = 0;
    // UInt32 out_indx = 0;
    UInt32 inserts = 0;
    string s;
    SInt64 cur_word;
    SInt8 cur_byte;
    bool found, inserted;
    while (((i * m_word_size) < data_size) && (overflow == false)) {
        // Read next word byte-by-byte
        cur_word = readWord(in, i, m_word_size);
        for(j = 0; j < m_word_size; j++) {     
            cur_byte = (cur_word >> (8*j)) & 0xff; // Get j-th byte from the word
            s.push_back(cur_byte); 
        }
        
        found = compression_CAM->find(s); 
        accesses++;

        if(found == false) { // If not found in dictionary, add it 
            dictionary_size++;
            inserts++;
            inserted = compression_CAM->insert(s);
            if (inserted == true)
                accesses++;
            else
                inserts++; // an additional index is needed to capture that this particular byte was not inserted in the dictionary
            //writeWord(out, out_indx, cur_word, m_word_size);
            //out_indx++; 
            compressed_size += m_word_size;

            // If the compressed size is larger than m_page_size, Send the page in an uncompressed format 
            if (compressed_size >= m_page_size)
                overflow = true; // Break compression if compressed page is larger than m_page_size
                

            // statistics 
            if (inserted == true) {
                if (s.size() > m_max_dict_entry)
                    m_max_dict_entry = s.size();
                if (s.size() > max_entry)
                    max_entry = s.size();
                sum_entry += s.size();
            }
            // statistics 


            s.clear();
        }
        
        i++; 
    }

    // Metadata needed for decompression
    dictionary_size = compression_CAM->getSize();
    UInt32 dictionary_size_log2 = floorLog2(dictionary_size); // bits needed to index an entry in the dictionary
    // additional bytes need for metadata related to index the corresponding entries in the dictionary
    UInt32 index_bytes = (inserts * dictionary_size_log2) / 8; // Convert bits to bytes
    if ((inserts * dictionary_size_log2) % 8 != 0)
        index_bytes++;
    compressed_size += index_bytes;

    *total_accesses = accesses;
    compression_CAM->clear();

    // If the compressed size is larger than m_page_size, Send the page in an uncompressed format 
    // (assuming that we check the payload of the packet. 
    // If data payload size = m_page_size, we avoid all the latencies related to decompressing the page
    if ((compressed_size >= m_page_size) || (overflow == true)) {
        compressed_size = m_page_size;
        overflow = true;
        m_num_overflowed_pages++;
    }

    // statistics 
    if (overflow == false) {
        if(dictionary_size > m_max_dict_size)
            m_max_dict_size = dictionary_size;
        m_sum_dict_size += dictionary_size;
        m_sum_max_dict_entry += max_entry;
        m_sum_avg_dict_entry += (sum_entry / inserts);
        if(m_dictsize_saved_map.count(dictionary_size) == 0) {
            // Compressed bytes
            m_dictsize_saved_map[dictionary_size] = 0;         
            if (m_page_size >= compressed_size)
                m_dictsize_saved_map[dictionary_size] += (UInt64)(m_page_size - compressed_size); // Assuming that lz is 'only' used to compressed data in page-granularity

            m_dictsize_accesses_map[dictionary_size] = 0;         
            m_dictsize_accesses_map[dictionary_size] += (UInt64) accesses;
            // Max_entry size 
            m_dictsize_max_entry_map[dictionary_size] = (UInt32) max_entry;         
        } else {
            // Compressed bytes
            if (m_page_size >= compressed_size)
                m_dictsize_saved_map[dictionary_size] += (UInt64)(m_page_size - compressed_size); // Assuming that lz is 'only' used to compressed data in page-granularity
            m_dictsize_accesses_map[dictionary_size] += (UInt64) accesses;
            // Max_entry size 
            if(m_dictsize_max_entry_map[dictionary_size] < (UInt32) max_entry) 
                m_dictsize_max_entry_map[dictionary_size] = (UInt32) max_entry;         
        }
    }
    // statistics

    //printf("Compressed Size %d Dictionary Table Size %d %d and Max Entry Size %d Total Size (KB) %d Accesses %d\n", compressed_size, dictionary_size, inserts, max_string_size, dictionary_size * max_string_size / 1024, accesses);
    // statistics - RemoveMe

    return compressed_size;
} 

SubsecondTime
CompressionModelLZ78::compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    UInt32 total_compressed_size = 0;
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        UInt32 compressed_page_size;
        UInt32 compressed_cache_lines;
        total_compression_latency += CompressionModelLZ78::compress(addr, m_page_size, core_id, &compressed_page_size, &compressed_cache_lines);
        total_compressed_size += compressed_page_size;
        (*address_to_num_cache_lines)[addr] = compressed_cache_lines;
    }
    *compressed_multipage_size = total_compressed_size;
    return total_compression_latency;
}


SubsecondTime
CompressionModelLZ78::decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines)
{
    SubsecondTime total_compression_latency = SubsecondTime::Zero();
    for (UInt32 i = 0; i < num_pages; i++) {
        UInt64 addr = addr_list.at(i);
        total_compression_latency += CompressionModelLZ78::decompress(addr, (*address_to_num_cache_lines)[addr], core_id);
    }
    return total_compression_latency;
}
