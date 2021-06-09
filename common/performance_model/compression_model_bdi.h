#ifndef __COMPRESSION_MODEL_BDI_H__
#define __COMPRESSION_MODEL_BDI_H__

#include "compression_model.h"
#include "moving_average.h"
#include "fixed_types.h"
#include "subsecond_time.h"

// BDI.cc
#include <climits>
#include <cstdio>
#include <cstring>
#include <boost/tuple/tuple.hpp>

class CompressionModelBDI : public CompressionModel
{
public:
   CompressionModelBDI(String name, UInt32 page_size, UInt32 cache_line_size);
   ~CompressionModelBDI();

   UInt32 compress(IntPtr addr, size_t data_size, core_id_t core_id);
   UInt32 decompress(IntPtr addr, size_t data_size, core_id_t core_id);

private:
    String m_name; 
    UInt32 m_page_size; 
    UInt32 m_cache_line_size = 64; // TODO: may want configurable

    // BDI.cc
    long int ReadWord( void*, unsigned int,int);
    void WriteWord(void*, unsigned int,long int,int);
    boost::tuple<bool,unsigned int> zeros(void* , void* );
    boost::tuple<bool,unsigned int> repeated(void* , void* );
    boost::tuple<bool,unsigned int> Specialized_compress(void *, void *, int , int );
    bool checkDeltalimits(long int,int);
    UInt32 Compress(void *in, void *out);
    UInt32 Decompress(void *in, void *out);
    Byte* MakeCompBuf();

};

#endif /* __COMPRESSION_MODEL_BDI_H__ */
