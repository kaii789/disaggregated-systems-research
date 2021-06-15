#include "config.h"
#include "log.h"
#include "config.hpp"
#include "simulator.h"
#include "compression_model.h"
#include "compression_model_bdi.h"
#include "compression_model_fpc.h"

CompressionModel*
CompressionModel::create(String name, UInt32 page_size, UInt32 cache_line_size, String compression_type)
{
    if (compression_type == "bdi")
	{
        return new CompressionModelBDI(name, page_size, cache_line_size);
	}
    if (compression_type == "fpc")
	{
        return new CompressionModelFPC(name, page_size, cache_line_size);
	}
    else
    {
        LOG_PRINT_ERROR("Unrecognized Compression Model(%s)", compression_type.c_str());
        return (CompressionModel*) NULL;

    }
}
