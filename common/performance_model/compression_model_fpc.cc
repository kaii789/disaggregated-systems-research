#include "compression_model_fpc.h"

const long long unsigned CompressionModelFPC::mask[8]=
        {0x0000000000000000LL,
        0x00000000000000ffLL,
        0x000000000000ffffLL,
        0x0000000000ffffffLL,
        0x000000ffffffffffLL,
        0x0000ffffffffffffLL,
        0x00ffffffffffffffLL,
        0xffffffffffffffffLL};

CompressionModelFPC::CompressionModelFPC(String name, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
    , insize((int)cache_line_size/sizeof(double))
    , predsizem1(8) // TODO: fix
    , c_hash(0)
    , d_hash(0)
    , c_dhash(0)
    , d_dhash(0)
    , c_pred1(0)
    , c_pred2(0)
    , d_pred1(0)
    , d_pred2(0)
    , c_lastval(0)
    , d_lastval(0)
{
    m_cacheline_count = m_page_size / m_cache_line_size;
    m_data_buffer = new char[m_page_size];
    m_compressed_data_buffer = new char[m_page_size + m_cacheline_count];
    m_compressed_cache_line_sizes = new UInt32[m_cacheline_count];

    predsizem1 = (1L << predsizem1) - 1;
	c_fcm = (long long *)calloc(predsizem1 + 1, 8);
	// assert(NULL != c_fcm);
	c_dfcm = (long long *)calloc(predsizem1 + 1, 8);
	// assert(NULL != c_dfcm);
	d_fcm = (long long *)calloc(predsizem1 + 1, 8);
	// assert(NULL != d_fcm);
	d_dfcm = (long long *)calloc(predsizem1 + 1, 8);
	// assert(NULL != d_dfcm);
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
   double* inbuf= reinterpret_cast<double*> (_inbuf);
   unsigned char* outbuf= reinterpret_cast<unsigned char*> (_outbuf);
 
	LOG_PRINT("Recieved to compress %i bytes",insize);
	register long i, out, intot, code, bcode;
	register long long val,xor1,xor2,stride;
	bcode=0;
	intot=insize;
	val=*(long long *)&inbuf[0];
	
	out = ((intot + 1) >> 1);
	
	*((long long *)&outbuf[(out >> 3) << 3]) = 0;
	

	for (i = 0; i < intot; i += 2) 
	{	xor1 = val ^ c_pred1;
		c_fcm[c_hash] = val;
		c_hash = ((c_hash << 6) ^ ((unsigned long long)val >> 48)) & predsizem1;
		c_pred1 = c_fcm[c_hash];

		stride = val - c_lastval;
   	xor2 = val ^ (c_lastval + c_pred2);
   	c_lastval = val;

		val=*(long long *)&inbuf[i + 1];
		c_dfcm[c_dhash] = stride;
      		c_dhash = ((c_dhash << 2) ^ ((unsigned long long)stride >> 40)) & predsizem1;
      		c_pred2 = c_dfcm[c_dhash];

		code = 0;

		if ((unsigned long long)xor1 > (unsigned long long)xor2) 
		{
        		code = 0x80;
        		xor1 = xor2;
 	  	}


		bcode = 7;                // 8 bytes
   	if (0 == (xor1 >> 56))
     		bcode = 6;              // 7 bytes
   	if (0 == (xor1 >> 48))
     		bcode = 5;              // 6 bytes
   	if (0 == (xor1 >> 40))
     		bcode = 4;              // 5 bytes
   	if (0 == (xor1 >> 24))
     		bcode = 3;              // 3 bytes
   	if (0 == (xor1 >> 16))
     		bcode = 2;              // 2 bytes
   	if (0 == (xor1 >> 8))
     		bcode = 1;              // 1 byte
   	if (0 == xor1)
     		bcode = 0;              // 0 bytes

      *((long long *)&outbuf[(out >> 3) << 3]) |= xor1 << ((out & 0x7) << 3);
      if (0 == (out & 0x7))
      	xor1 = 0;
      *((long long *)&outbuf[((out >> 3) << 3) + 8]) = (unsigned long long)xor1 >> (64 - ((out & 0x7) << 3));

  		out += bcode + (bcode >> 2);
  		code |= bcode << 4;

		xor1 = val ^ c_pred1;
		
		c_fcm[c_hash] = val;
		c_hash = ((c_hash << 6) ^ ((unsigned long long)val >> 48)) & predsizem1;
		c_pred1 = c_fcm[c_hash];

		stride = val - c_lastval;
  		xor2 = val ^ (c_lastval + c_pred2);
  		c_lastval = val;
		
		if((i+2)<intot)
   		val = *(long long *)&inbuf[i + 2];
	
		c_dfcm[c_dhash] = stride;
  		c_dhash = ((c_dhash << 2) ^ ((unsigned long long)stride >> 40)) & predsizem1;
  		c_pred2 = c_dfcm[c_dhash];

		bcode = code | 0x8;
		if ((unsigned long long)xor1 > (unsigned long long)xor2) 
		{
        		code = bcode;
	        	xor1 = xor2;
  		}

		

		bcode = 7;                // 8 bytes
  		if (0 == (xor1 >> 56))
     		bcode = 6;              // 7 bytes
  		if (0 == (xor1 >> 48))
     		bcode = 5;              // 6 bytes
  		if (0 == (xor1 >> 40))
     		bcode = 4;              // 5 bytes
  		if (0 == (xor1 >> 24))
     		bcode = 3;              // 3 bytes
  		if (0 == (xor1 >> 16))
     		bcode = 2;              // 2 bytes
  		if (0 == (xor1 >> 8))
     		bcode = 1;              // 1 byte
  		if (0 == xor1)
     		bcode = 0;              // 0 bytes

  		*((long long *)&outbuf[(out >> 3) << 3]) |= xor1 << ((out & 0x7) << 3);
  		if (0 == (out & 0x7))
     		xor1 = 0;
   	*((long long *)&outbuf[((out >> 3) << 3) + 8]) = (unsigned long long)xor1 >> (64 - ((out & 0x7) << 3));

  		out += bcode + (bcode >> 2);
		outbuf[(i >> 1)] = code | bcode;
      		
		
   }


	if (0 != (intot & 1)) 
   {
      		out -= bcode + (bcode >> 2);
	}
    		
   return (UInt32) out;
	
};

SubsecondTime
CompressionModelFPC::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), compressed_cache_lines * m_decompression_latency));
    return decompress_latency.getLatency();
}
