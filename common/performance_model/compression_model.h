#ifndef __COMPRESSION_MODEL_H__
#define __COMPRESSION_MODEL_H__

#include "fixed_types.h"
#include "log.h"
#include "core.h"
#include "simulator.h"
#include "core_manager.h"

class CompressionModel
{
    public:
        CompressionModel() {}
        virtual ~CompressionModel() {}
        virtual UInt32 compress(IntPtr addr, size_t data_size, core_id_t core_id) = 0;
        virtual UInt32 decompress(IntPtr addr, size_t data_size, core_id_t core_id) = 0;

        static CompressionModel* create(String name, UInt32 page_size, UInt32 cache_line_size, String compression_type);
};

#endif /* __COMPRESSION_MODEL_H__ */
