#include "compression_model_fpc.h"

// Assume 32 bit word
const UInt32 CompressionModelFPC::mask[6]=
       {0x00000000LL, // Zero run
        0x0000000fLL, // 4 Bit
        0x000000ffLL, // One byte
        0x0000ffffLL, // Halfword
        0xffff0000LL, // Halfword padded with a zero halfword
        0x00ff00ffLL}; // Two halfwords, each a byte

const UInt32 CompressionModelFPC::neg_check[6]=
       {0x00000000LL, // N/A
        0xfffffff0LL, // 4 Bit
        0xffffff00LL, // One byte
        0xffff0000LL, // Halfword
        0x00000000LL, // N/A
        0xff00ff00LL}; // Two halfwords, each a byte

CompressionModelFPC::CompressionModelFPC(String name, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
{
    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];
    m_compressed_cache_line_sizes = new UInt32[m_cacheline_count];
}

SubsecondTime
CompressionModelFPC::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines)
{
    // Get Data
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    core->getApplicationData(Core::NONE, Core::READ, addr, m_data_buffer, data_size, Core::MEM_MODELED_NONE); // Assume addr already points to page or cache line

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

    printf("[FPC Compression] Compressed Page Size: %u bytes", total_bytes);

    // Return compression latency
    ComponentLatency compress_latency(ComponentLatency(core->getDvfsDomain(), total_compressed_cache_lines * m_compression_latency));
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

	for (int i = 0; i < m_cache_line_size / 32; i++)
	{
		UInt32 word = cache_line[i];
		compressed_size_bits += prefix_len;

        bool is_pattern_matched = false;
		for (int j = 0; j < 6; j++)
		{
            // Pattern match and handle
			if (((word | mask[j]) == mask[j]) || ((int)word < 0 && word >= neg_check[j]))
			{
				compressed_size_bits += mask_to_bits[j];
                is_pattern_matched = true;
				break;
			}
		}

        if (!is_pattern_matched)
        {
            // Handle words consisting of repeated bytes
            bool repeated = true;
            SInt8 base = ((SInt8*)word)[0];
            for (int j = 1; j < 4; j++)
                if ((base - ((SInt8*)word)[j]) != 0) {
                    repeated = false;
                    break;
                }
            compressed_size_bits += 8;
            is_pattern_matched = true;
        }

        // None of the patterns match, so can't compress
        if (!is_pattern_matched)
            compressed_size_bits += 32;
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
