#include "dram_hardware_cntlr.h"
#include "simulator.h"
#include "config.h"
#include "config.hpp"
#include "stats.h"
#include "shmem_perf.h"
#include "address_home_lookup.h"
#include "utils.h"

DramHardwareCntlr::DramHardwareCntlr(core_id_t core_id, AddressHomeLookup* address_home_lookup, UInt32 cache_line_size, UInt32 page_size, UInt32 r_partition_queues)
    : m_core_id             (core_id)
    , m_address_home_lookup (address_home_lookup)
    , m_cache_line_size     (cache_line_size)
    , m_page_size           (page_size)
    , m_r_partition_queues  (r_partition_queues)
    , m_r_pq_cacheline_hw_no_queue_delay    (Sim()->getCfg()->getBool("perf_model/dram/r_cacheline_hw_no_queue_delay"))
    , m_use_detailed_cost_calculation       (Sim()->getCfg()->getBool("perf_model/dram/use_detailed_dram_hw_access_cost"))
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
    , m_banks_per_bank_group(m_num_banks / m_num_bank_groups)
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
    , m_dram_hw_fixed_latency(SubsecondTime::NS(Sim()->getCfg()->getInt("perf_model/dram/dram_hw_fixed_latency")))
    , m_bus_bandwidth       (m_dram_speed * m_data_bus_width / 1000) // In bits/ns: MT/s=transfers/us * bits/transfer
    , m_r_dram_bus_bandwidth(m_dram_speed * m_data_bus_width * Sim()->getCfg()->getInt("perf_model/dram/remote_dram_bus_scalefactor") / 1000) // In bits/ns: MT/s=transfers/us * bits/transfer
    , m_bank_keep_open          (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/bank_keep_open")))
    , m_bank_open_delay         (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/bank_open_delay")))
    , m_bank_close_delay        (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/bank_close_delay")))
    , m_dram_access_cost        (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/access_cost")))
    , m_r_added_dram_access_cost(SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/added_dram_access_cost")))
    , m_intercommand_delay      (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/intercommand_delay"))) // Rank availability
    , m_intercommand_delay_short(SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/intercommand_delay_short"))) // Rank availability
    , m_intercommand_delay_long (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/intercommand_delay_long"))) // Bank group availability
    , m_controller_delay        (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/controller_delay"))) // Average pipeline delay for various DDR controller stages
    , m_refresh_interval        (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/refresh_interval"))) // tREFI
    , m_refresh_length          (SubsecondTime::NS() * static_cast<uint64_t> (Sim()->getCfg()->getFloat("perf_model/dram/ddr/refresh_length"))) // tRFC
    , m_banks                   (m_total_banks)
    , m_r_banks                 (m_total_banks)
    , m_dram_page_hits          (0)
    , m_dram_page_empty         (0)
    , m_dram_page_closing       (0)
    , m_dram_page_misses        (0)
    , m_local_get_dram_access_cost_processing_time              (SubsecondTime::Zero())
, m_local_get_dram_access_cost_queue_delay                      (SubsecondTime::Zero())
    , m_remote_cacheline_get_dram_access_cost_processing_time   (SubsecondTime::Zero())
    , m_remote_cacheline_get_dram_access_cost_queue_delay       (SubsecondTime::Zero())
    , m_remote_page_get_dram_access_cost_processing_time        (SubsecondTime::Zero())
    , m_remote_page_get_dram_access_cost_queue_delay            (SubsecondTime::Zero())
{
    LOG_ASSERT_ERROR(m_column_offset <= m_dram_page_size_log2, "Column offset exceeds bounds!");
    if (m_randomize_address)
        LOG_ASSERT_ERROR(m_num_bank_groups == 4 || m_num_bank_groups == 8, "Number of bank groups incorrect for address randomization!");
    
    String name("dram");  // This should match the name temporary variable in dram_perf_model_disagg.cc
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
    m_dram_queue_model_single = QueueModel::create(
                name + "-single-queue", core_id, Sim()->getCfg()->getString("perf_model/dram/queue_model/type"),
                m_bus_bandwidth.getRoundedLatency(8), m_bus_bandwidth.getBandwidthBitsPerUs());
    m_r_dram_queue_model_single = QueueModel::create(
                name + "-single-remote-queue", core_id, Sim()->getCfg()->getString("perf_model/dram/queue_model/type"),
                m_bus_bandwidth.getRoundedLatency(8), m_bus_bandwidth.getBandwidthBitsPerUs());

    for (UInt32 rank = 0; rank < m_total_ranks; ++rank) {
        m_rank_avail.push_back(QueueModel::create(
                    name + "-rank-" + itostr(rank), core_id, "history_list",
                    (m_num_bank_groups > 1) ? m_intercommand_delay_short : m_intercommand_delay));
        m_r_rank_avail.push_back(QueueModel::create(
                    name + "-remote-rank-" + itostr(rank), core_id, "history_list",
                    (m_num_bank_groups > 1) ? m_intercommand_delay_short : m_intercommand_delay));
    }

    for (UInt32 group = 0; group < m_total_bank_groups; ++group) {
        m_bank_group_avail.push_back(QueueModel::create(
                    name + "-bank-group-" + itostr(group), core_id, "history_list",
                    m_intercommand_delay_long));
        m_r_bank_group_avail.push_back(QueueModel::create(
                    name + "-remote-bank-group-" + itostr(group), core_id, "history_list",
                    m_intercommand_delay_long));
    }

    registerStatsMetric("ddr", core_id, "page-hits", &m_dram_page_hits);
    registerStatsMetric("ddr", core_id, "page-empty", &m_dram_page_empty);
    registerStatsMetric("ddr", core_id, "page-closing", &m_dram_page_closing);
    registerStatsMetric("ddr", core_id, "page-misses", &m_dram_page_misses);

    registerStatsMetric("dram", core_id, "total-local-dram-hardware-latency-processing-time", &m_local_get_dram_access_cost_processing_time);
    registerStatsMetric("dram", core_id, "total-local-dram-hardware-latency-queue-delay", &m_local_get_dram_access_cost_queue_delay);
    registerStatsMetric("dram", core_id, "total-remote-dram-hardware-latency-cachelines-processing-time", &m_remote_cacheline_get_dram_access_cost_processing_time);
    registerStatsMetric("dram", core_id, "total-remote-dram-hardware-latency-cachelines-queue-delay", &m_remote_cacheline_get_dram_access_cost_queue_delay);
    registerStatsMetric("dram", core_id, "total-remote-dram-hardware-latency-pages-processing-time", &m_remote_page_get_dram_access_cost_processing_time);
    registerStatsMetric("dram", core_id, "total-remote-dram-hardware-latency-pages-queue-delay", &m_remote_page_get_dram_access_cost_queue_delay);

    // For debugging
    std::cout << "Uncompressed cacheline remote dram HW bandwidth processing time= " << m_r_dram_bus_bandwidth.getRoundedLatency(8 * m_cache_line_size).getPS() / 1000.0 << " ns, ";
    std::cout << "Uncompressed page remote dram HW bandwidth processing time= " << m_r_dram_bus_bandwidth.getRoundedLatency(8 * m_page_size).getPS() / 1000.0 << " ns" << std::endl;
}

DramHardwareCntlr::~DramHardwareCntlr()
{
    if (m_queue_model.size())
    {
        for(UInt32 channel = 0; channel < m_num_channels; ++channel)
            delete m_queue_model[channel];
    }

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
}

UInt64
DramHardwareCntlr::parseAddressBits(UInt64 address, UInt32 &data, UInt32 offset, UInt32 size, UInt64 base_address = 0)
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
DramHardwareCntlr::parseDeviceAddress(IntPtr address, UInt32 &channel, UInt32 &rank, UInt32 &bank_group, UInt32 &bank, UInt32 &column, UInt64 &dram_page)
{
    // Construct DDR address which has bits used for interleaving removed
    UInt64 linearAddress = m_address_home_lookup->getLinearAddress(address);
    UInt64 address_bits = linearAddress >> 6;
    /*address_bits = */parseAddressBits(address_bits, channel, m_channel_offset, m_num_channels, m_channel_offset < m_home_lookup_bit ? address : linearAddress);
    address_bits = parseAddressBits(address_bits, rank,    m_rank_offset,    m_num_ranks,    m_rank_offset < m_home_lookup_bit ? address : linearAddress);


    if (m_open_page_mapping) {
        // Open-page mapping: column address is bottom bits, then bank, then page
        if (m_column_offset) {
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

    if (m_randomize_address) {
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

// DRAM hardware access cost
SubsecondTime
DramHardwareCntlr::getDramWriteCost(SubsecondTime start_time, UInt64 size, core_id_t requester, IntPtr address, ShmemPerf *perf, bool is_exclude_cacheline, bool is_page)
{
    // Precondition: this method is called from remote
    SubsecondTime t_now = start_time;

    SubsecondTime ddr_processing_time;
    SubsecondTime ddr_queue_delay;
    if (is_exclude_cacheline && is_page) {
        UInt32 num_cachelines_in_page = m_page_size/m_cache_line_size;
        size = ((double)(num_cachelines_in_page - 1))/num_cachelines_in_page * size;
    }
    ddr_processing_time = m_bus_bandwidth.getRoundedLatency(8 * size); // bytes to bits
    ddr_queue_delay = m_dram_queue_model_single->computeQueueDelay(t_now, ddr_processing_time, requester);

    perf->updateTime(t_now);
    t_now += ddr_queue_delay;
    perf->updateTime(t_now, ShmemPerf::DRAM_QUEUE);
    t_now += ddr_processing_time;
    perf->updateTime(t_now, ShmemPerf::DRAM_BUS);
    t_now += m_dram_hw_fixed_latency;
    perf->updateTime(t_now, ShmemPerf::DRAM_DEVICE);

    return t_now - start_time;  // Net increase of time, ie the pure hardware access cost
}

// DRAM hardware access cost
SubsecondTime
DramHardwareCntlr::getDramAccessCost(SubsecondTime start_time, UInt64 size, core_id_t requester, IntPtr address, ShmemPerf *perf, bool is_remote, bool is_exclude_cacheline, bool is_page)
{
    if (m_use_detailed_cost_calculation)
        return getDramAccessCostDetailed(start_time, size, requester, address, perf, is_remote, is_exclude_cacheline, is_page);

    return getDramAccessCostSimple(start_time, size, requester, address, perf, is_remote, is_exclude_cacheline, is_page);
}

SubsecondTime
DramHardwareCntlr::getDramAccessCostSimple(SubsecondTime start_time, UInt64 size, core_id_t requester, IntPtr address, ShmemPerf *perf, bool is_remote, bool is_exclude_cacheline, bool is_page)
{
    SubsecondTime t_now = start_time;

    SubsecondTime ddr_processing_time;
    SubsecondTime ddr_queue_delay;
    if (is_exclude_cacheline && is_page) {
        UInt32 num_cachelines_in_page = m_page_size/m_cache_line_size;
        size = ((double)(num_cachelines_in_page - 1))/num_cachelines_in_page * size;
    }
    if (is_remote) {
        ddr_processing_time = m_r_dram_bus_bandwidth.getRoundedLatency(8 * size); // bytes to bits
        ddr_queue_delay = m_r_dram_queue_model_single->computeQueueDelay(t_now, ddr_processing_time, requester);
        if (is_page) {
            m_remote_page_get_dram_access_cost_processing_time += ddr_processing_time;
            m_remote_page_get_dram_access_cost_queue_delay += ddr_queue_delay;

            // Debug: Add extra dram access cost if page
            t_now += m_r_added_dram_access_cost;
            perf->updateTime(t_now);
        } else {
            // This is a cacheline
            if (m_r_pq_cacheline_hw_no_queue_delay && m_r_partition_queues) {
                ddr_queue_delay = SubsecondTime::Zero();  // option to remove hw queue delay from cachelines when PQ=on, to simulate prioritized cachelines
            }
            m_remote_cacheline_get_dram_access_cost_processing_time += ddr_processing_time;
            m_remote_cacheline_get_dram_access_cost_queue_delay += ddr_queue_delay;
        }
    } else {
        ddr_processing_time = m_bus_bandwidth.getRoundedLatency(8 * size); // bytes to bits
        ddr_queue_delay = m_dram_queue_model_single->computeQueueDelay(t_now, ddr_processing_time, requester);
        m_local_get_dram_access_cost_processing_time += ddr_processing_time;
        m_local_get_dram_access_cost_queue_delay += ddr_queue_delay;
    }

    perf->updateTime(t_now);
    t_now += ddr_queue_delay;
    perf->updateTime(t_now, ShmemPerf::DRAM_QUEUE);
    t_now += ddr_processing_time;
    perf->updateTime(t_now, ShmemPerf::DRAM_BUS);
    t_now += m_dram_hw_fixed_latency;
    perf->updateTime(t_now, ShmemPerf::DRAM_DEVICE);

    return t_now - start_time;  // Net increase of time, ie the pure hardware access cost
}

SubsecondTime
DramHardwareCntlr::getDramAccessCostDetailed(SubsecondTime start_time, UInt64 size, core_id_t requester, IntPtr address, ShmemPerf *perf, bool is_remote, bool is_exclude_cacheline, bool is_page)
{
    UInt64 phys_page = address & ~((UInt64(1) << floorLog2(m_page_size)) - 1);
    IntPtr cacheline_address = (size > m_cache_line_size) ? phys_page : address & ~((UInt64(1) << floorLog2(m_cache_line_size)) - 1);
    IntPtr actual_data_cacheline_address = address & ~((UInt64(1) << floorLog2(m_cache_line_size)) - 1);
    SubsecondTime t_now = start_time;

    for (UInt32 i = 0; i < size / m_cache_line_size; i++) {
        if (is_exclude_cacheline && cacheline_address == actual_data_cacheline_address)
            continue;

        // Calculate address mapping inside the DIMM
        UInt32 channel, rank, bank_group, bank, column;
        UInt64 dram_page;
        parseDeviceAddress(cacheline_address, channel, rank, bank_group, bank, column, dram_page);

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


        std::vector<QueueModel *> rank_avail = (is_remote) ? m_r_rank_avail : m_rank_avail;
        std::vector<QueueModel *> bank_group_avail = (is_remote) ? m_r_bank_group_avail : m_bank_group_avail;
        std::vector<QueueModel *> queue_model = (is_remote) ? m_r_queue_model : m_queue_model;

        // Add rank access time and availability
        UInt64 cr = (channel * m_num_ranks) + rank;
        LOG_ASSERT_ERROR(cr < m_total_ranks, "Rank index out of bounds");
        SubsecondTime rank_avail_request = (m_num_bank_groups > 1) ? m_intercommand_delay_short : m_intercommand_delay;
        SubsecondTime rank_avail_delay = rank_avail.size() ? rank_avail[cr]->computeQueueDelay(t_now, rank_avail_request, requester) : SubsecondTime::Zero();

        // Add bank group access time and availability
        UInt64 crbg = (channel * m_num_ranks * m_num_bank_groups) + (rank * m_num_bank_groups) + bank_group;
        LOG_ASSERT_ERROR(crbg < m_total_bank_groups, "Bank-group index out of bounds");
        SubsecondTime group_avail_delay = bank_group_avail.size() ? bank_group_avail[crbg]->computeQueueDelay(t_now, m_intercommand_delay_long, requester) : SubsecondTime::Zero();

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
        SubsecondTime ddr_processing_time = m_bus_bandwidth.getRoundedLatency(8 * m_cache_line_size); // bytes to bits
        SubsecondTime ddr_queue_delay = queue_model.size() ? queue_model[channel]->computeQueueDelay(t_now, ddr_processing_time, requester) : SubsecondTime::Zero();
        t_now += ddr_queue_delay;
        perf->updateTime(t_now, ShmemPerf::DRAM_QUEUE);

    }

    return t_now - start_time;  // Net increase of time, ie the pure hardware access cost
}