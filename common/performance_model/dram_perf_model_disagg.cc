#include "dram_perf_model_disagg.h"
#include "simulator.h"
#include "config.h"
#include "config.hpp"
#include "stats.h"
#include "shmem_perf.h"
#include "address_home_lookup.h"
#include "utils.h"

DramPerfModelDisagg::DramPerfModelDisagg(core_id_t core_id, UInt32 cache_block_size, AddressHomeLookup* address_home_lookup)
    : DramPerfModel(core_id, cache_block_size)
    , m_core_id(core_id)
    , m_address_home_lookup(address_home_lookup)
    , m_num_banks           (Sim()->getCfg()->getInt("perf_model/dram/ddr/num_banks"))
    , m_num_banks_log2      (floorLog2(m_num_banks))
    , m_num_bank_groups     (Sim()->getCfg()->getInt("perf_model/dram/ddr/num_bank_groups"))
    , m_num_ranks           (Sim()->getCfg()->getInt("perf_model/dram/ddr/num_ranks"))
    , m_rank_offset         (Sim()->getCfg()->getInt("perf_model/dram/ddr/rank_offset"))
    , m_num_channels        (Sim()->getCfg()->getInt("perf_model/dram/ddr/num_channels"))
    , m_channel_offset      (Sim()->getCfg()->getInt("perf_model/dram/ddr/channel_offset"))
    , m_home_lookup_bit     (Sim()->getCfg()->getInt("perf_model/dram_directory/home_lookup_param"))
    , m_total_ranks         (m_num_ranks * m_num_channels)
    , m_banks_per_channel   (m_num_banks * m_num_ranks)
    , m_banks_per_bank_group (m_num_banks / m_num_bank_groups)
    , m_total_banks         (m_banks_per_channel * m_num_channels)
    , m_total_bank_groups   (m_num_bank_groups * m_num_ranks * m_num_channels)
    , m_data_bus_width      (Sim()->getCfg()->getInt("perf_model/dram/ddr/data_bus_width"))   // In bits
    , m_dram_speed          (Sim()->getCfg()->getInt("perf_model/dram/ddr/dram_speed"))       // In MHz
    , m_dram_page_size      (Sim()->getCfg()->getInt("perf_model/dram/ddr/dram_page_size"))
    , m_dram_page_size_log2 (floorLog2(m_dram_page_size))
    , m_open_page_mapping   (Sim()->getCfg()->getBool("perf_model/dram/ddr/open_page_mapping"))
    , m_column_offset       (Sim()->getCfg()->getInt("perf_model/dram/ddr/column_offset"))
    , m_column_hi_offset    (m_dram_page_size_log2 - m_column_offset + m_num_banks_log2) // Offset for higher order column bits
    , m_bank_offset         (m_dram_page_size_log2 - m_column_offset) // Offset for bank bits
    , m_randomize_address   (Sim()->getCfg()->getBool("perf_model/dram/ddr/randomize_address"))
    , m_randomize_offset    (Sim()->getCfg()->getInt("perf_model/dram/ddr/randomize_offset"))
    , m_column_bits_shift   (Sim()->getCfg()->getInt("perf_model/dram/ddr/column_bits_shift"))
    , m_bus_bandwidth       (m_dram_speed * m_data_bus_width / 1000) // In bits/ns: MT/s=transfers/us * bits/transfer
    , m_r_bus_bandwidth     (m_dram_speed * m_data_bus_width / (1000 * Sim()->getCfg()->getFloat("perf_model/dram/remote_mem_bw_scalefactor"))) // Remote memory
    , m_r_part_bandwidth    (m_dram_speed * m_data_bus_width / (1000 * Sim()->getCfg()->getFloat("perf_model/dram/remote_mem_bw_scalefactor") / (1 - Sim()->getCfg()->getFloat("perf_model/dram/remote_cacheline_queue_fraction")))) // Remote memory - Partitioned Queues => Page Queue
    , m_r_part2_bandwidth   (m_dram_speed * m_data_bus_width / (1000 * Sim()->getCfg()->getFloat("perf_model/dram/remote_mem_bw_scalefactor") / Sim()->getCfg()->getFloat("perf_model/dram/remote_cacheline_queue_fraction"))) // Remote memory - Partitioned Queues => Cacheline Queue
    , m_bank_keep_open      (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/bank_keep_open")))
    , m_bank_open_delay     (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/bank_open_delay")))
    , m_bank_close_delay    (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/bank_close_delay")))
    , m_dram_access_cost    (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/access_cost")))
    , m_intercommand_delay  (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/intercommand_delay"))) // Rank availability
    , m_intercommand_delay_short  (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/intercommand_delay_short"))) // Rank availability
    , m_intercommand_delay_long  (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/intercommand_delay_long"))) // Bank group availability
    , m_controller_delay    (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/controller_delay"))) // Average pipeline delay for various DDR controller stages
    , m_refresh_interval    (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/refresh_interval"))) // tREFI
    , m_refresh_length      (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/refresh_length"))) // tRFC
    , m_r_added_latency       (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/remote_mem_add_lat"))) // Network latency for remote DRAM access 
    , m_r_datamov_threshold       (Sim()->getCfg()->getInt("perf_model/dram/remote_datamov_threshold"))// Move data if greater than
    , m_cache_line_size     (cache_block_size)
    , m_page_size        (Sim()->getCfg()->getInt("perf_model/dram/page_size"))  // Memory page size (bytes) in disagg.cc used for page movement (different from ddr page size)
    , m_localdram_size       (Sim()->getCfg()->getInt("perf_model/dram/localdram_size")) // Local DRAM size
    , m_enable_remote_mem       (Sim()->getCfg()->getBool("perf_model/dram/enable_remote_mem")) // Enable remote memory simulation
    , m_r_simulate_tlb_overhead       (Sim()->getCfg()->getBool("perf_model/dram/simulate_tlb_overhead")) // Simulate TLB overhead
    , m_r_simulate_datamov_overhead       (Sim()->getCfg()->getBool("perf_model/dram/simulate_datamov_overhead"))  // Simulate datamovement overhead for remote DRAM (default: true)
    , m_r_mode       (Sim()->getCfg()->getInt("perf_model/dram/remote_memory_mode")) // Various modes for Local DRAM usage
    , m_r_partitioning_ratio       (Sim()->getCfg()->getInt("perf_model/dram/remote_partitioning_ratio"))// Move data if greater than
    , m_r_simulate_sw_pagereclaim_overhead       (Sim()->getCfg()->getBool("perf_model/dram/simulate_sw_pagereclaim_overhead"))// Add 2600usec delay
    , m_r_exclusive_cache       (Sim()->getCfg()->getBool("perf_model/dram/remote_exclusive_cache"))
    , m_remote_init       (Sim()->getCfg()->getBool("perf_model/dram/remote_init")) // If true, all pages are initially allocated to remote memory
    , m_r_enable_nl_prefetcher       (Sim()->getCfg()->getBool("perf_model/dram/enable_remote_prefetcher")) // Enable prefetcher to prefetch pages from remote DRAM to local DRAM
    , m_r_disturbance_factor      (Sim()->getCfg()->getInt("perf_model/dram/remote_disturbance_factor")) // Other systems using the remote memory and creating disturbance
    , m_r_dontevictdirty      (Sim()->getCfg()->getBool("perf_model/dram/remote_dontevictdirty")) // Do not evict dirty pages
    , m_r_enable_selective_moves      (Sim()->getCfg()->getBool("perf_model/dram/remote_enable_selective_moves"))
    , m_r_partition_queues     (Sim()->getCfg()->getInt("perf_model/dram/remote_partitioned_queues")) // Enable partitioned queues
    , m_r_cacheline_queue_fraction    (Sim()->getCfg()->getFloat("perf_model/dram/remote_cacheline_queue_fraction")) // The fraction of remote bandwidth used for the cacheline queue (decimal between 0 and 1)
    , m_r_cacheline_gran      (Sim()->getCfg()->getBool("perf_model/dram/remote_use_cacheline_granularity")) // Move data and operate in cacheline granularity
    , m_r_reserved_bufferspace      (Sim()->getCfg()->getInt("perf_model/dram/remote_reserved_buffer_space")) // Max % of local DRAM that can be reserved for pages in transit
    , m_r_limit_redundant_moves      (Sim()->getCfg()->getInt("perf_model/dram/remote_limit_redundant_moves"))
    , m_r_throttle_redundant_moves      (Sim()->getCfg()->getBool("perf_model/dram/remote_throttle_redundant_moves"))
    , m_r_use_separate_queue_model      (Sim()->getCfg()->getBool("perf_model/dram/queue_model/use_separate_remote_queue_model")) // Whether to use the separate remote queue model
    , m_banks               (m_total_banks)
    , m_r_banks               (m_total_banks)
    , m_dram_page_hits           (0)
    , m_dram_page_empty          (0)
    , m_dram_page_closing        (0)
    , m_dram_page_misses         (0)
    , m_remote_reads        (0)
    , m_remote_writes       (0)
    , m_page_moves          (0)
    , m_page_prefetches     (0)
    , m_inflight_hits       (0)
    , m_writeback_pages     (0)
    , m_local_evictions     (0)
    , m_extra_pages         (0)
    , m_redundant_moves     (0)
    , m_max_bufferspace     (0)
    , m_move_page_cancelled_bufferspace_full(0)
    , m_move_page_cancelled_datamovement_queue_full(0)
    , m_unique_pages_accessed      (0)
    , m_total_queueing_delay(SubsecondTime::Zero())
    , m_total_local_access_latency(SubsecondTime::Zero())
    , m_total_remote_access_latency(SubsecondTime::Zero())
{
    String name("dram"); 
    if (Sim()->getCfg()->getBool("perf_model/dram/queue_model/enabled"))
    {
        for(UInt32 channel = 0; channel < m_num_channels; ++channel) {
            m_queue_model.push_back(QueueModel::create(
                        name + "-queue-" + itostr(channel), core_id, Sim()->getCfg()->getString("perf_model/dram/queue_model/type"),
                        m_bus_bandwidth.getRoundedLatency(8))); // bytes to bits
            m_r_queue_model.push_back(QueueModel::create(
                        name + "-remote-queue-" + itostr(channel), core_id, Sim()->getCfg()->getString("perf_model/dram/queue_model/type"),
                        m_bus_bandwidth.getRoundedLatency(8))); // bytes to bits
        } 
    }

    String data_movement_queue_model_type;
    if (m_r_use_separate_queue_model) {
        data_movement_queue_model_type = Sim()->getCfg()->getString("perf_model/dram/queue_model/remote_queue_model_type");
    } else {
        data_movement_queue_model_type = Sim()->getCfg()->getString("perf_model/dram/queue_model/type");
    }
    if(m_r_partition_queues == 1) {
        m_data_movement = QueueModel::create(
                name + "-datamovement-queue", core_id, data_movement_queue_model_type,
                m_r_part_bandwidth.getRoundedLatency(8), m_r_part_bandwidth.getBandwidthBitsPerUs()); // bytes to bits
        m_data_movement_2 = QueueModel::create(
                name + "-datamovement-queue-2", core_id, data_movement_queue_model_type,
                m_r_part2_bandwidth.getRoundedLatency(8), m_r_part2_bandwidth.getBandwidthBitsPerUs()); // bytes to bits
    } else {
        m_data_movement = QueueModel::create(
                name + "-datamovement-queue", core_id, data_movement_queue_model_type,
                m_r_bus_bandwidth.getRoundedLatency(8), m_r_bus_bandwidth.getBandwidthBitsPerUs()); // bytes to bits
        // Note: currently m_data_movement_2 is not used anywhere when m_r_partition_queues != 1
        m_data_movement_2 = QueueModel::create(
                name + "-datamovement-queue-2", core_id, data_movement_queue_model_type,
                m_r_bus_bandwidth.getRoundedLatency(8), m_r_bus_bandwidth.getBandwidthBitsPerUs()); // bytes to bits	
    }

    for(UInt32 rank = 0; rank < m_total_ranks; ++rank) {
        m_rank_avail.push_back(QueueModel::create(
                    name + "-rank-" + itostr(rank), core_id, "history_list",
                    (m_num_bank_groups > 1) ? m_intercommand_delay_short : m_intercommand_delay));
        m_r_rank_avail.push_back(QueueModel::create(
                    name + "-remote-rank-" + itostr(rank), core_id, "history_list",
                    (m_num_bank_groups > 1) ? m_intercommand_delay_short : m_intercommand_delay));
    }

    for(UInt32 group = 0; group < m_total_bank_groups; ++group) {
        m_bank_group_avail.push_back(QueueModel::create(
                    name + "-bank-group-" + itostr(group), core_id, "history_list",
                    m_intercommand_delay_long));
        m_r_bank_group_avail.push_back(QueueModel::create(
                    name + "-remote-bank-group-" + itostr(group), core_id, "history_list",
                    m_intercommand_delay_long));
    }

    // Compression
    m_use_compression = Sim()->getCfg()->getBool("perf_model/dram/compression_model/use_compression");
    if (m_use_compression) {
        String compression_scheme = Sim()->getCfg()->getString("perf_model/dram/compression_model/compression_scheme");
        UInt32 gran_size = m_r_cacheline_gran ? m_cache_line_size : m_page_size;
        m_compression_model = CompressionModel::create("Link Compression Model", gran_size, m_cache_line_size, compression_scheme);
        registerStatsMetric("compression", core_id, "bytes-saved", &bytes_saved);
        registerStatsMetric("compression", core_id, "sum-compression-ratio", &m_sum_compression_ratio);
        registerStatsMetric("compression", core_id, "total-compression-latency", &m_total_compression_latency);
        registerStatsMetric("compression", core_id, "total-decompression-latency", &m_total_decompression_latency);
    }

    LOG_ASSERT_ERROR(cache_block_size == 64, "Hardcoded for 64-byte cache lines");
    LOG_ASSERT_ERROR(m_column_offset <= m_dram_page_size_log2, "Column offset exceeds bounds!");
    if(m_randomize_address)
        LOG_ASSERT_ERROR(m_num_bank_groups == 4 || m_num_bank_groups == 8, "Number of bank groups incorrect for address randomization!");
    // Probably m_page_size needs to be < or <= 2^32 bytes
    LOG_ASSERT_ERROR(m_page_size > 0 && isPower2(m_page_size), "page_size must be a positive power of 2");

    registerStatsMetric("ddr", core_id, "page-hits", &m_dram_page_hits);
    registerStatsMetric("ddr", core_id, "page-empty", &m_dram_page_empty);
    registerStatsMetric("ddr", core_id, "page-closing", &m_dram_page_closing);
    registerStatsMetric("ddr", core_id, "page-misses", &m_dram_page_misses);
    registerStatsMetric("dram", core_id, "total-access-latency", &m_total_access_latency); // cgiannoula
    registerStatsMetric("dram", core_id, "total-local-access-latency", &m_total_local_access_latency);
    registerStatsMetric("dram", core_id, "total-remote-access-latency", &m_total_remote_access_latency);
    registerStatsMetric("dram", core_id, "remote-reads", &m_remote_reads);
    registerStatsMetric("dram", core_id, "remote-writes", &m_remote_writes);
    registerStatsMetric("dram", core_id, "data-moves", &m_page_moves);
    registerStatsMetric("dram", core_id, "page-prefetches", &m_page_prefetches);
    registerStatsMetric("dram", core_id, "inflight-hits", &m_inflight_hits);
    registerStatsMetric("dram", core_id, "writeback-pages", &m_writeback_pages);
    registerStatsMetric("dram", core_id, "local-evictions", &m_local_evictions);
    registerStatsMetric("dram", core_id, "extra-traffic", &m_extra_pages);
    registerStatsMetric("dram", core_id, "redundant-moves", &m_redundant_moves);
    registerStatsMetric("dram", core_id, "max-bufferspace", &m_max_bufferspace);
    registerStatsMetric("dram", core_id, "bufferspace-full-move-page-cancelled", &m_move_page_cancelled_bufferspace_full);
    registerStatsMetric("dram", core_id, "queue-full-move-page-cancelled", &m_move_page_cancelled_datamovement_queue_full);
    registerStatsMetric("dram", core_id, "unique-pages-accessed", &m_unique_pages_accessed);
}

DramPerfModelDisagg::~DramPerfModelDisagg()
{
    if (m_queue_model.size())
    {
        for(UInt32 channel = 0; channel < m_num_channels; ++channel)
            delete m_queue_model[channel];
    }
    delete m_data_movement;

    if (m_rank_avail.size())
    {
        for(UInt32 rank = 0; rank < m_total_ranks; ++rank)
            delete m_rank_avail[rank];
    }

    if (m_bank_group_avail.size())
    {
        for(UInt32 group = 0; group < m_total_bank_groups; ++group)
            delete m_bank_group_avail[group];
    }
    if (m_r_queue_model.size())
    {
        for(UInt32 channel = 0; channel < m_num_channels; ++channel)
            delete m_r_queue_model[channel];
    }

    if (m_r_rank_avail.size())
    {
        for(UInt32 rank = 0; rank < m_total_ranks; ++rank)
            delete m_r_rank_avail[rank];
    }

    if (m_r_bank_group_avail.size())
    {
        for(UInt32 group = 0; group < m_total_bank_groups; ++group)
            delete m_r_bank_group_avail[group];
    }

    // putting this near the end so hopefully print output from the two queue model destructors won't interfere
    if(m_r_partition_queues == 1) {
        delete m_data_movement_2;
    }
}

UInt64
DramPerfModelDisagg::parseAddressBits(UInt64 address, UInt32 &data, UInt32 offset, UInt32 size, UInt64 base_address = 0)
{
    // Parse data from the address based on the offset and size, return the address without the bits used to parse the data.
    UInt32 log2_size = floorLog2(size);
    if (base_address != 0) {
        data = (base_address >> offset) % size;
    } else {
        data = (address >> offset) % size;
    }
    return ((address >> (offset + log2_size)) << offset) | (address & ((1 << offset) - 1));
}

void
DramPerfModelDisagg::parseDeviceAddress(IntPtr address, UInt32 &channel, UInt32 &rank, UInt32 &bank_group, UInt32 &bank, UInt32 &column, UInt64 &dram_page)
{
    // Construct DDR address which has bits used for interleaving removed
    UInt64 linearAddress = m_address_home_lookup->getLinearAddress(address);
    UInt64 address_bits = linearAddress >> 6;
    /*address_bits = */parseAddressBits(address_bits, channel, m_channel_offset, m_num_channels, m_channel_offset < m_home_lookup_bit ? address : linearAddress);
    address_bits = parseAddressBits(address_bits, rank,    m_rank_offset,    m_num_ranks,    m_rank_offset < m_home_lookup_bit ? address : linearAddress);


    if (m_open_page_mapping) {
        // Open-page mapping: column address is bottom bits, then bank, then page
        if(m_column_offset) {
            // Column address is split into 2 halves ColHi and ColLo and
            // the address looks like: | Page | ColHi | Bank | ColLo |
            // m_column_offset specifies the number of ColHi bits
            column = (((address_bits >> m_column_hi_offset) << m_bank_offset)
                    | (address_bits & ((1 << m_bank_offset) - 1))) % m_dram_page_size;
            address_bits = address_bits >> m_bank_offset;
            bank_group = address_bits % m_num_bank_groups;
            bank = address_bits % m_num_banks;
            address_bits = address_bits >> (m_num_banks_log2 + m_column_offset);
        } else {
            column = address_bits % m_dram_page_size; address_bits /= m_dram_page_size;
            bank_group = address_bits % m_num_bank_groups;
            bank = address_bits % m_num_banks; address_bits /= m_num_banks;
        }
        dram_page = address_bits;

#if 0
        // Test address parsing done in this function for open page mapping
        std::bitset<10> bs_col (column);
        std::string str_col = bs_col.to_string<char,std::string::traits_type,std::string::allocator_type>();
        std::stringstream ss_original, ss_recomputed;
        ss_original << std::bitset<64>(linearAddress >> m_block_size_log2) << std::endl;
        ss_recomputed << std::bitset<50>(dram_page) << str_col.substr(0,m_column_offset) << std::bitset<4>(bank)
            << str_col.substr(m_column_offset, str_col.length()-m_column_offset) << std::endl;
        LOG_ASSERT_ERROR(ss_original.str() == ss_recomputed.str(), "Error in device address parsing!");
#endif
    } else {

        bank_group = address_bits % m_num_bank_groups;
        bank = address_bits % m_num_banks;
        address_bits /= m_num_banks;

        // Closed-page mapping: column address is bits X+banksize:X, row address is everything else
        // (from whatever is left after cutting channel/rank/bank from the bottom)
        column = (address_bits >> m_column_bits_shift) % m_dram_page_size;
        dram_page = (((address_bits >> m_column_bits_shift) / m_dram_page_size) << m_column_bits_shift)
            | (address_bits & ((1 << m_column_bits_shift) - 1));
    }

    if(m_randomize_address) {
        std::bitset<3> row_bits(dram_page >> m_randomize_offset);                 // Row[offset+2:offset]
        UInt32 row_bits3 = row_bits.to_ulong();
        row_bits[2] = 0;
        UInt32 row_bits2 = row_bits.to_ulong();
        bank_group ^= ((m_num_bank_groups == 8) ? row_bits3 : row_bits2);    // BankGroup XOR Row
        bank /= m_num_bank_groups;
        bank ^= row_bits2;                                                   // Bank XOR Row
        bank = m_banks_per_bank_group * bank_group + bank;
        rank = (m_num_ranks > 1) ? rank ^ row_bits[0] : rank;                // Rank XOR Row
    }

    //printf("[%2d] address %12lx linearAddress %12lx channel %2x rank %2x bank_group %2x bank %2x dram_page %8lx crb %4u\n", m_core_id, address, linearAddress, channel, rank, bank_group, bank, dram_page, (((channel * m_num_ranks) + rank) * m_num_banks) + bank);
}

SubsecondTime
DramPerfModelDisagg::getAccessLatencyRemote(SubsecondTime pkt_time, UInt64 pkt_size, core_id_t requester, IntPtr address, DramCntlrInterface::access_t access_type, ShmemPerf *perf)
{
    // pkt_size is in 'Bytes'
    // m_dram_bandwidth is in 'Bits per clock cycle'

    // Calculate address mapping inside the DIMM
    UInt32 channel, rank, bank_group, bank, column;
    UInt64 dram_page;
    parseDeviceAddress(address, channel, rank, bank_group, bank, column, dram_page);

    SubsecondTime t_now = pkt_time;
    perf->updateTime(t_now);

    // Add DDR controller pipeline delay
    t_now += m_controller_delay;
    perf->updateTime(t_now, ShmemPerf::DRAM_CNTLR);

    // Add DDR refresh delay if needed
    if (m_refresh_interval != SubsecondTime::Zero()) {

        SubsecondTime refresh_base = (t_now.getPS() / m_refresh_interval.getPS()) * m_refresh_interval;
        if (t_now - refresh_base < m_refresh_length) {
            t_now = refresh_base + m_refresh_length;
            perf->updateTime(t_now, ShmemPerf::DRAM_REFRESH);
        }
    }


    UInt64 crb = (channel * m_num_ranks * m_num_banks) + (rank * m_num_banks) + bank; // Combine channel, rank, bank to index m_banks
    LOG_ASSERT_ERROR(crb < m_total_banks, "Bank index out of bounds");
    BankInfo &bank_info = m_r_banks[crb];

    //printf("[%2d] %s (%12lx, %4lu, %4lu), t_open = %lu, t_now = %lu, bank_info.t_avail = %lu\n", m_core_id, bank_info.open_page == dram_page && bank_info.t_avail + m_bank_keep_open >= t_now ? "Page Hit: " : "Page Miss:", address, crb, dram_page % 10000, t_now.getNS() - bank_info.t_avail.getNS(), t_now.getNS(), bank_info.t_avail.getNS());
    // DRAM page hit/miss
    if (bank_info.open_page == dram_page                            // Last access was to this row
            && bank_info.t_avail + m_bank_keep_open >= t_now   // Bank hasn't been closed in the meantime
       ) {

        if (bank_info.t_avail > t_now) {
            t_now = bank_info.t_avail;
            perf->updateTime(t_now, ShmemPerf::DRAM_BANK_PENDING);
        }
        ++m_dram_page_hits;

    } else {
        // Wait for bank to become available
        if (bank_info.t_avail > t_now)
            t_now = bank_info.t_avail;
        // Close dram_page
        if (bank_info.t_avail + m_bank_keep_open >= t_now) {
            // We found the dram_page open and have to close it ourselves
            t_now += m_bank_close_delay;
            ++m_dram_page_misses;
        } else if (bank_info.t_avail + m_bank_keep_open + m_bank_close_delay > t_now) {
            // Bank was being closed, we have to wait for that to complete
            t_now = bank_info.t_avail + m_bank_keep_open + m_bank_close_delay;
            ++m_dram_page_closing;
        } else {
            // Bank was already closed, no delay.
            ++m_dram_page_empty;
        }

        // Open dram_page
        t_now += m_bank_open_delay;
        perf->updateTime(t_now, ShmemPerf::DRAM_BANK_CONFLICT);

        bank_info.open_page = dram_page;
    }

    // Add rank access time and availability
    UInt64 cr = (channel * m_num_ranks) + rank;
    LOG_ASSERT_ERROR(cr < m_total_ranks, "Rank index out of bounds");
    SubsecondTime rank_avail_request = (m_num_bank_groups > 1) ? m_intercommand_delay_short : m_intercommand_delay;
    SubsecondTime rank_avail_delay = m_r_rank_avail.size() ? m_r_rank_avail[cr]->computeQueueDelay(t_now, rank_avail_request, requester) : SubsecondTime::Zero();

    // Add bank group access time and availability
    UInt64 crbg = (channel * m_num_ranks * m_num_bank_groups) + (rank * m_num_bank_groups) + bank_group;
    LOG_ASSERT_ERROR(crbg < m_total_bank_groups, "Bank-group index out of bounds");
    SubsecondTime group_avail_delay = m_r_bank_group_avail.size() ? m_r_bank_group_avail[crbg]->computeQueueDelay(t_now, m_intercommand_delay_long, requester) : SubsecondTime::Zero();

    // Add device access time (tCAS)
    t_now += m_dram_access_cost;
    perf->updateTime(t_now, ShmemPerf::DRAM_DEVICE);

    // Mark bank as busy until it can receive its next command
    // Done before waiting for the bus to be free: sort of assumes best-case bus scheduling
    bank_info.t_avail = t_now;

    // Add the wait time for the larger of bank group and rank availability delay
    t_now += (rank_avail_delay > group_avail_delay) ? rank_avail_delay : group_avail_delay;
    perf->updateTime(t_now, ShmemPerf::DRAM_DEVICE);
    //std::cout << "DDR Processing time: " << m_bus_bandwidth.getRoundedLatency(8*pkt_size) << std::endl; 

    // Add DDR bus latency and queuing delay
    SubsecondTime ddr_processing_time = m_bus_bandwidth.getRoundedLatency(8 * pkt_size); // bytes to bits
    SubsecondTime ddr_queue_delay = m_r_queue_model.size() ? m_r_queue_model[channel]->computeQueueDelay(t_now, ddr_processing_time, requester) : SubsecondTime::Zero();
    t_now += ddr_queue_delay;
    perf->updateTime(t_now, ShmemPerf::DRAM_QUEUE);
    //std::cout << "Local Queue Processing time: " << m_bus_bandwidth.getRoundedLatency(8*pkt_size) << " Local queue delay " << ddr_queue_delay << std::endl; 

    // Compress
    UInt64 phys_page = address & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
    UInt32 size = pkt_size;
    if (m_use_compression && m_r_cacheline_gran)
    {
        UInt32 compressed_cache_lines;
        SubsecondTime compression_latency = m_compression_model->compress(phys_page, m_cache_line_size, m_core_id, &size, &compressed_cache_lines);
        bytes_saved += m_cache_line_size - size;
        address_to_compressed_size[phys_page] = size;
        address_to_num_cache_lines[phys_page] = compressed_cache_lines;
        m_sum_compression_ratio += float(m_cache_line_size) / float(size);
        m_total_compression_latency += compression_latency;
        t_now += compression_latency;
    }

    SubsecondTime datamovement_queue_delay;
    if (m_r_partition_queues == 1) {
        datamovement_queue_delay = m_data_movement_2->computeQueueDelayTrackBytes(t_now, m_r_part2_bandwidth.getRoundedLatency(8*size), size, requester);
        m_redundant_moves++;
    } else {
        datamovement_queue_delay = m_data_movement->computeQueueDelayTrackBytes(t_now, m_r_bus_bandwidth.getRoundedLatency(8*size), size, requester);
    }

    // TODO: Currently model decompression by adding decompression latency to inflight page time
    if (m_use_compression && m_r_cacheline_gran)
    {
        SubsecondTime decompression_latency = m_compression_model->decompress(phys_page, address_to_num_cache_lines[phys_page], m_core_id);
        datamovement_queue_delay += decompression_latency;
        m_total_decompression_latency += decompression_latency;
    }

    //std::cout << "Packet size: " << pkt_size << "  Cacheline Processing time: " << m_r_bus_bandwidth.getRoundedLatency(8*pkt_size) << " Remote queue delay " << datamovement_queue_delay << std::endl; 
    // LOG_PRINT("Packet size: %ld; Cacheline processing time: %ld; ddr_processing_time: %ld",
    //           pkt_size, m_r_bus_bandwidth.getRoundedLatency(8*pkt_size).getNS(), ddr_processing_time.getNS());


    t_now += ddr_processing_time;
    // LOG_PRINT("Processing time before remote added latency: %ld ns; datamovement_queue_delay: %ld ns",
    //           (t_now - pkt_time).getNS(), datamovement_queue_delay.getNS());
    // LOG_PRINT("m_r_bus_bandwidth getRoundedLatency=%ld ns; getLatency=%ld ns", m_r_bus_bandwidth.getRoundedLatency(8*pkt_size).getNS(), m_r_bus_bandwidth.getLatency(8*pkt_size).getNS());
    
    if (!m_r_use_separate_queue_model) {  // when a separate remote QueueModel is used, the network latency is added there
        t_now += m_r_added_latency;
    }
    if(m_r_mode != 4 && !m_r_enable_selective_moves) {
        t_now += datamovement_queue_delay;
    } 

    perf->updateTime(t_now, ShmemPerf::DRAM_BUS);

    // Track access to page
    // UInt64 phys_page = address & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
    if(m_r_cacheline_gran) 
        phys_page =  address & ~((UInt64(1) << floorLog2(m_cache_line_size)) - 1); // Was << 6
    bool move_page = false; 
    if(m_r_mode == 2) { //Only move pages when the page has been accessed remotely m_r_datamov_threshold times
        auto it = m_remote_access_tracker.find(phys_page);
        if (it != m_remote_access_tracker.end())
            m_remote_access_tracker[phys_page]++; 
        else
            m_remote_access_tracker[phys_page] = 1;
        if (m_remote_access_tracker[phys_page] > m_r_datamov_threshold)
            move_page = true;
    } 
    if(m_r_mode == 1 || m_r_mode == 3) {
        move_page = true; 
    }
    // Cancel moving the page if the amount of reserved bufferspace in localdram for inflight + inflight_evicted pages is not enough to support an additional move
    if((m_r_reserved_bufferspace > 0) && ((m_inflight_pages.size() + m_inflightevicted_pages.size())  >= (m_r_reserved_bufferspace/100)*m_localdram_size/m_page_size)) {
        move_page = false;
        ++m_move_page_cancelled_bufferspace_full;
    }
    // Cancel moving the page if the queue used to move the page is already full
    if(m_data_movement->isQueueFull(pkt_time)) {
        move_page = false;
        ++m_move_page_cancelled_datamovement_queue_full;
    } 

    // Adding data movement cost of the entire page for now (this just adds contention in the queue)
    if (move_page) {
        ++m_page_moves;
        SubsecondTime page_datamovement_queue_delay = SubsecondTime::Zero();
        if(m_r_simulate_datamov_overhead && !m_r_cacheline_gran) {
            //check if queue is full
            //if it is... wait.
            //to wait: t_now + window_size
            //try again

            // Compress
            UInt32 page_size = m_page_size;
            if (m_use_compression)
            {
                UInt32 compressed_cache_lines;
                SubsecondTime compression_latency = m_compression_model->compress(phys_page, m_page_size, m_core_id, &page_size, &compressed_cache_lines);
                bytes_saved += m_page_size - page_size;
                address_to_compressed_size[phys_page] = page_size;
                address_to_num_cache_lines[phys_page] = compressed_cache_lines;
                m_sum_compression_ratio += float(m_page_size) / float(page_size);
                m_total_compression_latency += compression_latency;
                t_now += compression_latency;
            }

            if(m_r_partition_queues == 1) {
                page_datamovement_queue_delay = m_data_movement->computeQueueDelayTrackBytes(t_now, m_r_part_bandwidth.getRoundedLatency(8*page_size), page_size, requester);
            } else {
                page_datamovement_queue_delay = m_data_movement->computeQueueDelayTrackBytes(t_now, m_r_bus_bandwidth.getRoundedLatency(8*page_size), page_size, requester);
                t_now += page_datamovement_queue_delay;
                t_now -= datamovement_queue_delay;
            }

            // TODO: Currently model decompression by adding decompression latency to inflight page time
            if (m_use_compression)
            {
                SubsecondTime decompression_latency = m_compression_model->decompress(phys_page, address_to_num_cache_lines[phys_page], m_core_id);
                page_datamovement_queue_delay += decompression_latency;
                m_total_decompression_latency += decompression_latency;
            }
        }
        else
            page_datamovement_queue_delay = SubsecondTime::Zero(); 


        assert(std::find(m_local_pages.begin(), m_local_pages.end(), phys_page) == m_local_pages.end()); 
        assert(std::find(m_remote_pages.begin(), m_remote_pages.end(), phys_page) != m_remote_pages.end()); 
        m_local_pages.push_back(phys_page);
        if(m_r_exclusive_cache)
            m_remote_pages.remove(phys_page);

        m_inflight_pages.erase(phys_page);
        m_inflight_pages[phys_page] = SubsecondTime::max(Sim()->getClockSkewMinimizationServer()->getGlobalTime() + page_datamovement_queue_delay, t_now + page_datamovement_queue_delay);
        m_inflight_redundant[phys_page] = 0; 
        if(m_inflight_pages.size() > m_max_bufferspace)
            m_max_bufferspace++; 
    } 

    if(move_page) { //Check if there's place in local DRAM and if not evict an older page to make space
        t_now += possiblyEvict(phys_page, pkt_time, requester);
    }

    // Update Memory Counters?
    //queue_delay = ddr_queue_delay;

    //std::cout << "Remote Latency: " << t_now - pkt_time << std::endl;
    possiblyPrefetch(phys_page, t_now, requester);
    m_total_remote_access_latency += (t_now - pkt_time);
    return t_now - pkt_time;
}


SubsecondTime
DramPerfModelDisagg::getAccessLatency(SubsecondTime pkt_time, UInt64 pkt_size, core_id_t requester, IntPtr address, DramCntlrInterface::access_t access_type, ShmemPerf *perf)
{
    UInt64 phys_page = address & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
    if(m_r_cacheline_gran) 
        phys_page =  address & ~((UInt64(1) << floorLog2(m_cache_line_size)) - 1); // Was << 6
    UInt64 cacheline =  address & ~((UInt64(1) << floorLog2(m_cache_line_size)) - 1); // Was << 6

    if (m_page_usage_map.count(phys_page) == 0) {
        ++m_unique_pages_accessed;
        m_page_usage_map[phys_page] = 0;
    } else {
        m_page_usage_map[phys_page] += 1;
    }

    // m_inflight_pages: tracks which pages are being moved and when the movement will complete
    // Check if the page movement is over and if so, remove from the list
    // Do this for both queues, forward and backward
    std::map<UInt64, SubsecondTime>::iterator i;
    for(i = m_inflight_pages.begin(); i != m_inflight_pages.end();) {
        if(i->second <= SubsecondTime::max(Sim()->getClockSkewMinimizationServer()->getGlobalTime(), pkt_time)) {
            m_inflight_redundant.erase(i->first);
            m_inflight_pages.erase(i++);
        } else {
            ++i;
        }
    }

    for(i = m_inflightevicted_pages.begin(); i != m_inflightevicted_pages.end();) {
        if(i->second <= SubsecondTime::max(Sim()->getClockSkewMinimizationServer()->getGlobalTime(), pkt_time)) {
            m_inflightevicted_pages.erase(i++);
        } else {
            ++i;
        }
    }

    // Other systems using the remote memory and creating disturbance
    if(m_r_disturbance_factor > 0) {
        if( (unsigned int)(rand() % 100) < m_r_disturbance_factor) {
            SubsecondTime delay(SubsecondTime::NS() * 1000);
            if(m_r_partition_queues == 1)  
                /* SubsecondTime page_datamovement_queue_delay = */ m_data_movement->computeQueueDelayTrackBytes(pkt_time + delay, m_r_part_bandwidth.getRoundedLatency(8*m_page_size), m_page_size, requester);
            else	
                /* SubsecondTime page_datamovement_queue_delay = */ m_data_movement->computeQueueDelayTrackBytes(pkt_time + delay, m_r_bus_bandwidth.getRoundedLatency(8*m_page_size), m_page_size, requester);
            m_extra_pages++;	
        } 
    } 

    // Should we enable a remote access?
    if(m_enable_remote_mem && isRemoteAccess(address, requester, access_type)) {
        if (access_type == DramCntlrInterface::READ) {
            ++m_remote_reads;
        } else {  // access_type == DramCntlrInterface::WRITE
            ++m_remote_writes;
        }
        //	printf("Remote access: %d\n",m_remote_reads); 
        return (getAccessLatencyRemote(pkt_time, pkt_size, requester, address, access_type, perf)); 
    }

    // pkt_size is in 'Bytes'
    // m_dram_bandwidth is in 'Bits per clock cycle'

    // Calculate address mapping inside the DIMM
    UInt32 channel, rank, bank_group, bank, column;
    UInt64 dram_page;
    parseDeviceAddress(address, channel, rank, bank_group, bank, column, dram_page);


    SubsecondTime t_now = pkt_time;
    perf->updateTime(t_now);

    // Add DDR controller pipeline delay
    t_now += m_controller_delay;
    perf->updateTime(t_now, ShmemPerf::DRAM_CNTLR);

    // Add DDR refresh delay if needed
    if (m_refresh_interval != SubsecondTime::Zero()) {
        SubsecondTime refresh_base = (t_now.getPS() / m_refresh_interval.getPS()) * m_refresh_interval;
        if (t_now - refresh_base < m_refresh_length) {
            t_now = refresh_base + m_refresh_length;
            perf->updateTime(t_now, ShmemPerf::DRAM_REFRESH);
        }
    }


    UInt64 crb = (channel * m_num_ranks * m_num_banks) + (rank * m_num_banks) + bank; // Combine channel, rank, bank to index m_banks
    LOG_ASSERT_ERROR(crb < m_total_banks, "Bank index out of bounds");
    BankInfo &bank_info = m_banks[crb];

    //printf("[%2d] %s (%12lx, %4lu, %4lu), t_open = %lu, t_now = %lu, bank_info.t_avail = %lu\n", m_core_id, bank_info.open_page == dram_page && bank_info.t_avail + m_bank_keep_open >= t_now ? "Page Hit: " : "Page Miss:", address, crb, dram_page % 10000, t_now.getNS() - bank_info.t_avail.getNS(), t_now.getNS(), bank_info.t_avail.getNS());

    // DRAM page hit/miss
    if (bank_info.open_page == dram_page                       // Last access was to this row
            && bank_info.t_avail + m_bank_keep_open >= t_now   // Bank hasn't been closed in the meantime
       ) {
        if (bank_info.t_avail > t_now) {
            t_now = bank_info.t_avail;
            perf->updateTime(t_now, ShmemPerf::DRAM_BANK_PENDING);
        }
        ++m_dram_page_hits;

    } else {
        // Wait for bank to become available
        if (bank_info.t_avail > t_now)
            t_now = bank_info.t_avail;
        // Close dram_page
        if (bank_info.t_avail + m_bank_keep_open >= t_now) {
            // We found the dram_page open and have to close it ourselves
            t_now += m_bank_close_delay;
            ++m_dram_page_misses;
        } else if (bank_info.t_avail + m_bank_keep_open + m_bank_close_delay > t_now) {
            // Bank was being closed, we have to wait for that to complete
            t_now = bank_info.t_avail + m_bank_keep_open + m_bank_close_delay;
            ++m_dram_page_closing;
        } else {
            // Bank was already closed, no delay.
            ++m_dram_page_empty;
        }

        // Open dram_page
        t_now += m_bank_open_delay;
        perf->updateTime(t_now, ShmemPerf::DRAM_BANK_CONFLICT);

        bank_info.open_page = dram_page;
    }

    // Add rank access time and availability
    UInt64 cr = (channel * m_num_ranks) + rank;
    LOG_ASSERT_ERROR(cr < m_total_ranks, "Rank index out of bounds");
    SubsecondTime rank_avail_request = (m_num_bank_groups > 1) ? m_intercommand_delay_short : m_intercommand_delay;
    SubsecondTime rank_avail_delay = m_rank_avail.size() ? m_rank_avail[cr]->computeQueueDelay(t_now, rank_avail_request, requester) : SubsecondTime::Zero();

    // Add bank group access time and availability
    UInt64 crbg = (channel * m_num_ranks * m_num_bank_groups) + (rank * m_num_bank_groups) + bank_group;
    LOG_ASSERT_ERROR(crbg < m_total_bank_groups, "Bank-group index out of bounds");
    SubsecondTime group_avail_delay = m_bank_group_avail.size() ? m_bank_group_avail[crbg]->computeQueueDelay(t_now, m_intercommand_delay_long, requester) : SubsecondTime::Zero();

    // Add device access time (tCAS)
    t_now += m_dram_access_cost;
    perf->updateTime(t_now, ShmemPerf::DRAM_DEVICE);

    // Mark bank as busy until it can receive its next command
    // Done before waiting for the bus to be free: sort of assumes best-case bus scheduling
    bank_info.t_avail = t_now;

    // Add the wait time for the larger of bank group and rank availability delay
    t_now += (rank_avail_delay > group_avail_delay) ? rank_avail_delay : group_avail_delay;
    perf->updateTime(t_now, ShmemPerf::DRAM_DEVICE);

    // DDR bus latency and queuing delay
    SubsecondTime ddr_processing_time = m_bus_bandwidth.getRoundedLatency(8 * pkt_size); // bytes to bits
    //std::cout << m_bus_bandwidth.getRoundedLatency(8*pkt_size) << std::endl;  
    SubsecondTime ddr_queue_delay = m_queue_model.size() ? m_queue_model[channel]->computeQueueDelay(t_now, ddr_processing_time, requester) : SubsecondTime::Zero();
    t_now += ddr_queue_delay;
    perf->updateTime(t_now, ShmemPerf::DRAM_QUEUE);
    t_now += ddr_processing_time;
    perf->updateTime(t_now, ShmemPerf::DRAM_BUS);

    // Update Memory Counters? 
    //queue_delay = ddr_queue_delay;

    if((m_inflight_pages.find(phys_page) == m_inflight_pages.end()) || m_r_enable_selective_moves) {
        // The phys_page is not included in m_inflight_pages or m_r_enable_selective_moves is true, then total access latency = t_now - pkt_time
        m_total_local_access_latency += (t_now - pkt_time);
        return t_now - pkt_time;
    } else {
        // The phys_age is an inflight page and m_r_enable_selective_moves is false
        //SubsecondTime current_time = std::min(Sim()->getClockSkewMinimizationServer()->getGlobalTime(), t_now);
        SubsecondTime access_latency = m_inflight_pages[phys_page] > t_now ? (m_inflight_pages[phys_page] - pkt_time): (t_now - pkt_time);

        if(access_latency > (t_now - pkt_time)) {
            // The page is still in transit from remote to local memory
            m_inflight_hits++; 

            if(m_r_partition_queues == 1 && m_inflight_redundant[phys_page] < m_r_limit_redundant_moves) {
                // Compare the arrival time of the inflight page vs requesting the cache line using the cacheline queue
               if(m_r_throttle_redundant_moves) {
                    SubsecondTime datamov_queue_delay = m_data_movement_2->computeQueueDelayNoEffect(t_now, m_r_part2_bandwidth.getRoundedLatency(8*pkt_size), requester);
                    if ((datamov_queue_delay + t_now - pkt_time) < access_latency) {
                        datamov_queue_delay = m_data_movement_2->computeQueueDelayTrackBytes(t_now, m_r_part2_bandwidth.getRoundedLatency(8*pkt_size), pkt_size, requester);
                        access_latency = datamov_queue_delay + t_now - pkt_time;
                        ++m_redundant_moves;
                    } 
                } else {
                    SubsecondTime datamov_queue_delay = m_data_movement_2->computeQueueDelayNoEffect(t_now, m_r_part2_bandwidth.getRoundedLatency(8*pkt_size), requester);
                    if ((datamov_queue_delay + t_now - pkt_time) < access_latency) {
                        datamov_queue_delay = m_data_movement_2->computeQueueDelayTrackBytes(t_now, m_r_part2_bandwidth.getRoundedLatency(8*pkt_size), pkt_size, requester);
                        access_latency = datamov_queue_delay + t_now - pkt_time;
                        ++m_redundant_moves;
                        m_inflight_redundant[phys_page] = m_inflight_redundant[phys_page] + 1; 
                    } 
                }
            }
        }
        m_total_local_access_latency += access_latency;
        return access_latency;  
    }
}


bool 
DramPerfModelDisagg::isRemoteAccess(IntPtr address, core_id_t requester, DramCntlrInterface::access_t access_type) 
{
    UInt64 num_local_pages = m_localdram_size/m_page_size;
    if(m_r_cacheline_gran) // When we perform moves at cacheline granularity (should be disabled by default)
        num_local_pages = m_localdram_size/m_cache_line_size;  // Assuming 64bit cache line

    UInt64 phys_page =  address & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
    if(m_r_cacheline_gran) 
        phys_page =  address & ~((UInt64(1) << floorLog2(m_cache_line_size)) - 1);

    if(m_r_mode == 0 || m_r_mode == 4) { // Static partitioning: no data movement and m_r_partitioning_ratio decides how many go where
        if (std::find(m_local_pages.begin(), m_local_pages.end(), phys_page) != m_local_pages.end())
            return false;
        else if (std::find(m_remote_pages.begin(), m_remote_pages.end(), phys_page) != m_remote_pages.end())
            return true;
        else if ( (unsigned int)(rand() % 100) < m_r_partitioning_ratio) {
            m_local_pages.push_back(phys_page);
            return false;
        } 
        else {
            m_remote_pages.push_back(phys_page);
            return true; 
        }
    }
    else if(m_r_mode == 1 || m_r_mode == 2 || m_r_mode == 3) {  // local DRAM as a cache 
        if (std::find(m_local_pages.begin(), m_local_pages.end(), phys_page) != m_local_pages.end()) { // Is it in local DRAM?
            m_local_pages.remove(phys_page); // LRU
            m_local_pages.push_back(phys_page);
            if(access_type == DramCntlrInterface::WRITE) {
                m_dirty_pages.remove(phys_page);
                m_dirty_pages.push_back(phys_page);
            }
            return false;
        } 
        else if (std::find(m_remote_pages.begin(), m_remote_pages.end(), phys_page) != m_remote_pages.end()) {	
            // printf("Remote page found: %lx\n", phys_page); 
            return true;
        }
        else {
            if(m_remote_init) { // Assuming all pages start off in remote memory
                m_remote_pages.push_back(phys_page); 
                //    printf("Remote page found: %lx\n", phys_page); 
                return true;
            } else {
                if(m_local_pages.size() < num_local_pages) {
                    m_local_pages.push_back(phys_page);
                    return false; 
                } 
                else {
                    m_remote_pages.push_back(phys_page); 
                    // printf("Remote page created: %lx\n", phys_page); 
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
    SubsecondTime sw_overhead = SubsecondTime::Zero();
    SubsecondTime evict_compression_latency = SubsecondTime::Zero();
    UInt64 evicted_page; 

    UInt64 num_local_pages = m_localdram_size/m_page_size;
    if(m_r_cacheline_gran)
        num_local_pages = m_localdram_size/m_cache_line_size;

    if(m_local_pages.size() > num_local_pages) {
        bool found = false;

        if(m_r_dontevictdirty) {
            auto i = m_local_pages.begin();
            for(unsigned int k = 0; k < m_local_pages.size()/2; ++i, ++k) {
                if (std::find(m_dirty_pages.begin(), m_dirty_pages.end(), *i) == m_dirty_pages.end()) {
                    // This is a non-dirty page
                    found = true;
                    evicted_page = *i; 
                    break;
                }
            }	
            // If a non-dirty page is found, just remove this page to make space
            if (found) {
                m_local_pages.remove(evicted_page); 
            }
        }

        // If found==false, remove the first page
        if(!found) {
            evicted_page = m_local_pages.front(); // Evict the least recently used page
            m_local_pages.pop_front(); 
        }
        ++m_local_evictions; 

        if(m_r_simulate_sw_pagereclaim_overhead) 
            sw_overhead = SubsecondTime::NS() * 30000; 		

        if (std::find(m_dirty_pages.begin(), m_dirty_pages.end(), evicted_page) != m_dirty_pages.end()) {
            // The page to evict is dirty
            ++m_page_moves;
            ++m_writeback_pages;

            // Compress
            UInt32 size = m_r_cacheline_gran ? m_cache_line_size : m_page_size;
            if (m_use_compression)
            {
                UInt32 gran_size = size;
                UInt32 compressed_cache_lines;
                SubsecondTime compression_latency = m_compression_model->compress(phys_page, gran_size, m_core_id, &size, &compressed_cache_lines);
                bytes_saved += gran_size - size;
                address_to_compressed_size[phys_page] = size;
                address_to_num_cache_lines[phys_page] = compressed_cache_lines;
                m_sum_compression_ratio += float(gran_size) / float(size);
                evict_compression_latency += compression_latency;
                m_total_compression_latency += compression_latency;
            }

            SubsecondTime page_datamovement_queue_delay = SubsecondTime::Zero();
            if(m_r_simulate_datamov_overhead) { 
                if(m_r_partition_queues == 1) {
                    page_datamovement_queue_delay = m_data_movement->computeQueueDelayTrackBytes(t_now, m_r_part_bandwidth.getRoundedLatency(8*size), size, requester);
                } /* else if(m_r_cacheline_gran) {
                    page_datamovement_queue_delay = m_data_movement->computeQueueDelayTrackBytes(t_now, m_r_bus_bandwidth.getRoundedLatency(8*size), size, requester);
                } */ else {
                    page_datamovement_queue_delay = m_data_movement->computeQueueDelayTrackBytes(t_now, m_r_bus_bandwidth.getRoundedLatency(8*size), size, requester);
                }
            }

            // TODO: Currently model decompression by adding decompression latency to inflight page time
            if (m_use_compression)
            {
                SubsecondTime decompression_latency = m_compression_model->decompress(phys_page, address_to_num_cache_lines[phys_page], m_core_id);
                page_datamovement_queue_delay += decompression_latency;
                m_total_decompression_latency += decompression_latency;
            }

            if (std::find(m_remote_pages.begin(), m_remote_pages.end(), evicted_page) == m_remote_pages.end()) {
                // The page to evict is not in remote_pages
                m_remote_pages.push_back(evicted_page);
            }
            m_inflightevicted_pages[evicted_page] = t_now + page_datamovement_queue_delay;

        } else if (std::find(m_remote_pages.begin(), m_remote_pages.end(), evicted_page) == m_remote_pages.end()) {
            // The page to evict is not dirty and not in remote memory
            m_remote_pages.push_back(evicted_page);
            ++m_page_moves;

            // Compress
            UInt32 size = m_r_cacheline_gran ? m_cache_line_size : m_page_size;
            if (m_use_compression)
            {
                UInt32 gran_size = size;
                UInt32 compressed_cache_lines;
                SubsecondTime compression_latency = m_compression_model->compress(phys_page, gran_size, m_core_id, &size, &compressed_cache_lines);
                bytes_saved += gran_size - size;
                address_to_compressed_size[phys_page] = size;
                address_to_num_cache_lines[phys_page] = compressed_cache_lines;
                m_sum_compression_ratio += float(gran_size) / float(size);
                evict_compression_latency += compression_latency;
                m_total_compression_latency += compression_latency;
            }

            SubsecondTime page_datamovement_queue_delay = SubsecondTime::Zero();
            if(m_r_simulate_datamov_overhead) {
                if(m_r_partition_queues == 1) {
                    page_datamovement_queue_delay = m_data_movement->computeQueueDelayTrackBytes(t_now, m_r_part_bandwidth.getRoundedLatency(8*size), size, requester);
                } /* else if(m_r_cacheline_gran) {
                    page_datamovement_queue_delay = m_data_movement->computeQueueDelayTrackBytes(t_now, m_r_bus_bandwidth.getRoundedLatency(8*size), size, requester);
                } */ else {
                    page_datamovement_queue_delay = m_data_movement->computeQueueDelayTrackBytes(t_now, m_r_bus_bandwidth.getRoundedLatency(8*size), size, requester);
                }
            }

            // TODO: Currently model decompression by adding decompression latency to inflight page time
            if (m_use_compression)
            {
                SubsecondTime decompression_latency = m_compression_model->decompress(phys_page, address_to_num_cache_lines[phys_page], m_core_id);
                page_datamovement_queue_delay += decompression_latency;
                m_total_decompression_latency += decompression_latency;
            }

            m_inflightevicted_pages[evicted_page] = t_now + page_datamovement_queue_delay;
        }

        m_dirty_pages.remove(evicted_page);
    }
    return sw_overhead + evict_compression_latency;
}


void 
DramPerfModelDisagg::possiblyPrefetch(UInt64 phys_page, SubsecondTime t_now, core_id_t requester) 
{
    if(!m_r_enable_nl_prefetcher) {
        return;
    }
    UInt64 pref_page = phys_page + 1 * m_page_size;
    if (std::find(m_local_pages.begin(), m_local_pages.end(), pref_page) == m_local_pages.end() && std::find(m_remote_pages.begin(), m_remote_pages.end(), pref_page) != m_remote_pages.end()) {
        // pref_page is not in local_pages but in remote_pages
        ++m_page_prefetches;
        ++m_page_moves;
        SubsecondTime page_datamovement_queue_delay = SubsecondTime::Zero();
        if(m_r_simulate_datamov_overhead) { 
            page_datamovement_queue_delay = m_data_movement->computeQueueDelayTrackBytes(t_now, m_r_bus_bandwidth.getRoundedLatency(8*m_page_size), m_page_size, requester);
        } 

        assert(std::find(m_local_pages.begin(), m_local_pages.end(), pref_page) == m_local_pages.end()); 
        assert(std::find(m_remote_pages.begin(), m_remote_pages.end(), pref_page) != m_remote_pages.end()); 
        m_local_pages.push_back(pref_page);
        if(m_r_exclusive_cache)
            m_remote_pages.remove(pref_page);
        m_inflight_pages.erase(pref_page);
        m_inflight_pages[pref_page] = t_now + page_datamovement_queue_delay;
        possiblyEvict(phys_page, t_now, requester);
    }
}
