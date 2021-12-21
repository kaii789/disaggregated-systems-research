#ifndef __DRAM_HARDWARE_CNTLR_H__
#define __DRAM_HARDWARE_CNTLR_H__

#include "dram_perf_model.h"
#include "queue_model.h"
#include "fixed_types.h"
#include "subsecond_time.h"
#include "dram_cntlr_interface.h"
#include "hashed_linked_list.h"

#include <vector>
#include <bitset>

class DramHardwareCntlr
{
    private:
        const core_id_t m_core_id;
        const AddressHomeLookup* m_address_home_lookup;
        const UInt32 m_cache_line_size;
        const UInt32 m_page_size;       // Memory page size (in bytes) in parent DramPerfModel (different from HW ddr page size)
        UInt32 m_r_partition_queues;    // Enable partitioned queues
        bool m_r_pq_cacheline_hw_no_queue_delay;  // When this is true, remove HW access queue delay from PQ=on cacheline requests' critical path to simulate prioritized cachelines
        bool m_use_detailed_cost_calculation;     // Whether to use the detailed method of calcuing DRAM HW access cost

        const UInt32 m_num_banks;       // number of banks in a rank
        const UInt32 m_num_banks_log2;
        const UInt32 m_num_bank_groups; // number of bank groups in a rank
        const UInt32 m_num_ranks;
        const UInt32 m_rank_offset;
        const UInt32 m_num_channels;
        const UInt32 m_channel_offset;
        const UInt32 m_home_lookup_bit;
        const UInt32 m_total_ranks;
        const UInt32 m_banks_per_channel;
        const UInt32 m_banks_per_bank_group;
        const UInt32 m_total_banks;
        const UInt32 m_total_bank_groups;
        const UInt32 m_data_bus_width;  // bus between dram and memory controller
        const UInt32 m_dram_speed;      // MHz, 533, 667, etc.
        const UInt32 m_dram_page_size;  // dram page size in bytes
        const UInt32 m_dram_page_size_log2;
        const bool m_open_page_mapping;
        const UInt32 m_column_offset;
        const UInt32 m_column_hi_offset;
        const UInt32 m_bank_offset;
        const bool m_randomize_address;
        const UInt32 m_randomize_offset;
        const UInt32 m_column_bits_shift; // Position of column bits for closed-page mapping (after cutting interleaving/channel/rank/bank from bottom)
        SubsecondTime m_dram_hw_fixed_latency;  // Only used in the simplified dram HW access cost queuing model, a fixed latency for dram access cost
        const ComponentBandwidth m_bus_bandwidth;
        const ComponentBandwidth m_r_dram_bus_bandwidth;
        const SubsecondTime m_bank_keep_open;
        const SubsecondTime m_bank_open_delay;
        const SubsecondTime m_bank_close_delay;
        const SubsecondTime m_dram_access_cost;
        const SubsecondTime m_r_added_dram_access_cost; // Additional penalty latency for remote HW dram access
        const SubsecondTime m_intercommand_delay;       // Rank availability
        const SubsecondTime m_intercommand_delay_short; // Rank availability
        const SubsecondTime m_intercommand_delay_long;  // Bank group availability
        const SubsecondTime m_controller_delay;         // Average pipeline delay for various DDR controller stages
        const SubsecondTime m_refresh_interval;         // tRFCI
        const SubsecondTime m_refresh_length;           // tRFC

        struct BankInfo
        {
            IntPtr open_page;
            SubsecondTime t_avail;
        };

        // Local Memory
        QueueModel* m_dram_queue_model_single;
        std::vector<QueueModel*> m_queue_model;
        std::vector<QueueModel*> m_rank_avail;
        std::vector<QueueModel*> m_bank_group_avail;
        std::vector<BankInfo> m_banks;

        // Remote memory
        QueueModel* m_r_dram_queue_model_single;
        std::vector<QueueModel*> m_r_queue_model;
        std::vector<QueueModel*> m_r_rank_avail;
        std::vector<QueueModel*> m_r_bank_group_avail;
        std::vector<BankInfo> m_r_banks;

        // Variables to keep track of stats
        UInt64 m_dram_page_hits;
        UInt64 m_dram_page_empty;
        UInt64 m_dram_page_closing;
        UInt64 m_dram_page_misses;
        SubsecondTime m_local_get_dram_access_cost_processing_time;
        SubsecondTime m_local_get_dram_access_cost_queue_delay;
        SubsecondTime m_remote_cacheline_get_dram_access_cost_processing_time;
        SubsecondTime m_remote_cacheline_get_dram_access_cost_queue_delay;
        SubsecondTime m_remote_page_get_dram_access_cost_processing_time;
        SubsecondTime m_remote_page_get_dram_access_cost_queue_delay;

        void parseDeviceAddress(IntPtr address, UInt32 &channel, UInt32 &rank, UInt32 &bank_group, UInt32 &bank, UInt32 &column, UInt64 &dram_page);
        UInt64 parseAddressBits(UInt64 address, UInt32 &data, UInt32 offset, UInt32 size, UInt64 base_address);
        
        SubsecondTime getDramAccessCostSimple(SubsecondTime start_time, UInt64 size, core_id_t requester, IntPtr address, ShmemPerf *perf, bool is_remote, bool is_exclude_cacheline, bool is_page);
        SubsecondTime getDramAccessCostDetailed(SubsecondTime start_time, UInt64 size, core_id_t requester, IntPtr address, ShmemPerf *perf, bool is_remote, bool is_exclude_cacheline, bool is_page);

    public:
        DramHardwareCntlr(core_id_t core_id, AddressHomeLookup* address_home_lookup, UInt32 cache_line_size, UInt32 page_size, UInt32 r_partition_queues);
        ~DramHardwareCntlr();

        SubsecondTime getDramAccessCost(SubsecondTime start_time, UInt64 size, core_id_t requester, IntPtr address, ShmemPerf *perf, bool is_remote, bool is_exclude_cacheline, bool is_page);
        SubsecondTime getDramWriteCost(SubsecondTime start_time, UInt64 size, core_id_t requester, IntPtr address, ShmemPerf *perf, bool is_exclude_cacheline, bool is_page);
};

#endif /* __DRAM_HARDWARE_CNTLR_H__ */
