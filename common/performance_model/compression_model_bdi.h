#ifndef __COMPRESSION_MODEL_BDI_H__
#define __COMPRESSION_MODEL_BDI_H__

#include "compression_model.h"
#include "moving_average.h"
#include "fixed_types.h"
#include "subsecond_time.h"

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
    UInt32 m_cache_line_size; 
};

#endif /* __COMPRESSION_MODEL_BDI_H__ */
