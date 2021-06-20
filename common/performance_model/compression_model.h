#ifndef __COMPRESSION_MODEL_H__
#define __COMPRESSION_MODEL_H__

#include "string.h"
#include "fixed_types.h"
#include "log.h"
#include "core.h"
#include "simulator.h"
#include "subsecond_time.h"
#include "core_manager.h"

class CompressionModel
{
    public:
        CompressionModel() {}
        virtual ~CompressionModel() {}
        virtual SubsecondTime compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines) = 0;
        virtual SubsecondTime decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id) = 0;

        static CompressionModel* create(String name, UInt32 page_size, UInt32 cache_line_size, String compression_type, int compression_latency_config, int decompression_latency_config);
};

#endif /* __COMPRESSION_MODEL_H__ */
