#include "config.h"
#include "log.h"
#include "config.hpp"
#include "simulator.h"
#include "compression_model.h"
#include "compression_model_ideal.h"
#include "compression_model_bdi.h"
#include "compression_model_fpc.h"
#include "compression_model_lcp.h"
#include "compression_model_fve.h"
#include "compression_model_lz4.h"
#include "compression_model_lz78.h"
#include "compression_model_lzw.h"
#include "compression_model_lzbdi.h"
#include "compression_model_zlib.h"

CompressionModel*
CompressionModel::create(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size, String compression_type)
{
    if (compression_type == "ideal")
    {
        return new CompressionModelIdeal(name, id, page_size, cache_line_size);
    }
    else if (compression_type == "bdi")
    {
        return new CompressionModelBDI(name, id, page_size, cache_line_size);
    }
    else if (compression_type == "fpc")
    {
        return new CompressionModelFPC(name, id, page_size, cache_line_size);
    }
    else if (compression_type == "lcp")
    {
        return new CompressionModelLCP(name, id, page_size, cache_line_size);
    }
    else if (compression_type == "fve")
    {
        return new CompressionModelFVE(name, id, page_size, cache_line_size);
    }
    else if (compression_type == "lz4")
    {
        return new CompressionModelLZ4(name, id, page_size, cache_line_size);
    }
    else if (compression_type == "lz78")
    {
        return new CompressionModelLZ78(name, id, page_size, cache_line_size);
    }
    else if (compression_type == "lzw")
    {
        return new CompressionModelLZW(name, id, page_size, cache_line_size);
    }
    else if (compression_type == "lzbdi")
    {
        return new CompressionModelLZBDI(name, id, page_size, cache_line_size);
    }
    else if (compression_type == "zlib")
    {
        return new CompressionModelZlib(name, id, page_size, cache_line_size);
    }
    else
    {
        LOG_PRINT_ERROR("Unrecognized Compression Model(%s)", compression_type.c_str());
        return (CompressionModel*) NULL;

    }
}
