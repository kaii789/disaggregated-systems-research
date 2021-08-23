#ifndef __DRAM_PERF_MODEL_DISAGG_H__
#define __DRAM_PERF_MODEL_DISAGG_H__

#include "dram_perf_model.h"
#include "queue_model.h"
#include "compression_model.h"
#include "prefetcher_model.h"
#include "fixed_types.h"
#include "subsecond_time.h"
#include "dram_cntlr_interface.h"

#include <vector>
#include <bitset>
#include <map>
#include <list>
#include <set>
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
        const ComponentBandwidth m_bus_bandwidth;
        ComponentBandwidth m_r_bus_bandwidth;   // Remote
        ComponentBandwidth m_r_part_bandwidth;  // Remote - Partitioned Queues => Page Queue
        ComponentBandwidth m_r_part2_bandwidth; // Remote - Partitioned Queues => Cacheline Queue
        double m_r_bw_scalefactor;              // Remote memory bandwidth is ddr bandwidth scaled down by m_r_bw_scalefactor
        bool m_use_dynamic_bandwidth;
        const SubsecondTime m_bank_keep_open;
        const SubsecondTime m_bank_open_delay;
        const SubsecondTime m_bank_close_delay;
        const SubsecondTime m_dram_access_cost;
        const SubsecondTime m_intercommand_delay;       // Rank availability
        const SubsecondTime m_intercommand_delay_short; // Rank availability
        const SubsecondTime m_intercommand_delay_long;  // Bank group availability
        const SubsecondTime m_controller_delay;         // Average pipeline delay for various DDR controller stages
        const SubsecondTime m_refresh_interval;         // tRFCI
        const SubsecondTime m_refresh_length;           // tRFC
        const SubsecondTime m_r_added_latency; // Additional remote latency
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
        const UInt32 m_r_disturbance_factor; // Other systems using the remote memory and creating disturbance
        const bool m_r_dontevictdirty; // Do not evict dirty data
        const bool m_r_enable_selective_moves; 
        const UInt32 m_r_partition_queues; // Enable partitioned queues
        double m_r_cacheline_queue_fraction; // The fraction of remote bandwidth used for the cacheline queue (decimal between 0 and 1) 
        bool m_use_dynamic_cl_queue_fraction_adjustment; // Whether to dynamically adjust m_r_cacheline_queue_fraction
        const bool m_r_cacheline_gran; // Move data and operate in cacheline granularity
        const UInt32 m_r_reserved_bufferspace; // Max % of local DRAM that can be reserved for pages in transit
        const UInt32 m_r_limit_redundant_moves; 
        const bool m_r_throttle_redundant_moves;
        const bool m_r_use_separate_queue_model;  // Whether to use the separate remote queue model
        double m_r_page_queue_utilization_threshold;  // When the datamovement queue for pages has percentage utilization above this, remote pages aren't moved to local
        double m_r_cacheline_queue_utilization_threshold;  // When the datamovement queue for cachelines has percentage utilization above this, cacheline requests on inflight pages aren't made
        double m_r_mode_5_limit_moves_threshold;  // When m_r_mode == 5, operate according to m_r_mode 2 when the page queue utilization is >= this value, otherwise operate according to m_r_mode 1
        SubsecondTime m_r_mode_5_remote_access_history_window_size;  // When m_r_mode == 5, and operating according to m_r_mode, track page accesses using the most recent window size number of ns
        bool m_use_throttled_pages_tracker;  // Whether to update m_throttled_pages_tracker. Must be true to use the ideal page throttler or print stats of throttled pages
        bool m_use_ideal_page_throttling;  // Whether to use ideal page throttling
        SubsecondTime m_r_ideal_pagethrottle_remote_access_history_window_size;  // Track remote page accesses using the most recent window size number of ns
        bool m_track_page_bw_utilization_stats;

        // Local Memory
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
        std::vector<QueueModel*> m_r_queue_model;
        std::vector<QueueModel*> m_r_rank_avail;
        std::vector<QueueModel*> m_r_bank_group_avail;

        std::vector<BankInfo> m_r_banks;

        std::list<UInt64> m_local_pages; // Pages of local memory
        std::map<UInt64, char> m_local_pages_remote_origin;  // Pages of local memory that were originally in remote
        std::list<UInt64> m_remote_pages; // Pages of remote memory
        std::list<UInt64> m_dirty_pages; // Dirty pages of local memory
        std::map<UInt64, SubsecondTime> m_inflight_pages; // Inflight pages that are being transferred from remote memory to local memory
        std::map<UInt64, UInt32> m_inflight_redundant;    // Count the number of redundant moves that occur for each inflight page while it is being transferred
        std::map<UInt64, SubsecondTime> m_inflightevicted_pages; // Inflight pages that are being transferred from local memory to remote memory

        UInt64 m_inflight_page_delayed;
        SubsecondTime m_inflight_pages_delay_time;

        std::map<UInt64, UInt32> m_page_usage_map;  // track number of times each phys page is accessed
        const UInt32 m_page_usage_stats_num_points = 10;  // the number of percentiles (from above 0% to including 100%)
        std::vector<UInt64> page_usage_count_stats;       // percentiles of phys_page access counts, to be registered as stats
        std::map<UInt64, UInt32> m_remote_access_tracker;  // Track remote page accesses
        std::multimap<SubsecondTime, UInt64> m_recent_remote_accesses;  // Track remote page access that are recent

        std::map<UInt64, std::pair<SubsecondTime, UInt32>> m_throttled_pages_tracker;  // keep track of pages that were throttled. The value is a (time, count) pair of the last time the page was throttled and the number of times the page was requested within the same 10^6 ns
        std::vector<std::pair<UInt64, UInt32>> m_throttled_pages_tracker_values;       // values to keep track of for stats
        std::list<UInt64> m_moved_pages_no_access_yet;                                 // Pages moved from remote to local, but haven't been accessed yet

        // TODO: Compression
        bool m_use_compression;
        CompressionModel *m_compression_model;
        UInt64 bytes_saved = 0;
        SubsecondTime m_total_compression_latency = SubsecondTime::Zero();
        SubsecondTime m_total_decompression_latency = SubsecondTime::Zero();
        std::map<IntPtr, UInt32> address_to_compressed_size;
        std::map<IntPtr, UInt32> address_to_num_cache_lines;

        bool m_use_cacheline_compression;
        CompressionModel *m_cacheline_compression_model;
        UInt64 cacheline_bytes_saved = 0;
        SubsecondTime m_total_cacheline_compression_latency = SubsecondTime::Zero();
        SubsecondTime m_total_cacheline_decompression_latency = SubsecondTime::Zero();

        // Prefetcher
        bool m_r_enable_nl_prefetcher;            // Enable prefetcher to prefetch pages from remote DRAM to local DRAM
        PrefetcherModel *m_prefetcher_model;
        bool m_prefetch_unencountered_pages;      // Whether to prefetch pages that haven't been encountered yet in program execution

        // Page spatial locality tracker
        UInt64 m_num_recent_remote_accesses;
        UInt64 m_num_recent_remote_additional_accesses;   // For cacheline queue requests made on inflight pages. Track this separately since they could be counted as either "remote" or "local" cacheline accesses
        UInt64 m_num_recent_local_accesses;
        // SubsecondTime m_recent_access_count_begin_time;
        std::set<UInt64> m_recent_accessed_pages;
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
        UInt64 m_redundant_moves;                   // number of times both a cacheline and its containing page are requested together
        UInt64 m_redundant_moves_type1;
        UInt64 partition_queues_cacheline_slower_than_page;  // with the new change, these situations no longer result in redundant moves
        UInt64 m_redundant_moves_type2;
        UInt64 m_redundant_moves_type2_cancelled_datamovement_queue_full;
        UInt64 m_redundant_moves_type2_cancelled_limit_redundant_moves; // number of times a cacheline queue request is cancelled due to m_r_limit_redundant_moves
        UInt64 m_redundant_moves_type2_slower_than_page_arrival;  // these situations don't result in redundant moves
        UInt64 m_max_bufferspace;                   // the maximum number of localdram pages actually used to back inflight and inflight_evicted pages 
        UInt64 m_move_page_cancelled_bufferspace_full;         // the number of times moving a remote page to local was cancelled due to localdram bufferspace being full
        UInt64 m_move_page_cancelled_datamovement_queue_full;  // the number of times moving a remote page to local was cancelled due to the queue for pages being full
        UInt64 m_move_page_cancelled_rmode5;                   // the number of times a remote page was not moved to local due to rmode5
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
        UInt64 m_global_time_much_larger_than_tnow;
        SubsecondTime m_sum_global_time_much_larger;

        UInt64 m_bw_utilization_decile_to_count[10];

        // Dynamic BW
        long long int m_update_bandwidth_count = 0;

        void parseDeviceAddress(IntPtr address, UInt32 &channel, UInt32 &rank, UInt32 &bank_group, UInt32 &bank, UInt32 &column, UInt64 &dram_page);
        UInt64 parseAddressBits(UInt64 address, UInt32 &data, UInt32 offset, UInt32 size, UInt64 base_address);
        SubsecondTime possiblyEvict(UInt64 phys_page, SubsecondTime pkt_time, core_id_t requester);
        void possiblyPrefetch(UInt64 phys_page, SubsecondTime pkt_time, core_id_t requester);

        // Helper to print vector percentiles, for stats output
        template<typename T>
        void sortAndPrintVectorPercentiles(std::vector<T>& vec, std::ostringstream& percentages_buffer, std::ostringstream& counts_buffer, UInt32 num_bins = 40);

        void update_bw_utilization_count(SubsecondTime pkt_time);

    public:
        DramPerfModelDisagg(core_id_t core_id, UInt32 cache_block_size, AddressHomeLookup* address_home_lookup);

        ~DramPerfModelDisagg();
        void finalizeStats();
        void updateBandwidth();

        bool isRemoteAccess(IntPtr address, core_id_t requester, DramCntlrInterface::access_t access_type); 
        SubsecondTime getAccessLatencyRemote(SubsecondTime pkt_time, UInt64 pkt_size, core_id_t requester, IntPtr address, DramCntlrInterface::access_t access_type, ShmemPerf *perf);

        SubsecondTime getAccessLatency(SubsecondTime pkt_time, UInt64 pkt_size, core_id_t requester, IntPtr address, DramCntlrInterface::access_t access_type, ShmemPerf *perf);
};

#endif /* __DRAM_PERF_MODEL_DISAGG_H__ */
