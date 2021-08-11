#ifndef __COMPRESSION_MODEL_H__
#define __COMPRESSION_MODEL_H__

#include "string.h"
#include "fixed_types.h"
#include "log.h"
#include "core.h"
#include "simulator.h"
#include "subsecond_time.h"
#include "core_manager.h"
#include <map>
#include <vector>

class CompressionModel
{
    public:
        CompressionModel() {}
        virtual ~CompressionModel() {}
        virtual SubsecondTime compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size, UInt32 *compressed_cache_lines) = 0;
        virtual SubsecondTime decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id) = 0;
        virtual SubsecondTime compress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, UInt32 *compressed_multipage_size, std::map<UInt64, UInt32> *address_to_num_cache_lines) = 0;
        virtual SubsecondTime decompress_multipage(std::vector<UInt64> addr_list, UInt32 num_pages, core_id_t core_id, std::map<UInt64, UInt32> *address_to_num_cache_lines) = 0;
        virtual void finalizeStats() = 0;
        virtual void update_bandwidth_utilization(double bandwidth_utilization);

        static CompressionModel* create(String name, UInt32 id, UInt32 page_size, UInt32 cache_line_size, String compression_type);
};

#endif /* __COMPRESSION_MODEL_H__ */
