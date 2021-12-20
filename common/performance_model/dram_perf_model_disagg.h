#ifndef __DRAM_PERF_MODEL_DISAGG_H__
#define __DRAM_PERF_MODEL_DISAGG_H__

#include "dram_perf_model.h"
#include "queue_model.h"
#include "compression_cntlr.h"
#include "prefetcher_model.h"
#include "fixed_types.h"
#include "subsecond_time.h"
#include "dram_cntlr_interface.h"
#include "hashed_linked_list.h"

#include <vector>
#include <bitset>
#include <map>
#include <unordered_map>
#include <list>
// #include <set>
#include <unordered_set>
#include <algorithm>

class DramPerfModelDisagg : public DramPerfModel
{
    private:
        const core_id_t m_core_id;
        const AddressHomeLookup* m_address_home_lookup;
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
        ComponentBandwidth m_r_bus_bandwidth;   // Remote
        ComponentBandwidth m_r_part_bandwidth;  // Remote - Partitioned Queues => Page Queue
        ComponentBandwidth m_r_part2_bandwidth; // Remote - Partitioned Queues => Cacheline Queue
        double m_r_bw_scalefactor;              // Remote memory bandwidth is ddr bandwidth scaled down by m_r_bw_scalefactor
        bool m_use_dynamic_bandwidth;
        bool m_use_dynamic_latency;
        const SubsecondTime m_bank_keep_open;
        const SubsecondTime m_bank_open_delay;
        const SubsecondTime m_bank_close_delay;
        const SubsecondTime m_dram_access_cost;
        const SubsecondTime m_r_added_dram_access_cost;
        const SubsecondTime m_intercommand_delay;       // Rank availability
        const SubsecondTime m_intercommand_delay_short; // Rank availability
        const SubsecondTime m_intercommand_delay_long;  // Bank group availability
        const SubsecondTime m_controller_delay;         // Average pipeline delay for various DDR controller stages
        const SubsecondTime m_refresh_interval;         // tRFCI
        const SubsecondTime m_refresh_length;           // tRFC
        SubsecondTime m_r_added_latency; // Additional remote latency
        UInt64 m_r_added_latency_int;
        const UInt32 m_r_datamov_threshold; // Move data if greater than yy
        const UInt32 m_cache_line_size;
        const UInt32 m_page_size; // Memory page size (in bytes) in disagg.cc (different from ddr page size)
        const UInt32 m_localdram_size; // Local DRAM size
        const bool m_enable_remote_mem; // Enable remote memory with the same DDR type as local for now
        const bool m_r_simulate_tlb_overhead; // Simulate tlb overhead
        const bool m_r_simulate_datamov_overhead; // Simulate datamovement overhead for remote memory
        const UInt32 m_r_mode ; // Randomly assigned = 0; Cache = 1 (local DRAM as a cache) 
        const UInt32 m_r_partitioning_ratio ; // % in local memory 
        const bool m_r_simulate_sw_pagereclaim_overhead; // Simulate tlb overhead
        const bool m_r_exclusive_cache; // Simulate tlb overhead
        const bool m_remote_init; // All pages are initially allocated to remote memory
        UInt32 m_r_disturbance_factor; // Other systems using the remote memory and creating disturbance
        const bool m_r_dontevictdirty; // Do not evict dirty data
        const bool m_r_enable_selective_moves; 
        UInt32 m_r_partition_queues; // Enable partitioned queues
        double m_r_cacheline_queue_fraction; // The fraction of remote bandwidth used for the cacheline queue (decimal between 0 and 1) 
        bool m_use_dynamic_cl_queue_fraction_adjustment; // Whether to dynamically adjust m_r_cacheline_queue_fraction
        const bool m_r_cacheline_gran; // Move data and operate in cacheline granularity
        const double m_r_reserved_bufferspace; // Max % of local DRAM that can be reserved for pages in transit
        const UInt32 m_r_limit_redundant_moves; 
        const bool m_r_throttle_redundant_moves;
        const bool m_r_use_separate_queue_model;  // Whether to use the separate remote queue model
        double m_r_page_queue_utilization_threshold;  // When the datamovement queue for pages has percentage utilization above this, remote pages aren't moved to local
        double m_r_cacheline_queue_type1_utilization_threshold;
        double m_r_cacheline_queue_type2_utilization_threshold;
        double m_r_mode_5_limit_moves_threshold;  // When m_r_mode == 5, operate according to m_r_mode 2 when the page queue utilization is >= this value, otherwise operate according to m_r_mode 1
        SubsecondTime m_r_mode_5_remote_access_history_window_size;  // When m_r_mode == 5, and operating according to m_r_mode, track page accesses using the most recent window size number of ns
        bool m_use_throttled_pages_tracker;  // Whether to update m_throttled_pages_tracker. Must be true to use the ideal page throttler or print stats of throttled pages
        bool m_use_ideal_page_throttling;  // Whether to use ideal page throttling
        SubsecondTime m_r_ideal_pagethrottle_remote_access_history_window_size;  // Track remote page accesses using the most recent window size number of ns
        bool m_track_page_bw_utilization_stats;
        bool m_speed_up_simulation;  // When this is true, some optional stats aren't calculated
        bool m_r_pq_cacheline_hw_no_queue_delay;  // When this is true, remove HW access queue delay from PQ=on cacheline requests' critical path to simulate prioritized cachelines
        bool m_track_inflight_cachelines;  // Whether to track simultaneous inflight cachelines (slows down simulation)
        bool m_auto_turn_off_partition_queues;
        double m_turn_off_pq_cacheline_queue_utilization_threshold;
        double m_cancel_pq_inflight_buffer_threshold;
        bool m_keep_space_in_cacheline_queue;

        // Local Memory
        QueueModel* m_dram_queue_model_single;
        std::vector<QueueModel*> m_queue_model;
        std::vector<QueueModel*> m_rank_avail;
        std::vector<QueueModel*> m_bank_group_avail;

        QueueModel* m_data_movement;        // Normally, this is the combined queue for pages and cachelines. When partitioned queues are enabled, this is the page queue
        QueueModel* m_data_movement_2;      // When partitioned queues are enabled, this is the cacheline queue

        struct BankInfo
        {
            IntPtr open_page;
            SubsecondTime t_avail;
        };
        std::vector<BankInfo> m_banks;

        // Remote memory
        QueueModel* m_r_dram_queue_model_single;
        std::vector<QueueModel*> m_r_queue_model;
        std::vector<QueueModel*> m_r_rank_avail;
        std::vector<QueueModel*> m_r_bank_group_avail;

        std::vector<BankInfo> m_r_banks;

        HashedLinkedList m_local_pages; // Pages of local memory
        std::unordered_map<UInt64, char> m_local_pages_remote_origin;  // Pages of local memory that were originally in remote; char type can be changed to int for tracking number of accesses
        // std::list<UInt64> m_remote_pages; // Pages of remote memory
        std::unordered_set<UInt64> m_remote_pages; // Pages of remote memory
        // std::list<UInt64> m_dirty_pages; // Dirty pages of local memory
        std::unordered_set<UInt64> m_dirty_pages; // Dirty pages of local memory
        std::map<UInt64, SubsecondTime> m_inflight_pages; // Inflight pages that are being transferred from remote memory to local memory
        std::map<UInt64, UInt32> m_inflight_redundant;    // Count the number of redundant moves that occur for each inflight page while it is being transferred
        std::unordered_set<UInt64> m_pages_cacheline_request_limit_exceeded;  // Remote/inflight pages with cacheline queues requests >= m_r_limit_redundant_moves
        std::map<UInt64, SubsecondTime> m_inflightevicted_pages; // Inflight pages that are being transferred from local memory to remote memory
        std::map<UInt64, SubsecondTime> m_inflight_pages_extra; // Inflight pages that are being transferred from remote memory to local memory, that exceed the limit from inflight buffer size or network bw (track arrival time while not counting it in the normal data structures)

        UInt64 m_inflight_page_delayed;
        SubsecondTime m_inflight_pages_delay_time;

        std::map<UInt64, UInt32> m_page_usage_map;  // track number of times each phys page is accessed
        const UInt32 m_page_usage_stats_num_points = 10;  // the number of percentiles (from above 0% to including 100%)
        std::vector<UInt64> page_usage_count_stats;       // percentiles of phys_page access counts, to be registered as stats
        std::map<UInt64, UInt32> m_remote_access_tracker;  // Track remote page accesses
        std::multimap<SubsecondTime, UInt64> m_recent_remote_accesses;  // Track remote page access that are recent

        std::map<UInt64, std::pair<SubsecondTime, UInt32>> m_throttled_pages_tracker;  // keep track of pages that were throttled. The value is a (time, count) pair of the last time the page was throttled and the number of times the page was requested within the same 10^6 ns
        std::vector<std::pair<UInt64, UInt32>> m_throttled_pages_tracker_values;       // values to keep track of for stats
        HashedLinkedList m_moved_pages_no_access_yet;                                  // Pages moved from remote to local, but haven't been accessed yet

        // Compression
        bool m_use_compression;
        bool m_use_cacheline_compression;
        bool m_use_r_compressed_pages;
        CompressionController m_compression_controller;

        // Prefetcher
        bool m_r_enable_nl_prefetcher;            // Enable prefetcher to prefetch pages from remote DRAM to local DRAM
        PrefetcherModel *m_prefetcher_model;
        bool m_prefetch_unencountered_pages;      // Whether to prefetch pages that haven't been encountered yet in program execution

        // Page spatial locality tracker
        UInt64 m_num_recent_remote_accesses;
        UInt64 m_num_recent_remote_additional_accesses;   // For cacheline queue requests made on inflight pages. Track this separately since they could be counted as either "remote" or "local" cacheline accesses
        UInt64 m_num_recent_local_accesses;
        // SubsecondTime m_recent_access_count_begin_time;
        std::unordered_set<UInt64> m_recent_accessed_pages;
        std::vector<double> m_page_locality_measures;
        std::vector<double> m_modified_page_locality_measures;
        std::vector<double> m_modified2_page_locality_measures;

        // Stats for when dynamically adjusting m_r_cacheline_queue_fraction
        UInt64 m_r_cacheline_queue_fraction_increased;
        UInt64 m_r_cacheline_queue_fraction_decreased;
        double m_min_r_cacheline_queue_fraction;
        double m_max_r_cacheline_queue_fraction;
        UInt64 m_min_r_cacheline_queue_fraction_stat_scaled;  // Min cl queue fraction * 10^4, saving double as an int for sim.out
        UInt64 m_max_r_cacheline_queue_fraction_stat_scaled;  // Max cl queue fraction * 10^4, saving double as an int for sim.out

        UInt64 m_num_accesses;                                // Total number of calls to getAccessLatency(), ie # cachelines requested

        // Variables to keep track of stats
        UInt64 m_dram_page_hits;
        UInt64 m_dram_page_empty;
        UInt64 m_dram_page_closing;
        UInt64 m_dram_page_misses;
        UInt64 m_local_reads_remote_origin;
        UInt64 m_local_writes_remote_origin;
        UInt64 m_remote_reads;
        UInt64 m_remote_writes;
        UInt64 m_page_moves;
        UInt64 m_page_prefetches;                                 // number of successful prefetches
        UInt64 m_prefetch_page_not_done_datamovement_queue_full;  // number of times a page prefetch candidate was not prefetched due to the queue for moving pages having full utilization
        UInt64 m_prefetch_page_not_done_page_local_already;       // number of times a page prefetch candidate was not prefetched due to the page already being in local memory
        UInt64 m_prefetch_page_not_done_page_not_initialized;     // number of times a page prefetch candidate was not prefetched due to the page not having been initialized already
        UInt64 m_inflight_hits;
        UInt64 m_writeback_pages;
        UInt64 m_local_evictions;
        UInt64 m_extra_pages;
        UInt64 m_extra_cachelines;
        UInt64 m_redundant_moves;                   // number of times both a cacheline and its containing page are requested together
        UInt64 m_redundant_moves_type1;
        UInt64 partition_queues_cacheline_slower_than_page;  // with the new change, these situations no longer result in redundant moves
        UInt64 m_redundant_moves_type2;
        UInt64 m_redundant_moves_type2_cancelled_already_inflight;  // cacheline queue (read) request cancelled because the cacheline is already inflight (only applicable when m_track_inflight_cachelines is true)
        UInt64 m_redundant_moves_type2_cancelled_datamovement_queue_full;
        UInt64 m_redundant_moves_type2_cancelled_limit_redundant_moves; // number of times a cacheline queue request is cancelled due to m_r_limit_redundant_moves
        UInt64 m_redundant_moves_type2_slower_than_page_arrival;  // these situations don't result in redundant moves
        UInt64 m_max_total_bufferspace;                        // the maximum number of localdram pages actually used to back inflight_pages and inflightevicted_pages pages 
        UInt64 m_max_inflight_bufferspace;                     // the maximum number of localdram pages actually used to back inflight pages in the m_inflight_pages map
        UInt64 m_max_inflight_extra_bufferspace;               // the maximum number of localdram pages in the inflight_extra map
        UInt64 m_max_inflightevicted_bufferspace;              // the maximum number of localdram pages actually used to back inflight evicted pages in the m_inflightevicted_pages map
        UInt64 m_move_page_cancelled_bufferspace_full;         // the number of times moving a remote page to local was cancelled due to localdram bufferspace being full
        UInt64 m_move_page_cancelled_datamovement_queue_full;  // the number of times moving a remote page to local was cancelled due to the network bandwidth queue for pages being full
        UInt64 m_move_page_cancelled_rmode5;                   // the number of times a remote page was not moved to local due to rmode5
        UInt64 m_bufferspace_full_page_still_moved;            // localdram bufferspace was full, but page was still moved with an additional estimated penalty (currently only when PQ=off)
        UInt64 m_datamovement_queue_full_page_still_moved;     // network bandwidth queue for pages was full, but page was still moved with an additional estimated penalty
        UInt64 m_datamovement_queue_full_cacheline_still_moved;// network bandwidth queue for cachelines was full, but cacheline was still moved with an additional estimated penalty (only when PQ=on)
        UInt64 m_rmode5_page_moved_due_to_threshold;           // the number of time when in rmode5 and acting according to rmode2, a page was moved because the threshold number of accesses was reached
        UInt64 m_unique_pages_accessed;             // track number of unique pages accessed
        UInt64 m_ideal_page_throttling_swaps_inflight;         // number of times the ideal page throttling algorithm swaps a throttled page with a previously moved page that was inflight
        UInt64 m_ideal_page_throttling_swaps_non_inflight;     // number of times the ideal page throttling algorithm swaps a throttled page with a previously moved page that was not inflight
        UInt64 m_ideal_page_throttling_swap_unavailable;       // number of times in the ideal page throttling algorithm a subsequent access to a throttled page could not be swapped with a previously moved page
        SubsecondTime m_redundant_moves_type1_time_savings;
        SubsecondTime m_redundant_moves_type2_time_savings;

        SubsecondTime m_total_queueing_delay;
        SubsecondTime m_total_access_latency;
        SubsecondTime m_total_local_access_latency;
        SubsecondTime m_total_remote_access_latency;
        SubsecondTime m_total_remote_datamovement_latency;
        
        SubsecondTime m_total_local_dram_hardware_latency;
        SubsecondTime m_total_remote_dram_hardware_latency_cachelines;
        SubsecondTime m_total_remote_dram_hardware_latency_pages;
        UInt64 m_total_local_dram_hardware_latency_count;
        UInt64 m_total_remote_dram_hardware_latency_cachelines_count;
        UInt64 m_total_remote_dram_hardware_latency_pages_count;
        SubsecondTime m_total_local_dram_hardware_write_latency_pages;
        // UInt64 m_local_get_dram_access_cost_called;
        // UInt64 m_remote_cacheline_get_dram_access_cost_called;
        // UInt64 m_remote_page_get_dram_access_cost_called;
        SubsecondTime m_local_get_dram_access_cost_processing_time;
        SubsecondTime m_local_get_dram_access_cost_queue_delay;
        SubsecondTime m_remote_cacheline_get_dram_access_cost_processing_time;
        SubsecondTime m_remote_cacheline_get_dram_access_cost_queue_delay;
        SubsecondTime m_remote_page_get_dram_access_cost_processing_time;
        SubsecondTime m_remote_page_get_dram_access_cost_queue_delay;
        SubsecondTime m_cacheline_network_processing_time;
        SubsecondTime m_cacheline_network_queue_delay;
        SubsecondTime m_page_network_processing_time;
        SubsecondTime m_page_network_queue_delay;
        UInt64 m_remote_to_local_cacheline_move_count;
        UInt64 m_remote_to_local_page_move_count;

        UInt64 m_global_time_much_larger_than_page_arrival;
        SubsecondTime m_sum_global_time_much_larger;

        UInt64 m_bw_utilization_decile_to_count[11];

        SubsecondTime m_local_total_remote_access_latency;
        UInt64 m_local_total_remote_access_latency_window_capacity = 100;
        UInt64 m_local_total_remote_access_latency_window_cur_size = 0;
        std::vector<SubsecondTime> m_local_total_remote_access_latency_avgs;

        // Dynamic BW and Latency
        long long int m_update_bandwidth_count = 0;
        long long int m_update_latency_count = 0;

        // For local IPC calculation
        UInt64 IPC_window_start_instr_count;
        UInt64 IPC_window_end_instr_count;
        UInt64 IPC_window_capacity;
        UInt64 IPC_window_cur_size = 0;
        std::vector<double> m_local_IPCs;
        std::vector<UInt64> m_instruction_count_x_axis;

        std::unordered_map<UInt64, UInt64> m_inflight_page_to_dirty_write_count;
        UInt64 m_dirty_write_buffer_size = 0;
        UInt64 m_sum_write_buffer_size = 0;
        UInt64 m_max_dirty_write_buffer_size = 0;

        std::map<UInt64, SubsecondTime> m_inflight_cachelines_reads;
        std::multimap<UInt64, SubsecondTime> m_inflight_cachelines_writes;  // possibility of mutliple writes to the same address
        UInt64 m_max_inflight_cachelines_reads;
        UInt64 m_max_inflight_cachelines_writes;
        UInt64 m_max_inflight_cachelines_total;
        UInt64 m_sum_inflight_cachelines_reads_size;
        UInt64 m_sum_inflight_cachelines_writes_size;
        UInt64 m_sum_inflight_cachelines_total_size;

        // BW utilization stats
        UInt64 m_cacheline_bw_utilization_sum = 0;
        UInt64 m_page_bw_utilization_sum = 0;
        UInt64 m_total_bw_utilization_sum = 0;

        // Handle dram access latency outliers
        SubsecondTime m_access_latency_outlier_threshold;
        SubsecondTime m_total_access_latency_no_outlier;
        UInt64 m_access_latency_outlier_count;

        SubsecondTime m_total_local_access_latency_no_outlier;
        UInt64 m_local_access_latency_outlier_count;

        SubsecondTime m_total_remote_access_latency_no_outlier;
        UInt64 m_remote_access_latency_outlier_count;

        UInt64 m_disturbance_bq_size;

        SubsecondTime getDramAccessCost(SubsecondTime start_time, UInt64 size, core_id_t requester, IntPtr address, ShmemPerf *perf, bool is_remote, bool is_exclude_cacheline, bool is_page);
        SubsecondTime getDramAccessCostSimple(SubsecondTime start_time, UInt64 size, core_id_t requester, IntPtr address, ShmemPerf *perf, bool is_remote, bool is_exclude_cacheline, bool is_page);
        SubsecondTime getDramAccessCostDetailed(SubsecondTime start_time, UInt64 size, core_id_t requester, IntPtr address, ShmemPerf *perf, bool is_remote, bool is_exclude_cacheline, bool is_page);
        SubsecondTime getDramWriteCost(SubsecondTime start_time, UInt64 size, core_id_t requester, IntPtr address, ShmemPerf *perf, bool is_exclude_cacheline, bool is_page);
        void parseDeviceAddress(IntPtr address, UInt32 &channel, UInt32 &rank, UInt32 &bank_group, UInt32 &bank, UInt32 &column, UInt64 &dram_page);
        UInt64 parseAddressBits(UInt64 address, UInt32 &data, UInt32 offset, UInt32 size, UInt64 base_address);
        SubsecondTime possiblyEvict(UInt64 phys_page, SubsecondTime pkt_time, core_id_t requester);
        void possiblyPrefetch(UInt64 phys_page, SubsecondTime pkt_time, core_id_t requester);

        // Helper to print vector percentiles, for stats output
        template<typename T>
        void sortAndPrintVectorPercentiles(std::vector<T>& vec, std::ostringstream& percentages_buffer, std::ostringstream& counts_buffer, UInt32 num_bins = 40);

        void update_bw_utilization_count(SubsecondTime pkt_time);

        void update_local_remote_latency_stat(SubsecondTime access_latency);

    public:
        DramPerfModelDisagg(core_id_t core_id, UInt32 cache_block_size, AddressHomeLookup* address_home_lookup);

        ~DramPerfModelDisagg();
        void finalizeStats();
        void updateBandwidth();
        void updateLatency();
        void updateLocalIPCStat(UInt64 instr_count);

        bool isRemoteAccess(IntPtr address, core_id_t requester, DramCntlrInterface::access_t access_type); 
        SubsecondTime getAccessLatencyRemote(SubsecondTime pkt_time, UInt64 pkt_size, core_id_t requester, IntPtr address, DramCntlrInterface::access_t access_type, ShmemPerf *perf);

        SubsecondTime getAccessLatency(SubsecondTime pkt_time, UInt64 pkt_size, core_id_t requester, IntPtr address, DramCntlrInterface::access_t access_type, ShmemPerf *perf);
};

#endif /* __DRAM_PERF_MODEL_DISAGG_H__ */
