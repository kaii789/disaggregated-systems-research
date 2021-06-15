#include "compression_model_fpc.h"

// Assume 64 bit word
const long long unsigned CompressionModelFPC::mask[6]=
       {0x0000000000000000LL, // Zero run
        0x00000000000000ffLL, // 4 Bit
        0x000000000000ffffLL, // One byte
        0x00000000ffffffffLL, // Halfword
        0xffffffff00000000LL, // Halfword padded with a zero halfword
        0x0000ffff0000ffffLL}; // Two halfwords, each a byte

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
	UInt64 *cache_line = (UInt64*)_inbuf;
	UInt32 compressed_size_bits = 0;
	UInt32 mask_to_bits[6] = {3, 4, 8, 32, 32, 16};
	const UInt8 prefix_len = 3;

	for (int i = 0; i < m_cache_line_size / 64; i++)
	{
		UInt64 word = cache_line[i];
		compressed_size_bits += prefix_len;
		for (int i = 0; i < 6; i++)
		{
			// TODO: How to handle words consisting of repeated bytes?
			if ((word | mask[i]) == mask[i])
			{
				compressed_size_bits += mask_to_bits[i];
				break;
			}
		}
		compressed_size_bits += 64; // Uncompressed word
	}

	return (UInt32)compressed_size_bits / 8; // Return compressed size in bytes
};

SubsecondTime
CompressionModelFPC::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), compressed_cache_lines * m_decompression_latency));
    return decompress_latency.getLatency();
}
