#include "compression_model_fpc.h"
#include "utils.h"

// Assume 32 bit word
const UInt32 CompressionModelFPC::mask[6]=
       {0x00000000, // Zero run
        0x00000007, // 4 Bit
        0x0000007f, // One byte
        0x00007fff, // Halfword
        0x7fff0000, // Halfword padded with a zero halfword
        0x007f007f}; // Two halfwords, each a byte

const UInt32 CompressionModelFPC::neg_check[6]=
       {0xffffffff, // N/A
        0xfffffff8, // 4 Bit
        0xffffff80, // One byte
        0xffff8000, // Halfword
        0xffffffff, // N/A
        0xff80ff80}; // Two halfwords, each a byte

CompressionModelFPC::CompressionModelFPC(String name, UInt32 page_size, UInt32 cache_line_size, int compression_latency_config, int decompression_latency_config)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
{
    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];
    m_compressed_cache_line_sizes = new UInt32[m_cacheline_count];

    // Set compression/decompression cycle latencies if configured
    if (compression_latency_config != -1)
        m_compression_latency = compression_latency_config;
    if (decompression_latency_config != -1)
        m_decompression_latency = decompression_latency_config;
}

SubsecondTime
CompressionModelFPC::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    // Get Data
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    if (data_size == m_cache_line_size)  { // If we compress in cache_line granularity
        core->getApplicationData(Core::NONE, Core::READ, addr, m_data_buffer, data_size, Core::MEM_MODELED_NONE); // Assume addr already points to page or cache line
    } else { // If we compress in page_size granularity, we shift to move to the start_addr of the corresponding page
        UInt64 page = addr & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
        core->getApplicationData(Core::NONE, Core::READ, page, m_data_buffer, data_size, Core::MEM_MODELED_NONE);
    }

    // FPC
    UInt32 total_bytes = 0;
    UInt32 total_compressed_cache_lines = 0;
    for (UInt32 i = 0; i < m_cacheline_count; i++)
    {
        m_compressed_cache_line_sizes[i] = compressCacheLine(m_data_buffer + i * m_cache_line_size, m_compressed_data_buffer + i * m_cache_line_size);
        total_bytes += m_compressed_cache_line_sizes[i];
        if (m_compressed_cache_line_sizes[i] < m_cache_line_size)
            total_compressed_cache_lines++;
    }
    assert(total_bytes <= m_page_size && "[FPC] Wrong compression!");

    // Return compressed cache lines
    *compressed_cache_lines = total_compressed_cache_lines;

    // Return compressed pages size in Bytes
    *compressed_page_size = total_bytes;

    // printf("[FPC Compression] Compressed Page Size: %u bytes", total_bytes);

    // Return compression latency
    ComponentLatency compress_latency(ComponentLatency(core->getDvfsDomain(), m_cacheline_count * m_compression_latency));
    return compress_latency.getLatency();
}

CompressionModelFPC::~CompressionModelFPC()
{
    delete [] m_data_buffer;
    delete [] m_compressed_data_buffer;
    delete [] m_compressed_cache_line_sizes;
}

UInt32 CompressionModelFPC::compressCacheLine(void* _inbuf, void* _outbuf)
{
	UInt32 *cache_line = (UInt32*)_inbuf;
	UInt32 compressed_size_bits = 0;
	UInt32 mask_to_bits[6] = {3, 4, 8, 16, 16, 16};
	const UInt8 prefix_len = 3;

	for (int i = 0; i < (m_cache_line_size * 8) / 32; i++)
	{
		UInt32 word = cache_line[i];

        bool is_pattern_matched = false;
		for (int j = 0; j < 6; j++)
		{
            // Pattern match and handle
			if (((word | mask[j]) == mask[j]) || ((int)word < 0 && word >= neg_check[j]))
			{
                compressed_size_bits += prefix_len;
				compressed_size_bits += mask_to_bits[j];
                is_pattern_matched = true;
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
                compressed_size_bits += prefix_len;
                compressed_size_bits += 8;
                is_pattern_matched = true;
                // printf("[FPC] pattern match %x\n", word);
            }
        }

        // None of the patterns match, so can't compress
        if (!is_pattern_matched)
        {
            compressed_size_bits += 32;
            // printf("[FPC] uncompressed %x\n", word);
        }
	}

	return (UInt32)((compressed_size_bits + 7) / 8); // Return compressed size in bytes
};

SubsecondTime
CompressionModelFPC::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), compressed_cache_lines * m_decompression_latency));
    return decompress_latency.getLatency();
}
