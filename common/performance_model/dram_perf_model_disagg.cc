#include "dram_perf_model_disagg.h"
#include "simulator.h"
#include "config.h"
#include "config.hpp"
#include "stats.h"
#include "shmem_perf.h"
#include "address_home_lookup.h"
#include "utils.h"
#include "print_utils.h"

#include <algorithm>

DramPerfModelDisagg::DramPerfModelDisagg(core_id_t core_id, UInt32 cache_block_size, AddressHomeLookup* address_home_lookup)
    : DramPerfModel(core_id, cache_block_size)
    , m_cache_line_size     (cache_block_size)
    , m_page_size           (Sim()->getCfg()->getInt("perf_model/dram/page_size"))  // Memory page size (bytes) in disagg.cc used for page movement (different from ddr page size)
    , m_enable_remote_mem       (Sim()->getCfg()->getBool("perf_model/dram/enable_remote_mem")) // Enable remote memory simulation
    , m_r_partition_queues  (Sim()->getCfg()->getInt("perf_model/dram/remote_partitioned_queues")) // Enable partitioned queues
    , m_dram_hardware_cntlr (DramHardwareCntlr(core_id, address_home_lookup, m_cache_line_size, m_page_size, m_r_partition_queues))
    , m_r_added_latency       (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/remote_mem_add_lat"))) // Network latency for remote DRAM access 
    , m_r_bw_scalefactor    (Sim()->getCfg()->getFloat("perf_model/dram/remote_mem_bw_scalefactor"))
    , m_r_cacheline_queue_fraction    (Sim()->getCfg()->getFloat("perf_model/dram/remote_cacheline_queue_fraction")) // The fraction of remote bandwidth used for the cacheline queue (decimal between 0 and 1)
    , m_use_dynamic_cl_queue_fraction_adjustment    (Sim()->getCfg()->getBool("perf_model/dram/use_dynamic_cacheline_queue_fraction_adjustment"))  // Whether to dynamically adjust m_r_cacheline_queue_fraction
    , m_base_bus_bandwidth  (Sim()->getCfg()->getInt("perf_model/dram/ddr/dram_speed") * Sim()->getCfg()->getInt("perf_model/dram/ddr/data_bus_width")) // in bits/us
    , m_r_bus_bandwidth     (m_base_bus_bandwidth / (1000 * m_r_bw_scalefactor)) // Remote memory
    , m_r_page_bandwidth    (m_base_bus_bandwidth / (1000 * m_r_bw_scalefactor / (1 - m_r_cacheline_queue_fraction))) // Remote memory - Partitioned Queues => Page Queue
    , m_r_cacheline_bandwidth   (m_base_bus_bandwidth / (1000 * m_r_bw_scalefactor / m_r_cacheline_queue_fraction)) // Remote memory - Partitioned Queues => Cacheline Queue
    , m_use_dynamic_bandwidth (Sim()->getCfg()->getBool("perf_model/dram/use_dynamic_bandwidth"))
    , m_use_dynamic_latency (Sim()->getCfg()->getBool("perf_model/dram/use_dynamic_latency"))
    , m_localdram_size       (Sim()->getCfg()->getInt("perf_model/dram/localdram_size")) // Local DRAM size
    , m_r_datamov_threshold       (Sim()->getCfg()->getInt("perf_model/dram/remote_datamov_threshold"))// Move data if greater than
    , m_r_simulate_tlb_overhead       (Sim()->getCfg()->getBool("perf_model/dram/simulate_tlb_overhead")) // Simulate TLB overhead
    , m_r_simulate_datamov_overhead       (Sim()->getCfg()->getBool("perf_model/dram/simulate_datamov_overhead"))  // Simulate datamovement overhead for remote DRAM (default: true)
    , m_r_mode       (Sim()->getCfg()->getInt("perf_model/dram/remote_memory_mode")) // Various modes for Local DRAM usage
    , m_r_partitioning_ratio       (Sim()->getCfg()->getInt("perf_model/dram/remote_partitioning_ratio"))// Move data if greater than
    , m_r_simulate_sw_pagereclaim_overhead       (Sim()->getCfg()->getBool("perf_model/dram/simulate_sw_pagereclaim_overhead"))// Add 2600usec delay
    , m_r_exclusive_cache       (Sim()->getCfg()->getBool("perf_model/dram/remote_exclusive_cache"))
    , m_remote_init       (Sim()->getCfg()->getBool("perf_model/dram/remote_init")) // If true, all pages are initially allocated to remote memory
    , m_r_disturbance_factor      (Sim()->getCfg()->getInt("perf_model/dram/remote_disturbance_factor")) // Other systems using the remote memory and creating disturbance
    , m_r_dontevictdirty      (Sim()->getCfg()->getBool("perf_model/dram/remote_dontevictdirty")) // Do not evict dirty pages
    , m_r_enable_selective_moves      (Sim()->getCfg()->getBool("perf_model/dram/remote_enable_selective_moves"))
    , m_r_cacheline_gran      (Sim()->getCfg()->getBool("perf_model/dram/remote_use_cacheline_granularity")) // Move data and operate in cacheline granularity
    , m_r_reserved_bufferspace      (Sim()->getCfg()->getFloat("perf_model/dram/remote_reserved_buffer_space")) // Max % of local DRAM that can be reserved for pages in transit
    , m_r_redundant_moves_limit      (Sim()->getCfg()->getInt("perf_model/dram/remote_limit_redundant_moves"))
    , m_r_throttle_redundant_moves      (Sim()->getCfg()->getBool("perf_model/dram/remote_throttle_redundant_moves"))
    , m_r_use_separate_queue_model      (Sim()->getCfg()->getBool("perf_model/dram/queue_model/use_separate_remote_queue_model")) // Whether to use the separate remote queue model
    , m_r_page_queue_utilization_threshold   (Sim()->getCfg()->getFloat("perf_model/dram/remote_page_queue_utilization_threshold")) // When the datamovement queue for pages has percentage utilization above this, remote pages aren't moved to local
    , m_r_cacheline_queue_type1_utilization_threshold   (Sim()->getCfg()->getFloat("perf_model/dram/remote_cacheline_queue_type1_utilization_threshold")) // When the datamovement queue for cachelines has percentage utilization above this, the first cacheline request on a remote page isn't made
    , m_r_cacheline_queue_type2_utilization_threshold   (Sim()->getCfg()->getFloat("perf_model/dram/remote_cacheline_queue_type2_utilization_threshold")) // When the datamovement queue for cachelines has percentage utilization above this, additional cacheline requests on inflight pages aren't made
    , m_use_throttled_pages_tracker    (Sim()->getCfg()->getBool("perf_model/dram/use_throttled_pages_tracker"))  // Whether to use and update m_use_throttled_pages_tracker
    , m_use_ideal_page_throttling    (Sim()->getCfg()->getBool("perf_model/dram/r_use_ideal_page_throttling"))  // Whether to use ideal page throttling (alternative currently is FCFS throttling)
    , m_r_ideal_pagethrottle_remote_access_history_window_size   (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/r_ideal_pagethrottle_access_history_window_size")))
    , m_speed_up_simulation    (Sim()->getCfg()->getBool("perf_model/dram/speed_up_disagg_simulation"))  // When this is true, some optional stats aren't calculated
    , m_track_inflight_cachelines    (Sim()->getCfg()->getBool("perf_model/dram/track_inflight_cachelines"))  // Whether to track simultaneous inflight cachelines (slows down simulation)
    , m_track_page_bw_utilization_stats    (Sim()->getCfg()->getBool("perf_model/dram/track_page_bw_utilization_stats"))  // Whether to track page queue bw utilization stats
    , m_auto_turn_off_partition_queues    (Sim()->getCfg()->getBool("perf_model/dram/auto_turn_off_partition_queues"))  // Whether to enable automatic detection of conditions to turn off partition queues
    , m_turn_off_pq_cacheline_queue_utilization_threshold    (Sim()->getCfg()->getFloat("perf_model/dram/turn_off_pq_cacheline_queue_utilization_threshold"))  // Only consider turning off partition queues when cacheline queue utilization is above this threshold
    , m_cancel_pq_inflight_buffer_threshold    (Sim()->getCfg()->getFloat("perf_model/dram/cancel_pq_inflight_buffer_threshold"))  // Fraction of inflight_pages size at which to cancel partition queues
    , m_keep_space_in_cacheline_queue     (Sim()->getCfg()->getBool("perf_model/dram/keep_space_in_cacheline_queue"))  // Try to keep more free bandwidth in cacheline queues
    , m_inflight_page_delayed(0)
    , m_inflight_pages_delay_time(SubsecondTime::Zero())
    , page_usage_count_stats(m_page_usage_stats_num_points, 0)
    , m_compression_controller(CompressionController(core_id, m_r_cacheline_gran, m_cache_line_size, m_page_size))
    , m_num_recent_remote_accesses(0)
    , m_num_recent_remote_additional_accesses(0)
    , m_num_recent_local_accesses(0)
    , m_r_cacheline_queue_fraction_increased(0)
    , m_r_cacheline_queue_fraction_decreased(0)
    , m_num_accesses(0)
    , m_local_reads_remote_origin(0)
    , m_local_writes_remote_origin(0)
    , m_remote_reads        (0)
    , m_remote_writes       (0)
    , m_page_moves          (0)
    , m_page_prefetches     (0)
    , m_prefetch_page_not_done_datamovement_queue_full(0)
    , m_prefetch_page_not_done_page_local_already(0)
    , m_prefetch_page_not_done_page_not_initialized(0)
    , m_inflight_hits       (0)
    , m_writeback_pages     (0)
    , m_local_evictions     (0)
    , m_extra_pages         (0)
    , m_extra_cachelines    (0)
    , m_redundant_moves     (0)
    , m_redundant_moves_type1  (0)
    , partition_queues_cacheline_slower_than_page (0)  // These situations don't result in redundant moves
    , m_redundant_moves_type2  (0)
    , m_redundant_moves_type2_cancelled_already_inflight(0)
    , m_redundant_moves_type2_cancelled_datamovement_queue_full(0)
    , m_redundant_moves_type2_cancelled_limit_redundant_moves(0)
    , m_redundant_moves_type2_slower_than_page_arrival(0)
    , m_max_total_bufferspace(0)
    , m_max_inflight_bufferspace(0)
    , m_max_inflight_extra_bufferspace(0)
    , m_max_inflightevicted_bufferspace(0)
    , m_move_page_cancelled_bufferspace_full(0)
    , m_move_page_cancelled_datamovement_queue_full(0)
    , m_move_page_cancelled_rmode5(0)
    , m_bufferspace_full_page_still_moved(0)
    , m_datamovement_queue_full_page_still_moved(0)
    , m_datamovement_queue_full_cacheline_still_moved(0)
    , m_rmode5_page_moved_due_to_threshold(0)
    , m_unique_pages_accessed      (0)
    , m_ideal_page_throttling_swaps_inflight(0)
    , m_ideal_page_throttling_swaps_non_inflight(0)
    , m_ideal_page_throttling_swap_unavailable(0)
    , m_redundant_moves_type1_time_savings(SubsecondTime::Zero())
    , m_redundant_moves_type2_time_savings(SubsecondTime::Zero())
    , m_total_queueing_delay(SubsecondTime::Zero())
    , m_total_access_latency(SubsecondTime::Zero())
    , m_total_local_access_latency(SubsecondTime::Zero())
    , m_total_remote_access_latency(SubsecondTime::Zero())
    , m_total_remote_datamovement_latency(SubsecondTime::Zero())
    , m_total_local_dram_hardware_latency(SubsecondTime::Zero())
    , m_total_remote_dram_hardware_latency_cachelines(SubsecondTime::Zero())
    , m_total_remote_dram_hardware_latency_pages(SubsecondTime::Zero())
    , m_total_local_dram_hardware_latency_count(0)
    , m_total_remote_dram_hardware_latency_cachelines_count(0)
    , m_total_remote_dram_hardware_latency_pages_count(0)
    , m_total_local_dram_hardware_write_latency_pages(SubsecondTime::Zero())
    , m_cacheline_network_processing_time(SubsecondTime::Zero())
    , m_cacheline_network_queue_delay(SubsecondTime::Zero())
    , m_page_network_processing_time(SubsecondTime::Zero())
    , m_page_network_queue_delay(SubsecondTime::Zero())
    , m_remote_to_local_cacheline_move_count(0)
    , m_remote_to_local_page_move_count(0)
    , m_global_time_much_larger_than_page_arrival(0)
    , m_sum_global_time_much_larger(SubsecondTime::Zero())
    , m_local_total_remote_access_latency(SubsecondTime::Zero())
    , m_ipc_window_capacity(Sim()->getCfg()->getInt("perf_model/dram/IPC_window_capacity"))
    , m_max_inflight_cachelines_reads(0)
    , m_max_inflight_cachelines_writes(0)
    , m_max_inflight_cachelines_total(0)
    , m_sum_inflight_cachelines_reads_size(0)
    , m_sum_inflight_cachelines_writes_size(0)
    , m_sum_inflight_cachelines_total_size(0)
    , m_access_latency_outlier_threshold(SubsecondTime::NS() * 20000)
    , m_total_access_latency_no_outlier(SubsecondTime::Zero())
    , m_access_latency_outlier_count(0)
    , m_total_local_access_latency_no_outlier(SubsecondTime::Zero())
    , m_local_access_latency_outlier_count(0)
    , m_total_remote_access_latency_no_outlier(SubsecondTime::Zero())
    , m_remote_access_latency_outlier_count(0)
    , m_disturbance_bq_size(Sim()->getCfg()->getInt("perf_model/dram/disturbance_bq_size"))
{
    String name("dram"); 

    String data_movement_queue_model_type = Sim()->getCfg()->getString("perf_model/dram/queue_model/type");
    if (m_r_use_separate_queue_model) {
        data_movement_queue_model_type = Sim()->getCfg()->getString("perf_model/dram/queue_model/remote_queue_model_type");
    }
    if (m_r_partition_queues == 2) {
        // Hardcode the queue model type for now
        m_data_movement = QueueModel::create(
                name + "-datamovement-queue", core_id, "windowed_mg1_remote_ind_queues_enhanced",
                m_r_bus_bandwidth.getRoundedLatency(8), m_r_bus_bandwidth.getBandwidthBitsPerUs(),
                m_r_bus_bandwidth.getRoundedLatency(8*m_page_size), m_r_bus_bandwidth.getRoundedLatency(8*m_cache_line_size));  // bytes to bits
    } else if (m_r_partition_queues == 3) {
        // Hardcode the queue model type for now
        m_data_movement = QueueModel::create(
                name + "-datamovement-queue", core_id, "windowed_mg1_remote_subqueuemodels",
                m_r_bus_bandwidth.getRoundedLatency(8), m_r_bus_bandwidth.getBandwidthBitsPerUs());  // bytes to bits
    } else if (m_r_partition_queues == 4) {
        // Hardcode the queue model type for now
        m_data_movement = QueueModel::create(
                name + "-datamovement-queue", core_id, "windowed_mg1_remote_ind_queues",
                m_r_bus_bandwidth.getRoundedLatency(8), m_r_bus_bandwidth.getBandwidthBitsPerUs());  // bytes to bits
    } else {
        m_data_movement = QueueModel::create(
                name + "-datamovement-queue", core_id, data_movement_queue_model_type,
                m_r_bus_bandwidth.getRoundedLatency(8), m_r_bus_bandwidth.getBandwidthBitsPerUs());  // bytes to bits
    }

    // r_mode 5
    if (m_r_mode == 5) {
        m_r_mode_5_limit_moves_threshold = Sim()->getCfg()->getFloat("perf_model/dram/r_mode_5_page_queue_utilization_mode_switch_threshold");
        m_r_mode_5_remote_access_history_window_size = SubsecondTime::NS(Sim()->getCfg()->getInt("perf_model/dram/r_mode_5_remote_access_history_window_size"));
        registerStatsMetric("dram", core_id, "rmode5-move-page-cancelled", &m_move_page_cancelled_rmode5);
        registerStatsMetric("dram", core_id, "rmode5-page-moved-due-to-threshold", &m_rmode5_page_moved_due_to_threshold);
    }

    // Compression
    m_use_compression = Sim()->getCfg()->getBool("perf_model/dram/compression_model/use_compression");
    m_use_cacheline_compression = Sim()->getCfg()->getBool("perf_model/dram/compression_model/cacheline/use_cacheline_compression");
    m_use_r_compressed_pages = Sim()->getCfg()->getBool("perf_model/dram/compression_model/use_r_compressed_pages");

    // Prefetcher
    m_r_enable_nl_prefetcher = Sim()->getCfg()->getBool("perf_model/dram/enable_remote_prefetcher");  // Enable prefetcher to prefetch pages from remote DRAM to local DRAM
    if (m_r_enable_nl_prefetcher) {
        m_prefetch_unencountered_pages = Sim()->getCfg()->getBool("perf_model/dram/prefetcher_model/prefetch_unencountered_pages");
        // When using m_r_cacheline_gran, the prefetcher operates by prefetching cachelines too
        UInt32 prefetch_granularity = m_r_cacheline_gran ? m_cache_line_size : m_page_size;

        // Type of prefetcher checked in PrefetcherModel, additional configs for specific prefetcher types are read there
        m_prefetcher_model = PrefetcherModel::createPrefetcherModel(prefetch_granularity);
    }

    LOG_ASSERT_ERROR(cache_block_size == 64, "Hardcoded for 64-byte cache lines");
    // Probably m_page_size needs to be < or <= 2^32 bytes
    LOG_ASSERT_ERROR(m_page_size > 0 && isPower2(m_page_size) && floorLog2(m_page_size) >= floorLog2(m_cache_line_size), "page_size must be a positive power of 2 (and page_size must be larger than the cacheline size)");

    registerStatsMetric("dram", core_id, "total-access-latency", &m_total_access_latency);
    registerStatsMetric("dram", core_id, "total-local-access-latency", &m_total_local_access_latency);
    registerStatsMetric("dram", core_id, "total-local-dram-hardware-latency", &m_total_local_dram_hardware_latency);
    registerStatsMetric("dram", core_id, "total-local-dram-hardware-latency-count", &m_total_local_dram_hardware_latency_count);
    registerStatsMetric("dram", core_id, "total-remote-access-latency", &m_total_remote_access_latency);
    registerStatsMetric("dram", core_id, "total-remote-dram-hardware-latency-cachelines", &m_total_remote_dram_hardware_latency_cachelines);
    registerStatsMetric("dram", core_id, "total-remote-dram-hardware-latency-pages", &m_total_remote_dram_hardware_latency_pages);
    registerStatsMetric("dram", core_id, "total-remote-dram-hardware-latency-cachelines-count", &m_total_remote_dram_hardware_latency_cachelines_count);
    registerStatsMetric("dram", core_id, "total-remote-dram-hardware-latency-pages-count", &m_total_remote_dram_hardware_latency_pages_count);
    
    registerStatsMetric("dram", core_id, "total-local-dram-hardware-write-latency-pages", &m_total_local_dram_hardware_write_latency_pages);
    
    registerStatsMetric("dram", core_id, "total-remote-datamovement-latency", &m_total_remote_datamovement_latency);
    registerStatsMetric("dram", core_id, "total-network-cacheline-processing-time", &m_cacheline_network_processing_time);
    registerStatsMetric("dram", core_id, "total-network-cacheline-queue-delay", &m_cacheline_network_queue_delay);
    registerStatsMetric("dram", core_id, "total-remote-to-local-cacheline-move-count", &m_remote_to_local_cacheline_move_count);
    registerStatsMetric("dram", core_id, "total-network-page-processing-time", &m_page_network_processing_time);
    registerStatsMetric("dram", core_id, "total-network-page-queue-delay", &m_page_network_queue_delay);
    registerStatsMetric("dram", core_id, "total-remote-to-local-page-move-count", &m_remote_to_local_page_move_count);
    
    // registerStatsMetric("dram", core_id, "local-reads-remote-origin", &m_local_reads_remote_origin);
    // registerStatsMetric("dram", core_id, "local-writes-remote-origin", &m_local_writes_remote_origin);
    registerStatsMetric("dram", core_id, "remote-reads", &m_remote_reads);
    registerStatsMetric("dram", core_id, "remote-writes", &m_remote_writes);
    registerStatsMetric("dram", core_id, "page-moves", &m_page_moves);
    registerStatsMetric("dram", core_id, "bufferspace-full-move-page-cancelled", &m_move_page_cancelled_bufferspace_full);
    registerStatsMetric("dram", core_id, "queue-full-move-page-cancelled", &m_move_page_cancelled_datamovement_queue_full);
    registerStatsMetric("dram", core_id, "bufferspace-full-page-still-moved", &m_bufferspace_full_page_still_moved);
    registerStatsMetric("dram", core_id, "queue-full-page-still-moved", &m_datamovement_queue_full_page_still_moved);    
    registerStatsMetric("dram", core_id, "queue-full-cacheline-still-moved", &m_datamovement_queue_full_cacheline_still_moved);    
    registerStatsMetric("dram", core_id, "inflight-hits", &m_inflight_hits);
    registerStatsMetric("dram", core_id, "writeback-pages", &m_writeback_pages);
    registerStatsMetric("dram", core_id, "local-evictions", &m_local_evictions);
    registerStatsMetric("dram", core_id, "extra-pages", &m_extra_pages);
    registerStatsMetric("dram", core_id, "extra-cachelines", &m_extra_cachelines);
    registerStatsMetric("dram", core_id, "redundant-moves", &m_redundant_moves);
    registerStatsMetric("dram", core_id, "max-simultaneous-inflight-cachelines-reads", &m_max_inflight_cachelines_reads);
    registerStatsMetric("dram", core_id, "max-simultaneous-inflight-cachelines-writes", &m_max_inflight_cachelines_writes);
    registerStatsMetric("dram", core_id, "max-simultaneous-inflight-cachelines-total", &m_max_inflight_cachelines_total);
    registerStatsMetric("dram", core_id, "sum-simultaneous-inflight-cachelines-reads", &m_sum_inflight_cachelines_reads_size);
    registerStatsMetric("dram", core_id, "sum-simultaneous-inflight-cachelines-writes", &m_sum_inflight_cachelines_writes_size);
    registerStatsMetric("dram", core_id, "sum-simultaneous-inflight-cachelines-total", &m_sum_inflight_cachelines_total_size);
    registerStatsMetric("dram", core_id, "max-total-bufferspace", &m_max_total_bufferspace);
    registerStatsMetric("dram", core_id, "max-inflight-bufferspace", &m_max_inflight_bufferspace);
    registerStatsMetric("dram", core_id, "max-inflight-extra-bufferspace", &m_max_inflight_extra_bufferspace);
    registerStatsMetric("dram", core_id, "max-inflightevicted-bufferspace", &m_max_inflightevicted_bufferspace);
    registerStatsMetric("dram", core_id, "page-prefetches", &m_page_prefetches);
    registerStatsMetric("dram", core_id, "queue-full-page-prefetch-not-done", &m_prefetch_page_not_done_datamovement_queue_full);
    registerStatsMetric("dram", core_id, "page-local-already-page-prefetch-not-done", &m_prefetch_page_not_done_page_local_already);
    registerStatsMetric("dram", core_id, "page-not-initialized-page-prefetch-not-done", &m_prefetch_page_not_done_page_not_initialized);
    registerStatsMetric("dram", core_id, "unique-pages-accessed", &m_unique_pages_accessed);     
    registerStatsMetric("dram", core_id, "inflight-page-delayed", &m_inflight_page_delayed);
    registerStatsMetric("dram", core_id, "inflight-page-total-delay-time", &m_inflight_pages_delay_time);

    registerStatsMetric("dram", core_id, "page-movement-num-global-time-much-larger", &m_global_time_much_larger_than_page_arrival);
    registerStatsMetric("dram", core_id, "page-movement-global-time-much-larger-total-time", &m_sum_global_time_much_larger);

    registerStatsMetric("dram", core_id, "local-dram-sum-dirty-write-buffer-size", &m_sum_write_buffer_size);
    registerStatsMetric("dram", core_id, "local-dram-max-dirty-write-buffer-size", &m_max_dirty_write_buffer_size);

    registerStatsMetric("dram", core_id, "cacheline-bw-utilization-sum", &m_cacheline_bw_utilization_sum);
    registerStatsMetric("dram", core_id, "page-bw-utilization-sum", &m_page_bw_utilization_sum);
    registerStatsMetric("dram", core_id, "total-bw-utilization-sum", &m_total_bw_utilization_sum);

    registerStatsMetric("dram", core_id, "total-access-latency-no-outlier", &m_total_access_latency_no_outlier);
    registerStatsMetric("dram", core_id, "access-latency-outlier-count", &m_access_latency_outlier_count);
    registerStatsMetric("dram", core_id, "total-remote-access-latency-no-outlier", &m_total_remote_access_latency_no_outlier);
    registerStatsMetric("dram", core_id, "remote-access-latency-outlier-count", &m_remote_access_latency_outlier_count);
    registerStatsMetric("dram", core_id, "total-local-access-latency-no-outlier", &m_total_local_access_latency_no_outlier);
    registerStatsMetric("dram", core_id, "local-access-latency-outlier-count", &m_local_access_latency_outlier_count);

    // Stats for partition_queues experiments
    if (m_r_partition_queues) {
        registerStatsMetric("dram", core_id, "redundant-moves-type1", &m_redundant_moves_type1);
        registerStatsMetric("dram", core_id, "pq-cacheline-slower-than-page", &partition_queues_cacheline_slower_than_page);
        registerStatsMetric("dram", core_id, "redundant-moves-type2", &m_redundant_moves_type2);
        registerStatsMetric("dram", core_id, "already-inflight-redundant-moves-type2-cancelled", &m_redundant_moves_type2_cancelled_already_inflight);
        registerStatsMetric("dram", core_id, "queue-full-redundant-moves-type2-cancelled", &m_redundant_moves_type2_cancelled_datamovement_queue_full);
        registerStatsMetric("dram", core_id, "limit-redundant-moves-redundant-moves-type2-cancelled", &m_redundant_moves_type2_cancelled_limit_redundant_moves);
        registerStatsMetric("dram", core_id, "cacheline-slower-than-inflight-page-arrival", &m_redundant_moves_type2_slower_than_page_arrival);
        registerStatsMetric("dram", core_id, "redundant-moves-type1-time-savings", &m_redundant_moves_type1_time_savings);
        registerStatsMetric("dram", core_id, "redundant-moves-type2-time-savings", &m_redundant_moves_type2_time_savings);

        if (m_use_dynamic_cl_queue_fraction_adjustment) {
            m_min_r_cacheline_queue_fraction = m_r_cacheline_queue_fraction;
            m_max_r_cacheline_queue_fraction = m_r_cacheline_queue_fraction;
            m_min_r_cacheline_queue_fraction_stat_scaled = (UInt64)(m_min_r_cacheline_queue_fraction * 10000);
            m_max_r_cacheline_queue_fraction_stat_scaled = (UInt64)(m_max_r_cacheline_queue_fraction * 10000);
            registerStatsMetric("dram", core_id, "min-runtime-cl-queue-fraction", &m_min_r_cacheline_queue_fraction_stat_scaled);
            registerStatsMetric("dram", core_id, "max-runtime-cl-queue-fraction", &m_max_r_cacheline_queue_fraction_stat_scaled);
            registerStatsMetric("dram", core_id, "num-cl-queue-fraction-increased", &m_r_cacheline_queue_fraction_increased);
            registerStatsMetric("dram", core_id, "num-cl-queue-fraction-decreased", &m_r_cacheline_queue_fraction_decreased);
        }
    }

    // Stats for ideal page throttling algorithm
    if (m_use_ideal_page_throttling) {
        registerStatsMetric("dram", core_id, "ideal-page-throttling-num-swaps-inflight", &m_ideal_page_throttling_swaps_inflight);
        registerStatsMetric("dram", core_id, "ideal-page-throttling-num-swaps-non-inflight", &m_ideal_page_throttling_swaps_non_inflight);
        registerStatsMetric("dram", core_id, "ideal-page-throttling-num-swap-unavailable", &m_ideal_page_throttling_swap_unavailable);
    }
    // Register stats for page locality
    for (UInt32 i = 0; i < m_page_usage_stats_num_points - 1; ++i) {
        UInt32 percentile = (UInt32)(100.0 / m_page_usage_stats_num_points) * (i + 1);
        String stat_name = "page-access-count-p";
        stat_name += std::to_string(percentile).c_str();
        registerStatsMetric("dram", core_id, stat_name, &(page_usage_count_stats[i]));
    }
    // Make sure last one is p100
    registerStatsMetric("dram", core_id, "page-access-count-p100", &(page_usage_count_stats[m_page_usage_stats_num_points - 1]));

    if (m_track_page_bw_utilization_stats) {
        // Stats for BW utilization
        for (int i = 0; i < 10; i++) {
            m_bw_utilization_decile_to_count[i] = 0;
            registerStatsMetric("dram", core_id, ("bw-utilization-decile-" + std::to_string(i)).c_str(), &m_bw_utilization_decile_to_count[i]);
        }
    }

    // RNG
    srand(time(NULL));
    
    // For debugging
    if (m_r_partition_queues)
        std::cout << "Initial m_r_cacheline_queue_fraction=" << m_r_cacheline_queue_fraction << std::endl;
}

DramPerfModelDisagg::~DramPerfModelDisagg()
{
    bool print_extra_stats = Sim()->getCfg()->getBool("perf_model/dram/print_extra_stats");
    if (print_extra_stats) {
        // TODO: temporarily disabled for now
        // // Remote Avg Latency Stats
        // std::cout << "\nAvg Remote DRAM Access Latencies:\n";
        // for (std::vector<SubsecondTime>::iterator it = m_local_total_remote_access_latency_avgs.begin(); it != m_local_total_remote_access_latency_avgs.end(); ++it) {
        //     UInt64 local_remote_access_latency_avg = it->getNS();
        //     std::cout << local_remote_access_latency_avg << ' ';
        // }
        // std::cout << "\n\n";

        // Local IPC Stats
        std::cout << "\nLocal IPC:\n";
        for (std::vector<double>::iterator it = m_local_ipcs.begin(); it != m_local_ipcs.end(); ++it) {
            double local_ipc = *it;
            std::cout << local_ipc << ' ';
        }
        std::cout << "\n\n";

        // Instruction Count X Axis
        std::cout << "\nInstruction Count X Axis:\n";
        for (std::vector<UInt64>::iterator it = m_instruction_count_x_axis.begin(); it != m_instruction_count_x_axis.end(); ++it) {
            UInt64 instruction_count = *it;
            std::cout << instruction_count << ' ';
        }
        std::cout << "\n\n";
    }

    delete m_data_movement;

    if (m_r_partition_queues && m_use_dynamic_cl_queue_fraction_adjustment) {
        std::cout << "Final m_r_cacheline_queue_fraction=" << m_r_cacheline_queue_fraction << std::endl;
        std::cout << "Final m_r_cacheline_queue_fraction_increased=" << m_r_cacheline_queue_fraction_increased << ", Final m_r_cacheline_queue_fraction_decreased=" << m_r_cacheline_queue_fraction_decreased << std::endl;
        std::cout << "Final m_min_r_cacheline_queue_fraction_stat_scaled=" << m_min_r_cacheline_queue_fraction_stat_scaled << ", Final m_max_r_cacheline_queue_fraction_stat_scaled=" << m_max_r_cacheline_queue_fraction_stat_scaled << std::endl;
    }
}

void
DramPerfModelDisagg::finalizeStats() 
{
    bool process_and_print_page_locality_stats = true;
    bool process_and_print_throttled_pages_stats = true;
    if (m_speed_up_simulation) {
        process_and_print_page_locality_stats = false;
        process_and_print_throttled_pages_stats = false;
    }

    // Finalize queue model stats
    m_data_movement->finalizeStats();

    std::cout << "dram_perf_model_disagg.cc finalizeStats():" << std::endl;
    if (m_page_locality_measures.size() > 0) {
        std::cout << "True page locality measure:" << std::endl;
        std::ostringstream percentages_buf, counts_buf;
        sortAndPrintVectorPercentiles(m_page_locality_measures, percentages_buf, counts_buf);
        std::cout << "CDF X values (true page locality):\n" << counts_buf.str() << std::endl;
        std::cout << "CDF Y values (probability):\n" << percentages_buf.str() << std::endl;
    }
    if (m_modified_page_locality_measures.size() > 0) {
        std::cout << "Modified page locality measure:" << std::endl;
        std::ostringstream percentages_buf, counts_buf;
        sortAndPrintVectorPercentiles(m_modified_page_locality_measures, percentages_buf, counts_buf);
        std::cout << "CDF X values (modified page locality):\n" << counts_buf.str() << std::endl;
        std::cout << "CDF Y values (probability):\n" << percentages_buf.str() << std::endl;
    }
    if (m_modified2_page_locality_measures.size() > 0) {
        std::cout << "Modified2 page locality measure:" << std::endl;
        std::ostringstream percentages_buf, counts_buf;
        sortAndPrintVectorPercentiles(m_modified2_page_locality_measures, percentages_buf, counts_buf);
        std::cout << "CDF X values (modified2 page locality):\n" << counts_buf.str() << std::endl;
        std::cout << "CDF Y values (probability):\n" << percentages_buf.str() << std::endl;
    }

    if (process_and_print_page_locality_stats && m_page_usage_map.size() > 0) {
        // Put values in a vector and sort
        std::vector<std::pair<UInt32, UInt64>> page_usage_counts;  // first is access count, second is the phys_page
        for (auto it = m_page_usage_map.begin(); it != m_page_usage_map.end(); ++it) {
            page_usage_counts.push_back(std::pair<UInt32, UInt64>(it->second, it->first));
        }
        // TODO: the following sort and printing could be extracted in another sortAndPrintVectorPercentiles() function
        std::sort(page_usage_counts.begin(), page_usage_counts.end());  // sort by access count

        // Update stats vector
        for (UInt32 i = 0; i < m_page_usage_stats_num_points - 1; ++i) {
            UInt64 index = (UInt64)((double)(i + 1) / m_page_usage_stats_num_points * (page_usage_counts.size() - 1));
            page_usage_count_stats[i] = page_usage_counts[index].first;
        }
        // Make sure last one is p100
        page_usage_count_stats[m_page_usage_stats_num_points - 1] = page_usage_counts[page_usage_counts.size() - 1].first;

        // Compute individual_counts percentiles for output
        UInt64 index;
        UInt32 percentile;
        double percentage;
        std::cout << "dram_perf_model_disagg.cc:" << std::endl;
        std::cout << "Page usage counts:" << std::endl;
        UInt32 num_bins = 40;  // the total number of points is 1 more than num_bins, since it includes the endpoints
        std::map<double, UInt32> usage_counts_percentiles;
        for (UInt32 bin = 0; bin < num_bins; ++bin) {
            percentage = (double)bin / num_bins;
            index = (UInt64)(percentage * (page_usage_counts.size() - 1));  // -1 so array indices don't go out of bounds
            percentile = page_usage_counts[index].first;
            std::cout << "percentage: " << percentage << ", vector index: " << index << ", percentile: " << percentile << std::endl;
            usage_counts_percentiles.insert(std::pair<double, UInt32>(percentage, percentile));
        }
        // Add the maximum
        percentage = 1.0;
        percentile = page_usage_counts[page_usage_counts.size() - 1].first;
        std::cout << "percentage: " << percentage << ", vector index: " << page_usage_counts.size() - 1 << ", percentile: " << percentile << std::endl;
        usage_counts_percentiles.insert(std::pair<double, UInt32>(percentage, percentile));
        // Print output in format that can easily be graphed in Python
        std::ostringstream percentages_buffer;
        std::ostringstream cdf_buffer_usage_counts;
        percentages_buffer << "[";
        cdf_buffer_usage_counts << "[";
        for (std::map<double, UInt32>::iterator it = usage_counts_percentiles.begin(); it != usage_counts_percentiles.end(); ++it) {
            percentages_buffer << it->first << ", ";
            cdf_buffer_usage_counts << it->second << ", ";
        }
        percentages_buffer << "]";
        cdf_buffer_usage_counts << "]";

        std::cout << "CDF X values (page usage counts):\n" << cdf_buffer_usage_counts.str() << std::endl;
        std::cout << "CDF Y values (probability):\n" << percentages_buffer.str() << std::endl;

        // // Print the least accessed 1/3 of phys_pages
        // std::ostringstream least_accessed_phys_pages_buffer;
        // least_accessed_phys_pages_buffer << "{ ";
        // std::vector<std::pair<UInt32, UInt64>>::iterator it = page_usage_counts.begin();
        // for (UInt64 i = 0; i < page_usage_counts.size() / 3; ++i) {
        //     least_accessed_phys_pages_buffer << it->second << ", ";
        //     ++it;
        // }
        // least_accessed_phys_pages_buffer << " }";
        // std::cout << "Least accessed phys_pages:\n" << least_accessed_phys_pages_buffer.str() << std::endl;

    }
    if (process_and_print_throttled_pages_stats && m_use_throttled_pages_tracker) {
        // Add values in the map at the end of program execution to m_throttled_pages_tracker_values
        for (std::map<UInt64, std::pair<SubsecondTime, UInt32>>::iterator it = m_throttled_pages_tracker.begin(); it != m_throttled_pages_tracker.end(); ++it) {
            m_throttled_pages_tracker_values.push_back(std::pair<UInt64, UInt32>(it->first, (it->second).second));
        }
        if (m_throttled_pages_tracker_values.size() < 1) {
            return;
        }

        // Build vectors of the stats we want
        std::vector<UInt32> throttled_pages_tracker_individual_counts;  // counts for the same phys_page are separate values
        std::map<UInt64, UInt32> throttled_pages_tracker_page_aggregated_counts_map;  // temporary variable
        std::vector<UInt32> throttled_pages_tracker_page_aggregated_counts;  // aggregate all numbers for a particular phys_page together
        for (std::vector<std::pair<UInt64, UInt32>>::iterator it = m_throttled_pages_tracker_values.begin(); it != m_throttled_pages_tracker_values.end(); ++it) {
            UInt64 phys_page = it->first;
            UInt32 count = it->second;

            throttled_pages_tracker_individual_counts.push_back(count);  // update individual counts

            if (!throttled_pages_tracker_page_aggregated_counts_map.count(phys_page)) {  // update aggregated counts map
                throttled_pages_tracker_page_aggregated_counts_map[phys_page] = 0;
            }
            throttled_pages_tracker_page_aggregated_counts_map[phys_page] += count;
        }
        // Generate aggregated counts vector
        for (std::map<UInt64, UInt32>::iterator it = throttled_pages_tracker_page_aggregated_counts_map.begin(); it != throttled_pages_tracker_page_aggregated_counts_map.end(); ++it) {
            throttled_pages_tracker_page_aggregated_counts.push_back(it->second);
        }
        
        // Compute individual_counts percentiles for output
        std::cout << "Throttled pages tracker individual counts:" << std::endl;
        std::ostringstream percentages_buf, individual_counts_buf;
        sortAndPrintVectorPercentiles(throttled_pages_tracker_individual_counts, percentages_buf, individual_counts_buf);
        std::cout << "CDF X values (throttled page accesses within time frame):\n" << individual_counts_buf.str() << std::endl;
        std::cout << "CDF Y values (probability):\n" << percentages_buf.str() << std::endl;

        // Compute aggregated_counts percentiles for output
        std::cout << "Throttled pages tracker page aggregated counts:" << std::endl;
        std::ostringstream percentages_buf_2, aggregated_counts_buf;
        sortAndPrintVectorPercentiles(throttled_pages_tracker_page_aggregated_counts, percentages_buf_2, aggregated_counts_buf);
        std::cout << "CDF X values (throttled page accesses aggregated by phys_page):\n" << aggregated_counts_buf.str() << std::endl;
        std::cout << "CDF Y values (probability):\n" << percentages_buf_2.str() << std::endl;
    }
}

SubsecondTime
DramPerfModelDisagg::getAccessLatencyRemote(SubsecondTime pkt_time, UInt64 pkt_size, core_id_t requester, IntPtr address, DramCntlrInterface::access_t access_type, ShmemPerf *perf)
{
    // pkt_size is in 'Bytes'

    // When partition queues is off: don't get cacheline when moving the page
    SubsecondTime cacheline_hw_access_latency = SubsecondTime::Zero();
    if (m_r_partition_queues) {
        // When partition queues is on, access the requested cacheline before the page, if applicable
        cacheline_hw_access_latency = m_dram_hardware_cntlr.getDramAccessCost(pkt_time, pkt_size, requester, address, perf, true, false, false);
        m_total_remote_dram_hardware_latency_cachelines += cacheline_hw_access_latency;
        m_total_remote_dram_hardware_latency_cachelines_count++;
    }

    SubsecondTime t_now = pkt_time + cacheline_hw_access_latency;

    SubsecondTime t_remote_queue_request = t_now;  // time of making queue request (after DRAM hardware access cost added)
    UInt64 phys_page = address & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
    UInt64 cacheline = address & ~((UInt64(1) << floorLog2(m_cache_line_size)) - 1);  // Was << 6
    if (m_r_cacheline_gran)
        phys_page = cacheline;
    
    // Compress
    UInt32 size = pkt_size;  // store the compressed size of the cacheline (unmodified when compression is off)
    SubsecondTime cacheline_compression_latency = SubsecondTime::Zero();  // when cacheline compression is not enabled, this is always 0
    if (m_use_compression) {
        if (m_r_cacheline_gran) {
            if (m_r_partition_queues == 3 || m_r_partition_queues == 4) {
                m_compression_controller.m_compression_model->update_bandwidth_utilization(m_data_movement->getCachelineQueueUtilizationPercentage(t_now));
            }
            else {  // use getTotalQueueUtilizationPercentage
                m_compression_controller.m_compression_model->update_bandwidth_utilization(m_data_movement->getTotalQueueUtilizationPercentage(t_now));
            }

            cacheline_compression_latency = m_compression_controller.compress(false, phys_page, m_cache_line_size, &size);
            t_now += cacheline_compression_latency;
        } else if (m_use_cacheline_compression) {
            if (m_r_partition_queues == 3 || m_r_partition_queues == 4) {
                m_compression_controller.m_cacheline_compression_model->update_bandwidth_utilization(m_data_movement->getCachelineQueueUtilizationPercentage(t_now));
            }
            else {  // use getTotalQueueUtilizationPercentage
                m_compression_controller.m_cacheline_compression_model->update_bandwidth_utilization(m_data_movement->getTotalQueueUtilizationPercentage(t_now));
            }

            cacheline_compression_latency = m_compression_controller.compress(true, phys_page, m_cache_line_size, &size);
            t_now += cacheline_compression_latency;
        }
    }
    // TODO: datamovement_delay is only added to t_now if(m_r_mode != 4 && !m_r_enable_selective_moves), should we also only add cacheline compression latency if the same condition is true?

    SubsecondTime cacheline_network_processing_time;
    if (m_r_partition_queues > 0)
        cacheline_network_processing_time = m_r_cacheline_bandwidth.getRoundedLatency(8*size);
    else
        cacheline_network_processing_time = m_r_bus_bandwidth.getRoundedLatency(8*size);
    SubsecondTime cacheline_queue_delay;
    if (m_r_throttle_redundant_moves) {
        // Use computeQueueDelayNoEffect here, in case need we end up moving the whole page instead and not requesting the cacheline separately
        cacheline_queue_delay = getPartitionQueueDelayNoEffect(t_remote_queue_request + cacheline_compression_latency, size, QueueModel::CACHELINE, requester);
    } else {  // always make cacheline queue request
        cacheline_queue_delay = getPartitionQueueDelayTrackBytes(t_remote_queue_request + cacheline_compression_latency, size, QueueModel::CACHELINE, requester);
    }
    SubsecondTime datamovement_delay = (cacheline_queue_delay + cacheline_network_processing_time);
    m_cacheline_network_processing_time += cacheline_network_processing_time;
    m_cacheline_network_queue_delay += cacheline_queue_delay;
    m_remote_to_local_cacheline_move_count++;
    
    // TODO: Currently model decompression by adding decompression latency to inflight page time
    if (m_use_compression && (m_r_cacheline_gran || m_use_cacheline_compression)) {
        datamovement_delay += m_compression_controller.decompress(!m_r_cacheline_gran, phys_page);
    }

    // Track access to page
    bool move_page = false;
    if (m_r_mode == 2 || m_r_mode == 5) {  // Update m_remote_access_tracker
        auto it = m_remote_access_tracker.find(phys_page);
        if (it != m_remote_access_tracker.end()) {
            m_remote_access_tracker[phys_page] += 1; 
        }
        else {
            m_remote_access_tracker[phys_page] = 1;
        }
        m_recent_remote_accesses.insert(std::pair<SubsecondTime, UInt64>(t_now, phys_page));
    }
    if (m_r_mode == 2 && m_remote_access_tracker[phys_page] > m_r_datamov_threshold) {
        // Only move pages when the page has been accessed remotely m_r_datamov_threshold times
        move_page = true;
    } 
    if (m_r_mode == 1 || m_r_mode == 3) {
        move_page = true; 
    }
    if (m_r_mode == 5) {
        // Use m_recent_remote_accesses to update m_remote_access_tracker so that it only keeps recent (10^5 ns) remote accesses
        while (!m_recent_remote_accesses.empty() && m_recent_remote_accesses.begin()->first + m_r_mode_5_remote_access_history_window_size < t_now) {
            auto entry = m_recent_remote_accesses.begin();
            m_remote_access_tracker[entry->second] -= 1;
            m_recent_remote_accesses.erase(entry);
        }

        double page_queue_utilization = m_data_movement->getPageQueueUtilizationPercentage(t_now);
        if (page_queue_utilization < m_r_mode_5_limit_moves_threshold) {
            // If queue utilization percentage is less than threshold, always move.
            move_page = true;
        } else {
            if (m_remote_access_tracker[phys_page] > m_r_datamov_threshold) {
                // Otherwise, only move if the page has been accessed a threshold number of times.
                move_page = true;
                ++m_rmode5_page_moved_due_to_threshold;
            } else {
                ++m_move_page_cancelled_rmode5;  // we chose not to move the page
            }
        }
    }
    // Cancel moving the page if the amount of reserved bufferspace in localdram for inflight + inflight_evicted pages is not enough to support an additional move
    if (m_r_partition_queues > 1 && move_page && m_r_reserved_bufferspace > 0 && ((m_inflight_pages.size() + m_inflightevicted_pages.size())  >= ((double)m_r_reserved_bufferspace/100)*(m_localdram_size/m_page_size))) {
        move_page = false;
        ++m_move_page_cancelled_bufferspace_full;
    }
    double page_queue_utilization_percentage = m_data_movement->getPageQueueUtilizationPercentage(t_now);
    double cacheline_queue_utilization_percentage = m_data_movement->getCachelineQueueUtilizationPercentage(t_now);
    // Cancel moving the page if the queue used to move the page is already full AND there is space in the cacheline queue
    if (m_r_partition_queues > 1 && move_page && page_queue_utilization_percentage > m_r_page_queue_utilization_threshold && ((m_keep_space_in_cacheline_queue && cacheline_queue_utilization_percentage <= m_r_cacheline_queue_type1_utilization_threshold) || page_queue_utilization_percentage > cacheline_queue_utilization_percentage)) {  // save 5% for evicted pages?
        move_page = false;
        ++m_move_page_cancelled_datamovement_queue_full;

        if (m_use_throttled_pages_tracker) {
            // Track future accesses to throttled page
            auto it = m_throttled_pages_tracker.find(phys_page);
            if (it != m_throttled_pages_tracker.end() && t_now <= m_r_ideal_pagethrottle_remote_access_history_window_size + m_throttled_pages_tracker[phys_page].first) {
                // found it, and last throttle of this page was within 10^5 ns
                m_throttled_pages_tracker[phys_page].first = t_now;
                m_throttled_pages_tracker[phys_page].second += 1;
            } else {
                if (it != m_throttled_pages_tracker.end()) {  // there was previously a value in the map
                    // printf("disagg.cc: m_throttled_pages_tracker[%lu] max was %u\n", phys_page, m_throttled_pages_tracker[phys_page].second);
                    m_throttled_pages_tracker_values.push_back(std::pair<UInt64, UInt32>(phys_page, m_throttled_pages_tracker[phys_page].second));
                }
                m_throttled_pages_tracker[phys_page] = std::pair<SubsecondTime, UInt32>(t_now, 0);
            }
        }
    } else if (m_use_throttled_pages_tracker) {
        // Page was not throttled
        auto it = m_throttled_pages_tracker.find(phys_page);
        if (it != m_throttled_pages_tracker.end()) {  // there was previously a value in the map
            // printf("disagg.cc: m_throttled_pages_tracker[%lu] max was %u\n", phys_page, m_throttled_pages_tracker[phys_page].second);
            m_throttled_pages_tracker_values.push_back(std::pair<UInt64, UInt32>(phys_page, m_throttled_pages_tracker[phys_page].second));
            m_throttled_pages_tracker.erase(phys_page);  // page was moved, clear
        }
    }
   
    if (!m_r_use_separate_queue_model) {  // when a separate remote QueueModel is used, the network latency is added there
        t_now += m_r_added_latency;
    }
    if (m_r_mode != 4 && !m_r_enable_selective_moves) {
        t_now += datamovement_delay;
        m_total_remote_datamovement_latency += datamovement_delay;
    }

    perf->updateTime(t_now, ShmemPerf::DRAM_BUS);

    SubsecondTime page_network_processing_time = SubsecondTime::Zero();

    SubsecondTime page_datamovement_delay = SubsecondTime::Zero();
    if (move_page) {
        ++m_page_moves;

        SubsecondTime page_compression_latency = SubsecondTime::Zero();  // when page compression is not enabled, this is always 0
        SubsecondTime page_hw_access_latency = SubsecondTime::Zero();
        SubsecondTime local_page_hw_write_latency = SubsecondTime::Zero();
        std::vector<std::pair<UInt64, SubsecondTime>> updated_inflight_page_arrival_time_deltas;  // only for m_r_partition_queues == 3, ie windowed_mg1_remote_subqueuemodels
        if (m_r_simulate_datamov_overhead && !m_r_cacheline_gran) {
            UInt32 page_size = m_page_size;
            if (m_r_partition_queues) {
                page_size = m_page_size - m_cache_line_size;  // We don't have to move the cacheline since it was separately moved via the cacheline queue
            }

            // Compress
            if (m_use_compression) {
                if (m_use_r_compressed_pages && m_compression_controller.address_to_compressed_size.find(phys_page) != m_compression_controller.address_to_compressed_size.end()) {
                    page_size = m_compression_controller.address_to_compressed_size[phys_page];
                } else {
                    m_compression_controller.m_compression_model->update_bandwidth_utilization(m_data_movement->getPageQueueUtilizationPercentage(t_now));

                    size_t size_to_compress = (m_r_partition_queues) ? m_page_size - m_cache_line_size : m_page_size;
                    page_compression_latency = m_compression_controller.compress(false, phys_page, size_to_compress, &page_size);
                    t_now += page_compression_latency;
                }
            }

            // Other systems using the remote memory and creating disturbance
            if (m_r_disturbance_factor > 0 && (unsigned int)(rand() % 100) < m_r_disturbance_factor) {
                /* SubsecondTime page_datamovement_delay = */ getPartitionQueueDelayTrackBytes(t_remote_queue_request, page_size, QueueModel::PAGE, requester);
                m_extra_pages++;
            }

            // Round page size for dram up to the nearest multiple of m_cache_line_size
            UInt32 page_size_for_dram = page_size;
            UInt32 cacheline_remainder = page_size % m_cache_line_size;
            if (cacheline_remainder > 0)
                page_size_for_dram = page_size_for_dram + m_cache_line_size - cacheline_remainder;
            if (m_r_partition_queues) {
                // Set exclude_cacheline to true (in this case, should still pass in the whole page size for the size parameter)
                page_hw_access_latency = m_dram_hardware_cntlr.getDramAccessCost(t_remote_queue_request, page_size_for_dram, requester, address, perf, true, true, true);
                local_page_hw_write_latency = m_dram_hardware_cntlr.getDramWriteCost(t_remote_queue_request, page_size_for_dram, requester, address, perf, true, true);
            } else {
                page_hw_access_latency = m_dram_hardware_cntlr.getDramAccessCost(t_remote_queue_request, page_size_for_dram, requester, address, perf, true, false, true);
                local_page_hw_write_latency = m_dram_hardware_cntlr.getDramWriteCost(t_remote_queue_request, page_size_for_dram, requester, address, perf, false, true);
            }
            m_total_remote_dram_hardware_latency_pages += page_hw_access_latency;
            m_total_remote_dram_hardware_latency_pages_count++;
            m_total_local_dram_hardware_write_latency_pages += local_page_hw_write_latency;

            // Compute network transmission delay
            if (m_r_partition_queues > 0)
                page_network_processing_time = m_r_page_bandwidth.getRoundedLatency(8*page_size);  // default of moving the whole page, use processing time of just the cacheline if we use that in the critical path
            else
                page_network_processing_time = m_r_bus_bandwidth.getRoundedLatency(8*page_size);

            
            if (m_r_partition_queues == 3) {
                page_datamovement_delay = m_data_movement->computeQueueDelayTrackBytes(t_remote_queue_request + page_hw_access_latency + page_compression_latency, m_r_page_bandwidth.getRoundedLatency(8*page_size), page_size, QueueModel::PAGE, requester, true, phys_page);
            } else {
                page_datamovement_delay = getPartitionQueueDelayTrackBytes(t_remote_queue_request + page_hw_access_latency + page_compression_latency, page_size, QueueModel::PAGE, requester);
            }

            // TODO: Currently model decompression by adding decompression latency to inflight page time
            SubsecondTime page_decompression_latency = SubsecondTime::Zero();
            if (m_use_compression) {
                page_decompression_latency = m_compression_controller.decompress(false, phys_page);
                page_datamovement_delay += page_decompression_latency;
            }

            // Update t_now after page_datamovement_delay includes the decompression latency
            if (m_r_partition_queues > 1) {
                m_page_network_processing_time += page_network_processing_time;
                m_page_network_queue_delay += page_datamovement_delay - page_decompression_latency;
                m_remote_to_local_page_move_count++;

                if (page_hw_access_latency + page_compression_latency + page_datamovement_delay <= cacheline_hw_access_latency + cacheline_compression_latency + datamovement_delay) {
                    // If the page arrival time via the page queue is faster than the cacheline via the cacheline queue, use the page queue arrival time
                    // (and the cacheline request is not sent)
                    t_now += (page_datamovement_delay + page_network_processing_time);  // if nonzero, compression latency was earlier added to t_now already
                    m_total_remote_datamovement_latency += (page_datamovement_delay + page_network_processing_time);
                    t_now -= cacheline_hw_access_latency;  // remove previously added latency
                    t_now += page_hw_access_latency;
                    t_now += local_page_hw_write_latency;
                    if (m_r_mode != 4 && !m_r_enable_selective_moves) {
                        t_now -= datamovement_delay;  // only subtract if it was added earlier
                        m_total_remote_datamovement_latency -= datamovement_delay;
                        m_cacheline_network_processing_time -= cacheline_network_processing_time;
                        m_cacheline_network_queue_delay -= cacheline_queue_delay;
                        m_remote_to_local_cacheline_move_count--;
                    }
                    if (m_use_compression && (m_r_cacheline_gran || m_use_cacheline_compression))
                        t_now -= cacheline_compression_latency;  // essentially didn't separately compress cacheline, so subtract this previously added compression latency
                    ++partition_queues_cacheline_slower_than_page;
                } else {
                    // Actually put the cacheline request on the cacheline queue, since after checking the page arrival time we're sure we actually use the cacheline request
                    // This is an ideal situation, since in real life we might not be able to compare these times, not actually send the cacheline request, avoid the cacheline compression latency, etc
                    if (m_r_throttle_redundant_moves) {
                        if (m_r_partition_queues == 3) {
                            // Delayed inflight pages, if any, updated after m_inflight_pages includes the current page
                            cacheline_queue_delay = m_data_movement->computeQueueDelayTrackBytesPotentialPushback(t_remote_queue_request + cacheline_compression_latency, m_r_cacheline_bandwidth.getRoundedLatency(8*size), size, QueueModel::CACHELINE, updated_inflight_page_arrival_time_deltas, true, requester);
                        } else if (m_r_partition_queues == 2 || m_r_partition_queues == 4) {
                            cacheline_queue_delay = getPartitionQueueDelayTrackBytes(t_remote_queue_request + cacheline_compression_latency, size, QueueModel::CACHELINE, requester);
                        }
                    }
                    t_now -= page_compression_latency;  // Page compression is not on critical path; this is 0 if compression is off
                    ++m_redundant_moves;
                    ++m_redundant_moves_type1;
                    m_redundant_moves_type1_time_savings += (page_hw_access_latency + page_compression_latency + page_datamovement_delay) - (cacheline_hw_access_latency + cacheline_compression_latency + datamovement_delay);

                    if (m_track_inflight_cachelines) {
                        // datamovement_delay includes cacheline network processing time; for PQ=on, cacheline hw latency already included in t_remote_queue_request 
                        addInflightCacheline(cacheline, t_remote_queue_request + cacheline_compression_latency + datamovement_delay, access_type);
                    }
                }
            } else {
                // Default is requesting the whole page at once (instead of also requesting cacheline), so replace time of cacheline request with the time of the page request
                t_now += (page_datamovement_delay + page_network_processing_time);
                m_total_remote_datamovement_latency += (page_datamovement_delay + page_network_processing_time);
                m_page_network_processing_time += page_network_processing_time;
                m_page_network_queue_delay += page_datamovement_delay - page_decompression_latency;
                m_remote_to_local_page_move_count++;
                t_now += page_hw_access_latency;
                t_now += local_page_hw_write_latency;
                if (m_r_mode != 4 && !m_r_enable_selective_moves) {
                    t_now -= datamovement_delay;  // only subtract if it was added earlier
                    m_total_remote_datamovement_latency -= datamovement_delay;
                    m_cacheline_network_processing_time -= cacheline_network_processing_time;
                    m_cacheline_network_queue_delay -= cacheline_queue_delay;
                    m_remote_to_local_cacheline_move_count--;
                }
                if (m_use_compression && (m_r_cacheline_gran || m_use_cacheline_compression))
                    t_now -= cacheline_compression_latency;  // essentially didn't separately compress cacheline, so subtract this previously added compression latency
            }
        } else if (!m_r_simulate_datamov_overhead) {
            // Include the hardware access cost of the page
            page_hw_access_latency = m_dram_hardware_cntlr.getDramAccessCost(t_remote_queue_request, m_page_size, requester, address, perf, true, false, true);
            t_now += page_hw_access_latency;
            t_now += local_page_hw_write_latency;
            m_total_remote_dram_hardware_latency_pages += page_hw_access_latency;
            m_total_remote_dram_hardware_latency_pages_count++;
            m_total_local_dram_hardware_write_latency_pages += local_page_hw_write_latency;
            if (m_r_mode != 4 && !m_r_enable_selective_moves) {
                t_now -= datamovement_delay;  // only subtract if it was added earlier
                m_total_remote_datamovement_latency -= datamovement_delay;
                m_cacheline_network_processing_time -= cacheline_network_processing_time;
                m_cacheline_network_queue_delay -= cacheline_queue_delay;
                m_remote_to_local_cacheline_move_count--;
            }
        } else {
            page_datamovement_delay = SubsecondTime::Zero();
        }


        // Commenting these out since for this function to be called by isRemoteAccess() returning true, these statements are already true
        // assert(!m_local_pages.find(phys_page));
        // assert(m_remote_pages.count(phys_page));
        m_local_pages.push_back(phys_page);
        if (m_r_exclusive_cache)
            m_remote_pages.erase(phys_page);
        // if (!m_speed_up_simulation)
        //     m_local_pages_remote_origin[phys_page] = 1;
        if (m_use_ideal_page_throttling || !m_speed_up_simulation)
            m_moved_pages_no_access_yet.push_back(phys_page);


        SubsecondTime global_time = Sim()->getClockSkewMinimizationServer()->getGlobalTime();
        SubsecondTime page_arrival_time = t_remote_queue_request + page_hw_access_latency + page_compression_latency + page_datamovement_delay + page_network_processing_time + local_page_hw_write_latency;  // page_datamovement_delay already contains the page decompression latency
        if (global_time > page_arrival_time + SubsecondTime::NS(50)) {  // if global time is more than 50 ns ahead of page_arrival_time
            ++m_global_time_much_larger_than_page_arrival;
            m_sum_global_time_much_larger += global_time - page_arrival_time;
        }
        if (m_r_partition_queues == 0 && m_r_reserved_bufferspace > 0 && ((m_inflight_pages.size() + m_inflightevicted_pages.size()) >= ((double)m_r_reserved_bufferspace/100)*(m_localdram_size/m_page_size))) {
            // PQ=off, page movement would exceed inflight pages bufferspace
            // Estimate how long it would take to send packet if inflight page buffer is full
            SubsecondTime extra_delay_penalty = SubsecondTime::NS() * 2000;
            t_now += extra_delay_penalty;
            m_inflight_pages_extra[phys_page] = SubsecondTime::max(global_time, page_arrival_time + extra_delay_penalty);
            ++m_bufferspace_full_page_still_moved;
            if (m_inflight_pages_extra.size() > m_max_inflight_extra_bufferspace)
                m_max_inflight_extra_bufferspace++;
        } else if (page_queue_utilization_percentage > m_r_page_queue_utilization_threshold) {
            // PQ=off, page movement would exceed network bandwidth
            // Queue model estimates how long it would take to send packet if inflight page buffer is full
            m_inflight_pages_extra[phys_page] = SubsecondTime::max(global_time, page_arrival_time);
            m_inflight_redundant[phys_page] = 0;
            m_pages_cacheline_request_limit_exceeded.erase(phys_page);
            ++m_datamovement_queue_full_page_still_moved;
            if (m_inflight_pages_extra.size() > m_max_inflight_extra_bufferspace)
                m_max_inflight_extra_bufferspace++;
        } else {
            m_inflight_pages[phys_page] = SubsecondTime::max(global_time, page_arrival_time);
            m_inflight_redundant[phys_page] = 0;
            m_pages_cacheline_request_limit_exceeded.erase(phys_page);
            if (m_inflight_pages.size() > m_max_inflight_bufferspace)
                m_max_inflight_bufferspace++;
            if (m_inflight_pages.size() + m_inflightevicted_pages.size() > m_max_total_bufferspace)
                m_max_total_bufferspace++;  // update stat

            for (auto it = updated_inflight_page_arrival_time_deltas.begin(); it != updated_inflight_page_arrival_time_deltas.end(); ++it) {
                if (m_inflight_pages.count(it->first) && it->second > SubsecondTime::Zero()) {
                    m_inflight_pages_delay_time += it->second;
                    m_inflight_pages[it->first] += it->second;  // update arrival time if it's still an inflight page
                    ++m_inflight_page_delayed;
                }
            }
        }

    }
    if (!move_page || !m_r_simulate_datamov_overhead || m_r_cacheline_gran) {  // move_page == false, or earlier condition (m_r_simulate_datamov_overhead && !m_r_cacheline_gran) is false
        // Actually put the cacheline request on the queue, since after now we're sure we actually use the cacheline request
        // This actual cacheline request probably has a similar delay value as the earlier computeQueueDelayNoEffect value, no need to update t_now
        // When partition queues is on, the cacheline HW access cost request was already made at the beginning of this function
        if (!m_r_partition_queues) {
            // When partition queues is off, only calculate cacheline access cost when moving the cacheline instead of the page
            cacheline_hw_access_latency = m_dram_hardware_cntlr.getDramAccessCost(pkt_time, pkt_size, requester, address, perf, true, false, false);  // A change for 64 byte page granularity
            t_remote_queue_request = pkt_time + cacheline_hw_access_latency;
            m_total_remote_dram_hardware_latency_cachelines += cacheline_hw_access_latency;
            m_total_remote_dram_hardware_latency_cachelines_count++;
            t_now += cacheline_hw_access_latency;
        } else {
            if (cacheline_queue_utilization_percentage > m_r_cacheline_queue_type1_utilization_threshold) {
                ++m_datamovement_queue_full_cacheline_still_moved;
            }
        }

        // Other systems using the remote memory and creating disturbance
        if (m_r_disturbance_factor > 0 && (unsigned int)(rand() % 100) < m_r_disturbance_factor) {
            /* SubsecondTime page_datamovement_delay = */ getPartitionQueueDelayTrackBytes(t_remote_queue_request, size, QueueModel::CACHELINE, requester);
            m_extra_cachelines++;
        }

        if (m_track_inflight_cachelines) {
            // datamovement_delay includes cacheline network processing time; for PQ=on, cacheline hw latency already included in t_remote_queue_request 
            addInflightCacheline(cacheline, t_remote_queue_request + cacheline_compression_latency + datamovement_delay, access_type);            
        }

        if (m_r_throttle_redundant_moves) {
            if (m_r_partition_queues == 3) {
                std::vector<std::pair<UInt64, SubsecondTime>> updated_inflight_page_arrival_time_deltas;
                cacheline_queue_delay = m_data_movement->computeQueueDelayTrackBytesPotentialPushback(t_remote_queue_request + cacheline_compression_latency, m_r_cacheline_bandwidth.getRoundedLatency(8*size), size, QueueModel::CACHELINE, updated_inflight_page_arrival_time_deltas, true, requester);
                for (auto it = updated_inflight_page_arrival_time_deltas.begin(); it != updated_inflight_page_arrival_time_deltas.end(); ++it) {
                    if (m_inflight_pages.count(it->first) && it->second > SubsecondTime::Zero()) {
                        m_inflight_pages_delay_time += it->second;
                        m_inflight_pages[it->first] += it->second;  // update arrival time if it's still an inflight page
                        ++m_inflight_page_delayed;
                    }
                }
            } else {
                // move_page == false so if PQ=off actually put the cacheline request on the queue
                cacheline_queue_delay = getPartitionQueueDelayTrackBytes(t_remote_queue_request + cacheline_compression_latency, size, QueueModel::CACHELINE, requester);
            }
        }

        // Track number of cacheline moves for each phys_page
        auto it = m_inflight_redundant.find(phys_page);
        if (it == m_inflight_redundant.end()) {
            m_inflight_redundant[phys_page] = 0;
            m_pages_cacheline_request_limit_exceeded.erase(phys_page);
        } else {
            m_inflight_redundant[phys_page] += 1;
            if (m_inflight_redundant[phys_page] >= m_r_redundant_moves_limit)
                m_pages_cacheline_request_limit_exceeded.insert(phys_page);
        }
        if (m_auto_turn_off_partition_queues && cacheline_queue_utilization_percentage > m_turn_off_pq_cacheline_queue_utilization_threshold && m_pages_cacheline_request_limit_exceeded.size() > m_cancel_pq_inflight_buffer_threshold * (m_inflight_pages.size() + m_inflight_pages_extra.size())) {
            m_r_partition_queues = 0;
            std::cout << "Partition queues turned off due to >= type 1 redundant moves limit of " << m_r_redundant_moves_limit << " at " << m_num_accesses << " accesses" << std::endl;
        }
    } 

    if (move_page) {  // Check if there's place in local DRAM and if not evict an older page to make space
        t_now += possiblyEvict(phys_page, pkt_time, requester);
    }

    possiblyPrefetch(phys_page, t_now, requester);

    SubsecondTime access_latency = t_now - pkt_time;

    // Update stats
    m_total_remote_access_latency += access_latency;
    m_total_access_latency += access_latency;
    if (access_latency < m_access_latency_outlier_threshold) {
        m_total_access_latency_no_outlier += access_latency;
        m_total_remote_access_latency_no_outlier += access_latency;
    } else {
        m_access_latency_outlier_count += 1;
        m_remote_access_latency_outlier_count += 1;
    }
    updateLocalRemoteLatencyStat(access_latency);

    return access_latency;
}

void
DramPerfModelDisagg::updateLocalIpcStat(UInt64 instr_count)
{
    if (m_ipc_window_cur_size == 0)
        m_ipc_window_start_instr_count = instr_count;
    m_ipc_window_cur_size += 1;
    if (m_ipc_window_cur_size == m_ipc_window_capacity) {
        ComponentPeriod cp = ComponentPeriod::fromFreqHz(1000000000 * Sim()->getCfg()->getFloat("perf_model/core/frequency"));
        SubsecondTimeCycleConverter converter = SubsecondTimeCycleConverter(&cp);

        m_ipc_window_end_instr_count = instr_count;
        UInt64 instructions = m_ipc_window_end_instr_count - m_ipc_window_start_instr_count;
        UInt64 cycles = converter.subsecondTimeToCycles(SubsecondTime::NS(1000) * m_ipc_window_capacity);
        double ipc = instructions / (double) cycles;
        ipc = std::round(ipc * 100000.0) / 100000.0;
        m_local_ipcs.push_back(ipc);
        m_instruction_count_x_axis.push_back(m_ipc_window_end_instr_count);

        m_ipc_window_cur_size = 0;
    }
}

void
DramPerfModelDisagg::updateLocalRemoteLatencyStat(SubsecondTime access_latency)
{
    m_local_total_remote_access_latency += access_latency;
    m_local_total_remote_access_latency_window_cur_size += 1;
    if (m_local_total_remote_access_latency_window_cur_size == m_local_total_remote_access_latency_window_capacity) {
        m_local_total_remote_access_latency_avgs.push_back(m_local_total_remote_access_latency / (float) m_local_total_remote_access_latency_window_capacity);
        m_local_total_remote_access_latency = SubsecondTime::Zero();
        m_local_total_remote_access_latency_window_cur_size = 0;
    }
}

void
DramPerfModelDisagg::updateBandwidth()
{
    m_update_bandwidth_count += 1;
    if (m_use_dynamic_bandwidth && m_update_bandwidth_count % m_disturbance_bq_size == 0) {
        m_r_disturbance_factor = rand() % 101;
    } else if (m_use_dynamic_cl_queue_fraction_adjustment) {
        // Same formulas here as in DramPerfModelDisagg constructor
        m_r_bus_bandwidth.changeBandwidth(m_base_bus_bandwidth / (1000 * m_r_bw_scalefactor));  // Remote memory
        m_r_page_bandwidth.changeBandwidth(m_base_bus_bandwidth / (1000 * m_r_bw_scalefactor / (1 - m_r_cacheline_queue_fraction)));  // Remote memory - Partitioned Queues => Page Queue
        m_r_cacheline_bandwidth.changeBandwidth(m_base_bus_bandwidth / (1000 * m_r_bw_scalefactor / m_r_cacheline_queue_fraction));  // Remote memory - Partitioned Queues => Cacheline Queue
        // Currently only windowed_mg1_remote_ind_queues QueueModel updates stats tracking based on updateBandwidth()
        m_data_movement->updateBandwidth(m_r_bus_bandwidth.getBandwidthBitsPerUs(), m_r_cacheline_queue_fraction);
    }
}

void
DramPerfModelDisagg::updateLatency()
{
    m_update_latency_count += 1;
    if (m_use_dynamic_latency && m_update_latency_count % m_disturbance_bq_size == 0) {
        int added_netlat_ns = (rand() % 300) + m_r_added_latency.getNS();
        m_data_movement->updateAddedNetLat(added_netlat_ns);
    }
}

void
DramPerfModelDisagg::updateBandwidthUtilizationCount(SubsecondTime pkt_time)
{
    double bw_utilization = m_data_movement->getPageQueueUtilizationPercentage(pkt_time);
    int decile = (int)(bw_utilization * 10);
    if (decile > 10)
        decile = 10;  // put all utilizations above 100% here
    m_bw_utilization_decile_to_count[decile] += 1;
}

void
DramPerfModelDisagg::updateDynamicCachelineQueueRatio(SubsecondTime pkt_time)
{
    UInt64 total_recent_accesses = m_num_recent_remote_accesses + m_num_recent_remote_additional_accesses + m_num_recent_local_accesses;
    UInt64 total_recent_pages = m_recent_accessed_pages.size();
    // average number of cachelines accessed per unique page
    double true_page_locality_measure = (double)total_recent_accesses / total_recent_pages;
    m_page_locality_measures.push_back(true_page_locality_measure);
    
    // counts every non-first access to a page as a "local" access
    double modified_page_locality_measure = (double)(m_num_recent_local_accesses + m_num_recent_remote_additional_accesses) / total_recent_accesses;
    // counts every non-first access to a page that wasn't accessed again via the cacheline queue as a "local" access
    double modified2_page_locality_measure = (double)m_num_recent_local_accesses / total_recent_accesses;
    m_modified_page_locality_measures.push_back(modified_page_locality_measure);
    m_modified2_page_locality_measures.push_back(modified2_page_locality_measure);

    // Adjust cl queue fraction if needed
    double cacheline_queue_utilization_percentage = m_data_movement->getCachelineQueueUtilizationPercentage(pkt_time); 
    if (m_use_dynamic_cl_queue_fraction_adjustment && m_r_partition_queues > 1 && (m_data_movement->getPageQueueUtilizationPercentage(pkt_time) > 0.8 || cacheline_queue_utilization_percentage > 0.8)) {
        // Consider adjusting m_r_cacheline_queue_fraction
        // 0.2 is chosen as the "baseline" cacheline queue fraction, 0.025 is chosen as a step size
        if (true_page_locality_measure > 40 + std::max(0.0, (0.2 - m_r_cacheline_queue_fraction) * 100)) {
            // Page locality high, increase prioritization of cachelines
            m_r_cacheline_queue_fraction -= 0.025;
            if (m_r_cacheline_queue_fraction < 0.1)  // min cl queue fraction
                m_r_cacheline_queue_fraction = 0.1;
            else
                ++m_r_cacheline_queue_fraction_decreased;
        } else if (true_page_locality_measure < 20 - std::max(0.0, (m_r_cacheline_queue_fraction - 0.2) * 50)) {
            // Page locality low, increase prioritization of cachelines
            m_r_cacheline_queue_fraction += 0.025;
            if (m_r_cacheline_queue_fraction > 0.6)  // max cl queue fraction (for now)
                m_r_cacheline_queue_fraction = 0.6;
            else
                ++m_r_cacheline_queue_fraction_increased;
        }
        updateBandwidth();

        // Update stats
        if (m_r_cacheline_queue_fraction < m_min_r_cacheline_queue_fraction) {
            m_min_r_cacheline_queue_fraction = m_r_cacheline_queue_fraction;
            m_min_r_cacheline_queue_fraction_stat_scaled = m_min_r_cacheline_queue_fraction * 10000;
        }
        if (m_r_cacheline_queue_fraction > m_max_r_cacheline_queue_fraction) {
            m_max_r_cacheline_queue_fraction = m_r_cacheline_queue_fraction;
            m_max_r_cacheline_queue_fraction_stat_scaled = m_max_r_cacheline_queue_fraction * 10000;
        }
    }

    // Reset variables
    m_num_recent_remote_accesses = 0;
    m_num_recent_remote_additional_accesses = 0;   // For cacheline queue requests made on inflight pages. Track this separately since they could be counted as either "remote" or "local" cacheline accesses
    m_num_recent_local_accesses = 0;
    m_recent_accessed_pages.clear();
}

SubsecondTime
DramPerfModelDisagg::getAccessLatency(SubsecondTime pkt_time, UInt64 pkt_size, core_id_t requester, IntPtr address, DramCntlrInterface::access_t access_type, ShmemPerf *perf)
{
    if (m_track_page_bw_utilization_stats) {
        // Update BW utilization count
        updateBandwidthUtilizationCount(pkt_time);
    }
    // Update BW utilization stat (5 decimal precision)
    if (m_r_partition_queues) {
        m_cacheline_bw_utilization_sum += m_data_movement->getCachelineQueueUtilizationPercentage(pkt_time) * m_r_cacheline_queue_fraction * 100000;
        m_page_bw_utilization_sum += m_data_movement->getPageQueueUtilizationPercentage(pkt_time) * (1. - m_r_cacheline_queue_fraction) * 100000;
        m_total_bw_utilization_sum += m_data_movement->getCachelineQueueUtilizationPercentage(pkt_time) * m_r_cacheline_queue_fraction + m_data_movement->getPageQueueUtilizationPercentage(pkt_time) * (1. - m_r_cacheline_queue_fraction) * 100000;
    } else {
        m_total_bw_utilization_sum += m_data_movement->getPageQueueUtilizationPercentage(pkt_time) * 100000;
    }

    UInt64 phys_page = address & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
    UInt64 cacheline = address & ~((UInt64(1) << floorLog2(m_cache_line_size)) - 1);  // Was << 6
    if (m_r_cacheline_gran)
        phys_page = cacheline;

    if (!m_speed_up_simulation) {
        if (m_page_usage_map.count(phys_page) == 0) {
            ++m_unique_pages_accessed;
            m_page_usage_map[phys_page] = 0;
        } else {
            m_page_usage_map[phys_page] += 1;
        }
    }

    SubsecondTime current_time = SubsecondTime::max(Sim()->getClockSkewMinimizationServer()->getGlobalTime(), pkt_time);
    // m_inflight_pages: tracks which pages are being moved and when the movement will complete
    // Check if the page movement is over and if so, remove from the list
    // Do this for both queues, forward and backward
    std::map<UInt64, SubsecondTime>::iterator i;
    for (i = m_inflight_pages.begin(); i != m_inflight_pages.end();) {
        if (i->second <= current_time) {
            m_inflight_redundant.erase(i->first);
            m_pages_cacheline_request_limit_exceeded.erase(i->first);
            m_data_movement->removeInflightPage(i->first);
            m_inflight_pages.erase(i++);

            // Dirty write buffer
            UInt64 inflight_page = i->first;
            if (m_inflight_page_to_dirty_write_count.find(inflight_page) != m_inflight_page_to_dirty_write_count.end()) {
                m_dirty_write_buffer_size -= m_inflight_page_to_dirty_write_count[inflight_page];
                m_inflight_page_to_dirty_write_count.erase(inflight_page);
                m_max_dirty_write_buffer_size = std::max(m_max_dirty_write_buffer_size, m_dirty_write_buffer_size);
            }
        } else {
            ++i;
        }
    }
    // Update dirty write buffer avg stat
    m_sum_write_buffer_size += m_dirty_write_buffer_size;
    
    for (i = m_inflight_pages_extra.begin(); i != m_inflight_pages_extra.end();) {
        if (i->second <= current_time) {
            m_inflight_redundant.erase(i->first);
            m_pages_cacheline_request_limit_exceeded.erase(i->first);
            m_inflight_pages_extra.erase(i++);
        } else {
            ++i;
        }
    }

    for (i = m_inflightevicted_pages.begin(); i != m_inflightevicted_pages.end();) {
        if (i->second <= current_time) {
            m_inflightevicted_pages.erase(i++);
        } else {
            ++i;
        }
    }

    // Inflight cachelines
    if (m_track_inflight_cachelines) {
        for (i = m_inflight_cachelines_reads.begin(); i != m_inflight_cachelines_reads.end();) {
            if (i->second <= current_time) {
                m_inflight_cachelines_reads.erase(i++);
            } else {
                ++i;
            }
        }
        for (i = m_inflight_cachelines_writes.begin(); i != m_inflight_cachelines_writes.end();) {
            if (i->second <= current_time) {
                m_inflight_cachelines_writes.erase(i++);
            } else {
                ++i;
            }
        }
        m_sum_inflight_cachelines_reads_size += m_inflight_cachelines_reads.size();
        m_sum_inflight_cachelines_writes_size += m_inflight_cachelines_writes.size();
        m_sum_inflight_cachelines_total_size += m_inflight_cachelines_reads.size() + m_inflight_cachelines_writes.size();
    }

    // Every 1000 cacheline requests, update page locality stats and determine whether to adjust cacheline queue ratio
    ++m_num_accesses;
    if (m_num_accesses % 30000 == 0 && (m_use_dynamic_cl_queue_fraction_adjustment || !m_speed_up_simulation)) {  // only track if using dynamic cl queue fraction, or if not speeding up simulation
        updateDynamicCachelineQueueRatio(pkt_time);
    }
    if (m_use_dynamic_cl_queue_fraction_adjustment || !m_speed_up_simulation) {  // only track if using dynamic cl queue fraction, or if not speeding up simulation
        if (!m_recent_accessed_pages.count(phys_page)) {
            m_recent_accessed_pages.insert(phys_page);
        }
    }

    // Should we enable a remote access?
    if (m_enable_remote_mem && isRemoteAccess(address, requester, access_type)) {
        if (access_type == DramCntlrInterface::READ) {
            ++m_remote_reads;
        } else {  // access_type == DramCntlrInterface::WRITE
            ++m_remote_writes;
        }
        ++m_num_recent_remote_accesses;
        return (getAccessLatencyRemote(pkt_time, pkt_size, requester, address, access_type, perf)); 
    }
    // if (!m_speed_up_simulation) {
    //     // m_local_reads_remote_origin
    //     if (m_local_pages_remote_origin.count(phys_page)) {
    //         m_local_pages_remote_origin[phys_page] += 1;
    //         if (access_type == DramCntlrInterface::READ) {
    //             ++m_local_reads_remote_origin;
    //         } else {  // access_type == DramCntlrInterface::WRITE
    //             ++m_local_writes_remote_origin;
    //         }
    //     }
    // }
    if (m_use_ideal_page_throttling || !m_speed_up_simulation)
        m_moved_pages_no_access_yet.remove(phys_page);  // there has been a local access to phys_page
   
    SubsecondTime cacheline_hw_access_latency = m_dram_hardware_cntlr.getDramAccessCost(pkt_time, pkt_size, requester, address, perf, false, false, false);
    m_total_local_dram_hardware_latency += cacheline_hw_access_latency;
    m_total_local_dram_hardware_latency_count++;
    SubsecondTime t_now = pkt_time + cacheline_hw_access_latency;

    SubsecondTime t_remote_queue_request = t_now;  // time of making queue request (after DRAM hardware access cost added)

    ++m_num_recent_local_accesses;
    if (((m_inflight_pages.find(phys_page) == m_inflight_pages.end()) && (m_inflight_pages_extra.find(phys_page) == m_inflight_pages_extra.end())) || m_r_enable_selective_moves) {
        // The phys_page is not included in m_inflight_pages and m_inflight_pages_extra, or m_r_enable_selective_moves is true: then total access latency = t_now - pkt_time
        SubsecondTime access_latency = t_now - pkt_time;
        m_total_local_access_latency += access_latency;
        m_total_access_latency += access_latency;

        if (access_latency < m_access_latency_outlier_threshold) {
            m_total_access_latency_no_outlier += access_latency;
            m_total_local_access_latency_no_outlier += access_latency;
        } else {
            m_access_latency_outlier_count += 1;
            m_local_access_latency_outlier_count += 1;
        }
        return access_latency;
    } else {
        // The phys_page is an inflight page and m_r_enable_selective_moves is false
        SubsecondTime access_latency;
        if (m_inflight_pages_extra.find(phys_page) != m_inflight_pages_extra.end()) {
            access_latency = m_inflight_pages_extra[phys_page] > t_now ? (m_inflight_pages_extra[phys_page] - pkt_time) : (t_now - pkt_time);
        } else {
            access_latency = m_inflight_pages[phys_page] > t_now ? (m_inflight_pages[phys_page] - pkt_time) : (t_now - pkt_time);
        }

        if (access_latency > (t_now - pkt_time)) {
            // The page is still in transit from remote to local memory
            m_inflight_hits++; 

            if (m_r_partition_queues > 1) {
                double cacheline_queue_utilization_percentage = m_data_movement->getCachelineQueueUtilizationPercentage(t_now);
                if (m_track_inflight_cachelines && access_type == DramCntlrInterface::READ && m_inflight_cachelines_reads.find(cacheline) != m_inflight_cachelines_reads.end()) {
                    // This cacheline read was already inflight, wait for to arrive
                    access_latency = SubsecondTime::min(access_latency, m_inflight_cachelines_reads[cacheline] - pkt_time);
                    ++m_redundant_moves_type2_cancelled_already_inflight;
                } else if (cacheline_queue_utilization_percentage > m_r_cacheline_queue_type2_utilization_threshold) {
                    // Can't make additional cacheline request
                    ++m_redundant_moves_type2_cancelled_datamovement_queue_full;
                    if (m_auto_turn_off_partition_queues)
                        m_inflight_redundant[phys_page] += 1;  // track this as a redundant request even though it wasn't actually made
                } else if (m_inflight_redundant[phys_page] < m_r_redundant_moves_limit) {
                    // Update dirty write buffer
                    if (access_type == DramCntlrInterface::WRITE) {
                        UInt64 dirty_write_count = 0;
                        if (m_inflight_page_to_dirty_write_count.find(phys_page) != m_inflight_page_to_dirty_write_count.end())
                            dirty_write_count = m_inflight_page_to_dirty_write_count[phys_page];
                        dirty_write_count += 1;
                        // if (std::find(m_inflight_page_to_dirty_write_count.begin(), m_inflight_page_to_dirty_write_count.end(), phys_page) != m_inflight_page_to_dirty_write_count.end()) {
                        //     m_inflight_page_to_dirty_write_count[phys_page] = dirty_write_count;
                        // } else {
                        //     m_inflight_page_to_dirty_write_count.insert(phys_page, dirty_write_count);
                        // }
                        m_inflight_page_to_dirty_write_count[phys_page] = dirty_write_count;

                        m_dirty_write_buffer_size += 1;
                    }

                    SubsecondTime add_cacheline_hw_access_latency = m_dram_hardware_cntlr.getDramAccessCost(t_now, pkt_size, requester, address, perf, true, false, false);
                    m_total_remote_dram_hardware_latency_cachelines += add_cacheline_hw_access_latency;
                    m_total_remote_dram_hardware_latency_cachelines_count++;

                    UInt32 size = pkt_size;  // store the compressed size of the cacheline (unmodified when compression is off)
                    SubsecondTime cacheline_compression_latency = SubsecondTime::Zero();  // when cacheline compression is not enabled, this is always 0
                    if (m_use_compression) {
                        if (m_r_cacheline_gran) {
                            m_compression_controller.m_compression_model->update_bandwidth_utilization(m_data_movement->getCachelineQueueUtilizationPercentage(t_now));
                            cacheline_compression_latency = m_compression_controller.compress(false, phys_page, m_cache_line_size, &size);
                        } else if (m_use_cacheline_compression) {
                            m_compression_controller.m_cacheline_compression_model->update_bandwidth_utilization(m_data_movement->getCachelineQueueUtilizationPercentage(t_now));
                            cacheline_compression_latency = m_compression_controller.compress(true, phys_page, m_cache_line_size, &size);
                        }
                    }
                    // For clearer code logic, calculate decompression latency (but not adding it to anything) before computing the queue delay
                    SubsecondTime cacheline_decompression_latency = SubsecondTime::Zero();
                    // TODO: Currently model decompression by adding decompression latency to inflight page time
                    if (m_use_compression && (m_r_cacheline_gran || m_use_cacheline_compression)) {
                        cacheline_decompression_latency = m_compression_controller.decompress(!m_r_cacheline_gran, phys_page);
                    }

                    // Network transmission cost
                    SubsecondTime cacheline_network_processing_time = m_r_cacheline_bandwidth.getRoundedLatency(8*size);
                    
                    SubsecondTime add_cacheline_request_time = t_remote_queue_request + add_cacheline_hw_access_latency + cacheline_compression_latency;  // cacheline_compression_latency is 0 if compression not enabled
                    bool make_add_cacheline_request = true;
                    // Main difference when m_r_throttle_redundant_moves is true: reduce traffic sent through cacheline queue
                    if (m_r_throttle_redundant_moves) {
                        // Don't request cacheline via the cacheline queue if the inflight page arrives sooner
                        SubsecondTime datamov_delay = getPartitionQueueDelayNoEffect(add_cacheline_request_time, size, QueueModel::CACHELINE, requester);
                        datamov_delay += cacheline_network_processing_time + cacheline_decompression_latency;  // decompression latency is 0 if not using cacheline compression
                        if (add_cacheline_request_time + datamov_delay - pkt_time >= access_latency) {
                            make_add_cacheline_request = false;
                            ++m_redundant_moves_type2_slower_than_page_arrival;
                        }
                    } 
                    if (make_add_cacheline_request) {
                        SubsecondTime datamov_delay;
                        if (m_r_partition_queues == 3) {
                            std::vector<std::pair<UInt64, SubsecondTime>> updated_inflight_page_arrival_time_deltas;
                            datamov_delay = m_data_movement->computeQueueDelayTrackBytesPotentialPushback(add_cacheline_request_time, m_r_cacheline_bandwidth.getRoundedLatency(8*size), size, QueueModel::CACHELINE, updated_inflight_page_arrival_time_deltas, true, requester);
                            for (auto it = updated_inflight_page_arrival_time_deltas.begin(); it != updated_inflight_page_arrival_time_deltas.end(); ++it) {
                                if (m_inflight_pages.count(it->first) && it->second > SubsecondTime::Zero()) {
                                    m_inflight_pages_delay_time += it->second;
                                    m_inflight_pages[it->first] += it->second;  // update arrival time if it's still an inflight page
                                    ++m_inflight_page_delayed;
                                }
                            }
                        } else if (m_r_partition_queues == 2 || m_r_partition_queues == 4) {
                            datamov_delay = getPartitionQueueDelayTrackBytes(add_cacheline_request_time, size, QueueModel::CACHELINE, requester);
                        }
                        datamov_delay += cacheline_network_processing_time + cacheline_decompression_latency;  // decompression latency is 0 if not using cacheline compression
                        ++m_redundant_moves;
                        ++m_redundant_moves_type2;
                        --m_num_recent_local_accesses;
                        ++m_num_recent_remote_additional_accesses;  // this is now an additional remote access
                        m_inflight_redundant[phys_page] += 1;
                        SubsecondTime new_arrival_time = add_cacheline_request_time + datamov_delay;
                        if (new_arrival_time - pkt_time < access_latency) {
                            m_redundant_moves_type2_time_savings += access_latency - (new_arrival_time - pkt_time);
                            access_latency = new_arrival_time - pkt_time;
                        }

                        if (m_track_inflight_cachelines) {
                            addInflightCacheline(cacheline, new_arrival_time, access_type);
                        }
                    }
                } else {
                    ++m_redundant_moves_type2_cancelled_limit_redundant_moves;

                    m_pages_cacheline_request_limit_exceeded.insert(phys_page);
                    if (m_auto_turn_off_partition_queues && cacheline_queue_utilization_percentage > m_turn_off_pq_cacheline_queue_utilization_threshold && m_pages_cacheline_request_limit_exceeded.size() > m_cancel_pq_inflight_buffer_threshold * (m_inflight_pages.size() + m_inflight_pages_extra.size())) {
                        m_r_partition_queues = 0;
                        std::cout << "Partition queues turned off due to >= type 2 redundant moves limit of " << m_r_redundant_moves_limit << " at " << m_num_accesses << " accesses" << std::endl;
                    }
                }
            }
        }
        m_total_local_access_latency += access_latency;
        m_total_access_latency += access_latency;

        if (access_latency < m_access_latency_outlier_threshold) {
            m_total_access_latency_no_outlier += access_latency;
            m_total_local_access_latency_no_outlier += access_latency;
        } else {
            m_access_latency_outlier_count += 1;
            m_local_access_latency_outlier_count += 1;
        }

        return access_latency;
    }
}

bool
DramPerfModelDisagg::isRemoteAccess(IntPtr address, core_id_t requester, DramCntlrInterface::access_t access_type) 
{
    UInt64 num_local_pages = m_localdram_size / m_page_size;
    if (m_r_cacheline_gran) // When we perform moves at cacheline granularity (should be disabled by default)
        num_local_pages = m_localdram_size / m_cache_line_size;

    UInt64 phys_page = address & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
    if (m_r_cacheline_gran) 
        phys_page = address & ~((UInt64(1) << floorLog2(m_cache_line_size)) - 1);

    if (m_r_mode == 0 || m_r_mode == 4) {  // Static partitioning: no data movement and m_r_partitioning_ratio decides how many go where
        if (m_local_pages.find(phys_page))
            return false;
        else if (m_remote_pages.count(phys_page))
            return true;
        else if ( (unsigned int)(rand() % 100) < m_r_partitioning_ratio) {
            m_local_pages.push_back(phys_page);
            return false;
        } 
        else {
            m_remote_pages.insert(phys_page);
            return true; 
        }
    }
    else if (m_r_mode == 1 || m_r_mode == 2 || m_r_mode == 3 || m_r_mode == 5) {  // local DRAM as a cache 
        if (m_local_pages.find(phys_page)) {  // Is it in local DRAM?
            m_local_pages.remove(phys_page);  // LRU
            m_local_pages.push_back(phys_page);
            if (access_type == DramCntlrInterface::WRITE) {
                m_dirty_pages.insert(phys_page);  // for unordered_set, the element is only inserted if it's not already in the container
            }
            return false;
        }
        else if (m_remote_pages.count(phys_page)) {
            if (m_use_throttled_pages_tracker && m_use_ideal_page_throttling && m_throttled_pages_tracker.count(phys_page)) {
                // This is a previously throttled page
                if (m_moved_pages_no_access_yet.size() > 0) {
                    UInt64 other_page = m_moved_pages_no_access_yet.front();  // for simplicity, choose first element
                    m_moved_pages_no_access_yet.pop_front();
                    // Do swap: mimic procedure for evicting other_page and replacing it with phys_page
                    // other_page hasn't been accessed yet so no need to check if it's dirty
                    m_local_pages.remove(other_page);
                    // if (!m_speed_up_simulation)
                    //     m_local_pages_remote_origin.erase(other_page);
                    if (std::find(m_remote_pages.begin(), m_remote_pages.end(), other_page) == m_remote_pages.end()) {
                        m_remote_pages.insert(other_page);  // other_page is not in remote_pages, add it back
                    }

                    m_local_pages.push_back(phys_page);
                    // if (!m_speed_up_simulation)
                    //     m_local_pages_remote_origin[phys_page] = 1;
                    if (m_r_exclusive_cache) {
                        m_remote_pages.erase(phys_page);
                    }
                    
                    auto it = m_inflight_pages.find(other_page);
                    if (it != m_inflight_pages.end()) {  // the other page was an inflight page
                        // m_inflight_pages.erase(phys_page);
                        m_data_movement->removeInflightPage(phys_page);  // TODO: replace with call that updates the map within queue model
                        m_inflight_pages[phys_page] = it->second;  // use the other page's arrival time
                        m_inflight_redundant[phys_page] = 0;

                        m_inflight_pages.erase(other_page);
                        m_data_movement->removeInflightPage(other_page);
                        m_inflight_redundant.erase(other_page);
                        ++m_ideal_page_throttling_swaps_inflight;
                    } else {
                        // For now, don't need to add this page to inflight pages
                        ++m_ideal_page_throttling_swaps_non_inflight;
                    }
                    return false;  // After swap, this is now a local access
                } else {
                    ++m_ideal_page_throttling_swap_unavailable;
                }
            }
            return true;
        }
        else {
            if (m_remote_init) {  // Assuming all pages start off in remote memory
                m_remote_pages.insert(phys_page); 
                return true;
            } else {
                if (m_local_pages.size() < num_local_pages) {
                    m_local_pages.push_back(phys_page);
                    return false; 
                } 
                else {
                    m_remote_pages.insert(phys_page); 
                    return true;

                }
            }
        }  
    }
    return false;
}

SubsecondTime 
DramPerfModelDisagg::possiblyEvict(UInt64 phys_page, SubsecondTime t_now, core_id_t requester) 
{
    // Important note: phys_page is the current physical page being accessed before the call to this function,
    // NOT the page to be evicted!
    // This function can only evict one page per function call
    SubsecondTime sw_overhead = SubsecondTime::Zero();
    SubsecondTime evict_compression_latency = SubsecondTime::Zero();
    UInt64 evicted_page; 

    UInt64 num_local_pages = m_localdram_size/m_page_size;
    if (m_r_cacheline_gran)
        num_local_pages = m_localdram_size/m_cache_line_size;
        
    SubsecondTime page_network_processing_time = SubsecondTime::Zero();

    QueueModel::request_t queue_request_type = m_r_cacheline_gran ? QueueModel::CACHELINE : QueueModel::PAGE;
    SubsecondTime t_remote_queue_request = t_now;  // Use this instead of incrementing t_now throughout, if need to send page requests in parallel
    if (m_local_pages.size() > num_local_pages) {
        bool found = false;

        if (m_r_dontevictdirty) {
            auto i = m_local_pages.begin();
            for(unsigned int k = 0; k < m_local_pages.size()/2; ++i, ++k) {
                if (!m_dirty_pages.count(*i)) {
                    // This is a non-dirty page
                    found = true;
                    evicted_page = *i; 
                    break;
                }
            }	
            // If a non-dirty page is found, just remove this page to make space
            if (found) {
                m_local_pages.remove(evicted_page);
                // if (!m_speed_up_simulation)
                //     m_local_pages_remote_origin.erase(evicted_page);
            }
        }

        // If found==false, remove the first page
        if (!found) {
            evicted_page = m_local_pages.front();  // Evict the least recently used page
            m_local_pages.pop_front();
            // if (!m_speed_up_simulation)
            //     m_local_pages_remote_origin.erase(evicted_page);
        }
        ++m_local_evictions; 

        if (m_r_simulate_sw_pagereclaim_overhead) 
            sw_overhead = SubsecondTime::NS() * 30000; 		

        if (m_dirty_pages.count(evicted_page)) {
            // The page to evict is dirty
            ++m_page_moves;
            ++m_writeback_pages;

            // Compress
            UInt32 size = m_r_cacheline_gran ? m_cache_line_size : m_page_size;  // store the compressed size of the page (unmodified when compression is off)
            if (m_use_compression) {
                m_compression_controller.m_compression_model->update_bandwidth_utilization(m_data_movement->getPageQueueUtilizationPercentage(t_now));
                evict_compression_latency += m_compression_controller.compress(false, evicted_page, size, &size);
            }

            SubsecondTime page_datamovement_delay = SubsecondTime::Zero();
            if (m_r_simulate_datamov_overhead) { 
                page_datamovement_delay = getPartitionQueueDelayTrackBytes(t_remote_queue_request + evict_compression_latency, size, queue_request_type, requester);
            }

            // TODO: Currently model decompression by adding decompression latency to inflight page time
            if (m_use_compression) {
                page_datamovement_delay += m_compression_controller.decompress(false, evicted_page);
            }

            if (!m_remote_pages.count(evicted_page)) {
                // The page to evict is not in remote_pages
                m_remote_pages.insert(evicted_page);
            }

            // Compute network transmission delay
            if (m_r_partition_queues > 0)
                page_network_processing_time = m_r_page_bandwidth.getRoundedLatency(8*size);
            else
                page_network_processing_time = m_r_bus_bandwidth.getRoundedLatency(8*size);

            m_inflightevicted_pages[evicted_page] = t_remote_queue_request + evict_compression_latency + page_datamovement_delay + page_network_processing_time;
            if (m_inflightevicted_pages.size() > m_max_inflightevicted_bufferspace)
                m_max_inflightevicted_bufferspace++;
            if (m_inflight_pages.size() + m_inflightevicted_pages.size() > m_max_total_bufferspace)
                m_max_total_bufferspace++;  // update stat

        } else if (!m_remote_pages.count(evicted_page)) {
            // The page to evict is not dirty and not in remote memory
            m_remote_pages.insert(evicted_page);
            ++m_page_moves;

            // Compress
            UInt32 size = m_r_cacheline_gran ? m_cache_line_size : m_page_size;  // store the compressed size of the page (unmodified when compression is off)
            if (m_use_compression) {
                m_compression_controller.m_compression_model->update_bandwidth_utilization(m_data_movement->getPageQueueUtilizationPercentage(t_now));
                evict_compression_latency += m_compression_controller.compress(false, evicted_page, size, &size);
            }

            SubsecondTime page_datamovement_delay = SubsecondTime::Zero();
            if (m_r_simulate_datamov_overhead) {
                page_datamovement_delay = getPartitionQueueDelayTrackBytes(t_remote_queue_request + evict_compression_latency, size, queue_request_type, requester);
            }

            // TODO: Currently model decompression by adding decompression latency to inflight page time
            if (m_use_compression) {
                page_datamovement_delay += m_compression_controller.decompress(false, evicted_page);
            }

            // Compute network transmission delay
            if (m_r_partition_queues > 0)
                page_network_processing_time = m_r_page_bandwidth.getRoundedLatency(8*size);
            else
                page_network_processing_time = m_r_bus_bandwidth.getRoundedLatency(8*size);

            m_inflightevicted_pages[evicted_page] = t_remote_queue_request + evict_compression_latency + page_datamovement_delay + page_network_processing_time;
            if (m_inflightevicted_pages.size() > m_max_inflightevicted_bufferspace)
                m_max_inflightevicted_bufferspace++;
            if (m_inflight_pages.size() + m_inflightevicted_pages.size() > m_max_total_bufferspace)
                m_max_total_bufferspace++;  // update stat
        }

        m_dirty_pages.erase(evicted_page);
    }
    // return sw_overhead + evict_compression_latency;
    return sw_overhead;  // latencies that are on the critical path
}


void 
DramPerfModelDisagg::possiblyPrefetch(UInt64 phys_page, SubsecondTime t_now, core_id_t requester) 
{
    // Important note: phys_page is the current physical page being accessed before the call to this function,
    // NOT the page to be prefetched!
    if (!m_r_enable_nl_prefetcher) {
        return;
    }
    QueueModel::request_t queue_request_type = m_r_cacheline_gran ? QueueModel::CACHELINE : QueueModel::PAGE;
    SubsecondTime t_remote_queue_request = t_now;  // Use this instead of incrementing t_now throughout, to mimic sending page requests in parallel
    std::vector<UInt64> prefetch_page_candidates;
    m_prefetcher_model->pagePrefetchCandidates(phys_page, prefetch_page_candidates);
    for (auto it = prefetch_page_candidates.begin(); it != prefetch_page_candidates.end(); ++it) {
        if (m_data_movement->getPageQueueUtilizationPercentage(t_now) > m_r_page_queue_utilization_threshold) {
            // Cancel moving pages if the queue used for moving pages is already full
            ++m_prefetch_page_not_done_datamovement_queue_full;
            continue;  // could return here, but continue the loop to update stats for when prefetching was not done
        }
        UInt64 pref_page = *it;
        if (m_local_pages.find(pref_page)) {
            ++m_prefetch_page_not_done_page_local_already;  // page already in m_local_pages
            continue;
        }
        if (!m_remote_pages.count(pref_page)) {
            if (m_prefetch_unencountered_pages) {
                m_remote_pages.insert(pref_page);  // hack for this page to be prefetched
            } else {
                ++m_prefetch_page_not_done_page_not_initialized;  // page not in m_remote_pages, means it's uninitialized? or just not seen yet by the system?
                continue;
            }
        }
        // pref_page is not in local_pages but in remote_pages, can prefetch
        ++m_page_prefetches;
        ++m_page_moves;

        SubsecondTime page_network_processing_time = SubsecondTime::Zero();

        // TODO: enable Hardware DRAM access cost for prefetched pages; need way to find ddr address from phys_page?
        // SubsecondTime page_hw_access_latency = m_dram_hardware_cntlr.getDramAccessCost(t_remote_queue_request, m_page_size, requester, address, perf, true, false, true);

        // Compress
        UInt32 size = m_r_cacheline_gran ? m_cache_line_size : m_page_size;  // store the compressed size of the page (unmodified when compression is off)
        SubsecondTime page_compression_latency = SubsecondTime::Zero();  // when page compression is not enabled, this is always 0
        if (m_use_compression) {
            if (m_use_r_compressed_pages && m_compression_controller.address_to_compressed_size.find(phys_page) != m_compression_controller.address_to_compressed_size.end()) {
                size = m_compression_controller.address_to_compressed_size[phys_page];
            } else {
                m_compression_controller.m_compression_model->update_bandwidth_utilization(m_data_movement->getPageQueueUtilizationPercentage(t_now));
                page_compression_latency = m_compression_controller.compress(false, pref_page, size, &size);
            }
        }

        SubsecondTime page_datamovement_delay = SubsecondTime::Zero();
        if (m_r_simulate_datamov_overhead) {
            if (m_r_partition_queues == 3) {
                page_datamovement_delay = m_data_movement->computeQueueDelayTrackBytes(t_remote_queue_request + page_compression_latency, m_r_page_bandwidth.getRoundedLatency(8*size), size, queue_request_type, requester, true, pref_page);
            } else {
                page_datamovement_delay = getPartitionQueueDelayTrackBytes(t_remote_queue_request + page_compression_latency, size, queue_request_type, requester);
            }
        }

        // Compute network transmission delay
        if (m_r_partition_queues > 0)
            page_network_processing_time = m_r_page_bandwidth.getRoundedLatency(8*size);
        else
            page_network_processing_time = m_r_bus_bandwidth.getRoundedLatency(8*size);

        // TODO: Currently model decompression by adding decompression latency to inflight page time
        if (m_use_compression) {
            page_datamovement_delay += m_compression_controller.decompress(false, pref_page);
        }

        // Commenting out since earlier in this loop, these checks were already made
        // assert(!m_local_pages.find(pref_page)); 
        // assert(m_remote_pages.count(pref_page)); 
        m_local_pages.push_back(pref_page);
        if (m_r_exclusive_cache)
            m_remote_pages.erase(pref_page);
        // if (!m_speed_up_simulation)
        //     m_local_pages_remote_origin[pref_page] = 1;
        m_inflight_pages[pref_page] = t_remote_queue_request + page_compression_latency + page_datamovement_delay + page_network_processing_time;  // use max of this time with Sim()->getClockSkewMinimizationServer()->getGlobalTime() here as well?
        m_inflight_redundant[pref_page] = 0; 
        if (m_inflight_pages.size() > m_max_inflight_bufferspace)
            m_max_inflight_bufferspace++;
        if (m_inflight_pages.size() + m_inflightevicted_pages.size() > m_max_total_bufferspace)
            m_max_total_bufferspace++;  // update stat
        possiblyEvict(phys_page, t_remote_queue_request, requester);
    }
}

SubsecondTime
DramPerfModelDisagg::getDataMovementBandwidthProcessingTime(UInt64 num_bytes, QueueModel::request_t queue_request_type)
{
    SubsecondTime processing_time;
    if (m_r_partition_queues == 3 || m_r_partition_queues == 4) {
        if (queue_request_type == QueueModel::PAGE)
            processing_time = m_r_page_bandwidth.getRoundedLatency(8*num_bytes);       // Page queue bandwidth
        else  // queue_request_type == QueueModel::CACHELINE
            processing_time = m_r_cacheline_bandwidth.getRoundedLatency(8*num_bytes);  // Cacheline queue bandwidth
    }
    else {
        processing_time = m_r_bus_bandwidth.getRoundedLatency(8*num_bytes);            // Combined queue bandwidth
    }
    return processing_time;
}

SubsecondTime
DramPerfModelDisagg::getPartitionQueueDelayTrackBytes(SubsecondTime pkt_time, UInt64 num_bytes, QueueModel::request_t queue_request_type, core_id_t requester)
{
    SubsecondTime processing_time = getDataMovementBandwidthProcessingTime(num_bytes, queue_request_type);
    SubsecondTime queue_delay = m_data_movement->computeQueueDelayTrackBytes(pkt_time, processing_time, num_bytes, queue_request_type, requester);
    return queue_delay;
}

SubsecondTime
DramPerfModelDisagg::getPartitionQueueDelayNoEffect(SubsecondTime pkt_time, UInt64 num_bytes, QueueModel::request_t queue_request_type, core_id_t requester)
{
    SubsecondTime processing_time = getDataMovementBandwidthProcessingTime(num_bytes, queue_request_type);
    SubsecondTime queue_delay = m_data_movement->computeQueueDelayNoEffect(pkt_time, processing_time, queue_request_type, requester);
    return queue_delay;
}

void
DramPerfModelDisagg::addInflightCacheline(UInt64 cacheline, SubsecondTime arrival_time, DramCntlrInterface::access_t access_type)
{
    // Track inflight cachelines
    if (access_type == DramCntlrInterface::READ && m_inflight_cachelines_reads.find(cacheline) == m_inflight_cachelines_reads.end()) {
        // The current cacheline is not in inflight cachelines
        m_inflight_cachelines_reads.insert(std::pair<UInt64, SubsecondTime>(cacheline, arrival_time));
        if (m_inflight_cachelines_reads.size() > m_max_inflight_cachelines_reads)
            m_max_inflight_cachelines_reads++;
        if (m_inflight_cachelines_reads.size() + m_inflight_cachelines_writes.size() > m_max_inflight_cachelines_total)
            m_max_inflight_cachelines_total++;
    } else if (access_type == DramCntlrInterface::WRITE) {
        m_inflight_cachelines_writes.insert(std::pair<UInt64, SubsecondTime>(cacheline, arrival_time));
        if (m_inflight_cachelines_writes.size() > m_max_inflight_cachelines_writes)
            m_max_inflight_cachelines_writes++;
        if (m_inflight_cachelines_reads.size() + m_inflight_cachelines_writes.size() > m_max_inflight_cachelines_total)
            m_max_inflight_cachelines_total++;
    }
}