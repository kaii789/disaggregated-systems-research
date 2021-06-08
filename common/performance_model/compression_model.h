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
        void compress(IntPtr addr, size_t data_size, core_id_t core_id);
};

#endif /* __COMPRESSION_MODEL_H__ */