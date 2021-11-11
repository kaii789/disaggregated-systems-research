import sniper_lib
from enum import Enum, auto
from itertools import starmap

def get_ipc(res_directory):
    res = sniper_lib.get_results(resultsdir=res_directory)
    results = res['results']
    config = res['config']
    ncores = int(config['general/total_cores'])

    if 'barrier.global_time_begin' in results:
        time0_begin = results['barrier.global_time_begin']
        time0_end = results['barrier.global_time_end']

    if 'barrier.global_time' in results:
        time0 = results['barrier.global_time'][0]
    else:
        time0 = time0_begin - time0_end

    if sum(results['performance_model.instruction_count']) == 0:
        # core.instructions is less exact, but in cache-only mode it's all there is
        results['performance_model.instruction_count'] = results['core.instructions']

    results['performance_model.elapsed_time_fixed'] = [
        time0
        for c in range(ncores)
    ]
    results['performance_model.cycle_count_fixed'] = [
        results['performance_model.elapsed_time_fixed'][c] * results['fs_to_cycles_cores'][c]
        for c in range(ncores)
    ]
    results['performance_model.ipc'] = [
        i / (c or 1)
        for i, c in zip(results['performance_model.instruction_count'], results['performance_model.cycle_count_fixed'])
    ]
    return results['performance_model.ipc'][0]

def get_time(res_dir):
    # Return execution time in milliseconds
    res = sniper_lib.get_results(resultsdir=res_dir)
    results = res['results']
    config = res['config']

    ncores = int(config['general/total_cores'])
    if 'barrier.global_time_begin' in results:
        time0_begin = results['barrier.global_time_begin']
        time0_end = results['barrier.global_time_end']

    if 'barrier.global_time' in results:
        time0 = results['barrier.global_time'][0]
    else:
        time0 = time0_begin - time0_end

    results['performance_model.elapsed_time_fixed'] = [time0 for c in range(ncores)]
    return float(results['performance_model.elapsed_time_fixed'][0]) / (10 ** 12)

def get_compression_stats(res_dir):
    res = sniper_lib.get_results(resultsdir=res_dir)
    results = res['results']
    config = res['config']

    cr, cl, dl, ccr, ccl, cdl = None, None, None, None, None, None

    # Compression
    bytes_saved = results['compression.bytes-saved'][0] if 'compression.bytes-saved' in results else 0
    cacheline_bytes_saved = results['compression.cacheline-bytes-saved'][0] if 'compression.cacheline-bytes-saved' in results else 0
    if bytes_saved != 0:
        data_moves = results['dram.page-moves'][0]
        total_compression_latency = results['compression.total-compression-latency'][0] / 10**6
        total_decompression_latency = results['compression.total-decompression-latency'][0] / 10**6

        gran_size = 64 if config['perf_model/dram/remote_use_cacheline_granularity'] == "true" else 4096
        cr = float((data_moves * gran_size)) / float(((data_moves * gran_size) - bytes_saved))
        cl = total_compression_latency / data_moves
        dl = total_decompression_latency / data_moves

        if cacheline_bytes_saved != 0:
            data_moves = results['dram.remote-reads'][0] + results['dram.remote-writes'][0]
            total_cacheline_compression_latency = results['compression.total-cacheline-compression-latency'][0] / 10**6
            total_cacheline_decompression_latency = results['compression.total-cacheline-decompression-latency'][0] / 10**6

            gran_size = 64
            ccr = float((data_moves * gran_size)) / float(((data_moves * gran_size) - cacheline_bytes_saved))
            ccl = total_cacheline_compression_latency / data_moves
            cdl = total_cacheline_decompression_latency / data_moves

    return cr, cl, dl, ccr, ccl, cdl

def get_average_bw(res_dir):
    res = sniper_lib.get_results(resultsdir=res_dir)
    results = res['results']

    weighted_average = 0
    results['dram.accesses'] = list(map(sum, zip(results['dram.reads'], results['dram.writes'])))
    total_count = results['dram.accesses'][0]
    for i in range(10):
        decile_count = results["dram.bw-utilization-decile-{}".format(i)][0]
        decile_ratio = ((float)(decile_count) / (float)(total_count))
        weighted_average += decile_ratio * (float(i + (i + 1))/2/10)  # use the midpoint of the decile "bucket"

    print(weighted_average)
    return weighted_average

def get_inflight_page_stats(res_dir):
    res = sniper_lib.get_results(resultsdir=res_dir)
    results = res['results']

    total = results['dram.max-total-bufferspace']                       # max simultaneous # inflight pages, both directions (bufferspace)
    inflight = results['dram.max-inflight-bufferspace']                 # max simultaneous # inflight remote->local pages (bufferspace)
    inflight_extra = results['dram.max-inflight-extra-bufferspace']     # max simultaneous # inflight extra remote->local pages
    inflightevicted = results['dram.max-inflightevicted-bufferspace']   # max simultaneous # inflight local->remote evicted pages (bufferspace)
    return total[0], inflight[0], inflight_extra[0], inflightevicted[0]  # return stats for Core 0

def get_inflight_cacheline_stats(res_dir):
    res = sniper_lib.get_results(resultsdir=res_dir)
    results = res['results']
    results['dram.accesses'] = list(map(sum, zip(results['dram.reads'], results['dram.writes'])))

    results['dram.avg_simultaneous_inflight_cachelines_reads'] = list(starmap(lambda a,b: a/b if b else float('inf'), zip(results['dram.sum-simultaneous-inflight-cachelines-reads'], results['dram.accesses'])))
    results['dram.avg_simultaneous_inflight_cachelines_writes'] = list(starmap(lambda a,b: a/b if b else float('inf'), zip(results['dram.sum-simultaneous-inflight-cachelines-writes'], results['dram.accesses'])))
    results['dram.avg_simultaneous_inflight_cachelines_total'] = list(starmap(lambda a,b: a/b if b else float('inf'), zip(results['dram.sum-simultaneous-inflight-cachelines-total'], results['dram.accesses'])))

    avg_total = results['dram.avg_simultaneous_inflight_cachelines_total']    # avg simultaneous inflight cachelines - total
    max_total = results['dram.max-simultaneous-inflight-cachelines-total']    # max simultaneous inflight cachelines - total
    avg_reads = results['dram.avg_simultaneous_inflight_cachelines_reads']    # avg simultaneous inflight cachelines - reads
    max_reads = results['dram.max-simultaneous-inflight-cachelines-reads']    # max simultaneous inflight cachelines - reads
    avg_writes = results['dram.avg_simultaneous_inflight_cachelines_writes']  # avg simultaneous inflight cachelines - writes
    max_writes = results['dram.max-simultaneous-inflight-cachelines-writes']  # max simultaneous inflight cachelines - writes
    return avg_total[0], max_total[0], avg_reads[0], max_reads[0], avg_writes[0], max_writes[0]

class CachelineLatencies(Enum):
    DRAM_HW_READ_FIXED_LATENCY = auto()
    DRAM_HW_READ_PROCESSING_TIME = auto()
    DRAM_HW_READ_QUEUE_DELAY = auto()
    NETWORK_BW_PROCESSING_TIME = auto()
    NETWORK_BW_QUEUE_DELAY = auto()
    NETWORK_LATENCY = auto()

class PageLatencies(Enum):
    DRAM_HW_READ_FIXED_LATENCY = auto()
    DRAM_HW_READ_PROCESSING_TIME = auto()
    DRAM_HW_READ_QUEUE_DELAY = auto()
    NETWORK_BW_PROCESSING_TIME = auto()
    NETWORK_BW_QUEUE_DELAY = auto()
    NETWORK_LATENCY = auto()
    # New ones not in CachelineLatencies
    COMPRESSION_LATENCY = auto()
    DECOMPRESSION_LATENCY = auto()
    DRAM_HW_WRITE_FIXED_LATENCY = auto()
    # DRAM_HW_WRITE_PROCESSING_TIME = auto()
    # DRAM_HW_WRITE_QUEUE_DELAY = auto()
    DRAM_HW_WRITE_PROCESSING_TIME_AND_QUEUE_DELAY = auto()

def populate_latency_breakdown(res_dir, cacheline_latencies, page_latencies):
    # Assume NETWORK_LATENCY and DRAM_HW_WRITE_FIXED_LATENCY (in ns) are already prepopulated in cacheline_latencies and page_latencies
    res = sniper_lib.get_results(resultsdir=res_dir)
    results = res['results']
    config = res['config']
    ncores = int(config['general/total_cores'])
    results['dram.accesses'] = list(map(sum, zip(results['dram.reads'], results['dram.writes'])))
    if 'dram.remote-reads' in results:
        results['dram.local-reads'] = list(starmap(lambda a,b: a-b, zip(results['dram.reads'], results['dram.remote-reads'])))
    if 'dram.remote-writes' in results:
        results['dram.local-writes'] = list(starmap(lambda a,b: a-b, zip(results['dram.writes'], results['dram.remote-writes'])))
    if 'dram.remote-reads' and 'dram.remote-writes' in results:
        results['dram.remote-accesses'] = list(map(sum, zip(results['dram.remote-reads'], results['dram.remote-writes'])))
        results['dram.local-accesses'] = list(starmap(lambda a,b: a-b, zip(results['dram.accesses'], results['dram.remote-accesses'])))

    results['dram.localavghardwarelatency'] = list(starmap(lambda a,b: a/b if b else 0.0, zip(results['dram.total-local-dram-hardware-latency'], results['dram.total-local-dram-hardware-latency-count'])))
    results['dram.localavghardwarelatency_processing_time'] = list(starmap(lambda a,b: a/b if b else 0.0, zip(results['dram.total-local-dram-hardware-latency-processing-time'], results['dram.total-local-dram-hardware-latency-count'])))
    results['dram.localavghardwarelatency_queue_delay'] = list(starmap(lambda a,b: a/b if b else 0.0, zip(results['dram.total-local-dram-hardware-latency-queue-delay'], results['dram.total-local-dram-hardware-latency-count'])))

    results['dram.remoteavghardwarelatency_pages'] = list(starmap(lambda a,b: a/b if b else 0.0, zip(results['dram.total-remote-dram-hardware-latency-pages'], results['dram.total-remote-dram-hardware-latency-pages-count'])))  # Prefetched pages not currently accounted for in sniper stats
    results['dram.remoteavghardwarelatency_pages_processing_time'] = list(starmap(lambda a,b: a/b if b else 0.0, zip(results['dram.total-remote-dram-hardware-latency-pages-processing-time'], results['dram.total-remote-dram-hardware-latency-pages-count'])))  # Prefetched pages not currently accounted for in sniper stats
    results['dram.remoteavghardwarelatency_pages_queue_delay'] = list(starmap(lambda a,b: a/b if b else 0.0, zip(results['dram.total-remote-dram-hardware-latency-pages-queue-delay'], results['dram.total-remote-dram-hardware-latency-pages-count'])))  # Prefetched pages not currently accounted for in sniper stats
    page_latencies[PageLatencies.DRAM_HW_READ_PROCESSING_TIME] = results['dram.remoteavghardwarelatency_pages_processing_time'][0] / 10**6
    page_latencies[PageLatencies.DRAM_HW_READ_QUEUE_DELAY] = results['dram.remoteavghardwarelatency_pages_queue_delay'][0] / 10**6
    if page_latencies[PageLatencies.DRAM_HW_READ_PROCESSING_TIME] <= 0.0:
        page_latencies[PageLatencies.DRAM_HW_READ_FIXED_LATENCY] = 0

    results['dram.localavghardwarewritelatency_pages'] = list(starmap(lambda a,b: a/b if b else 0.0, zip(results['dram.total-local-dram-hardware-write-latency-pages'], results['dram.total-remote-dram-hardware-latency-pages-count'])))  # Prefetched pages not currently accounted for in sniper stats
    page_latencies[PageLatencies.DRAM_HW_WRITE_PROCESSING_TIME_AND_QUEUE_DELAY] = results['dram.localavghardwarewritelatency_pages'][0] / 10**6
    if page_latencies[PageLatencies.DRAM_HW_WRITE_PROCESSING_TIME_AND_QUEUE_DELAY] > 0.0:
        page_latencies[PageLatencies.DRAM_HW_WRITE_PROCESSING_TIME_AND_QUEUE_DELAY] -= page_latencies[PageLatencies.DRAM_HW_WRITE_FIXED_LATENCY]
    else:
        page_latencies[PageLatencies.DRAM_HW_WRITE_FIXED_LATENCY] = 0

    results['dram.remoteavghardwarelatency_cachelines'] = list(starmap(lambda a,b: (a)/b if b else 0.0, zip(results['dram.total-remote-dram-hardware-latency-cachelines'], results['dram.total-remote-dram-hardware-latency-cachelines-count'])))
    results['dram.remoteavghardwarelatency_cachelines_processing_time'] = list(starmap(lambda a,b: (a)/b if b else 0.0, zip(results['dram.total-remote-dram-hardware-latency-cachelines-processing-time'], results['dram.total-remote-dram-hardware-latency-cachelines-count'])))
    results['dram.remoteavghardwarelatency_cachelines_queue_delay'] = list(starmap(lambda a,b: (a)/b if b else 0.0, zip(results['dram.total-remote-dram-hardware-latency-cachelines-queue-delay'], results['dram.total-remote-dram-hardware-latency-cachelines-count'])))
    cacheline_latencies[CachelineLatencies.DRAM_HW_READ_PROCESSING_TIME] = results['dram.remoteavghardwarelatency_cachelines_processing_time'][0] / 10**6
    cacheline_latencies[CachelineLatencies.DRAM_HW_READ_QUEUE_DELAY] = results['dram.remoteavghardwarelatency_cachelines_queue_delay'][0] / 10**6
    if cacheline_latencies[CachelineLatencies.DRAM_HW_READ_PROCESSING_TIME] <= 0.0:
        cacheline_latencies[CachelineLatencies.DRAM_HW_READ_FIXED_LATENCY] = 0

    results['dram.avg_remotetolocal_cacheline_network_processing_time'] = list(starmap(lambda a,b: a/b if b else 0.0, zip(results['dram.total-network-cacheline-processing-time'], results['dram.total-remote-to-local-cacheline-move-count'])))
    results['dram.avg_remotetolocal_cacheline_network_queue_delay'] = list(starmap(lambda a,b: a/b if b else 0.0, zip(results['dram.total-network-cacheline-queue-delay'], results['dram.total-remote-to-local-cacheline-move-count'])))
    results['dram.avg_remotetolocal_page_network_processing_time'] = list(starmap(lambda a,b: a/b if b else 0.0, zip(results['dram.total-network-page-processing-time'], results['dram.total-remote-to-local-page-move-count'])))
    results['dram.avg_remotetolocal_page_network_queue_delay'] = list(starmap(lambda a,b: a/b if b else 0.0, zip(results['dram.total-network-page-queue-delay'], results['dram.total-remote-to-local-page-move-count'])))
    cacheline_latencies[CachelineLatencies.NETWORK_BW_PROCESSING_TIME] = results['dram.avg_remotetolocal_cacheline_network_processing_time'][0] / 10**6
    cacheline_latencies[CachelineLatencies.NETWORK_BW_QUEUE_DELAY] = results['dram.avg_remotetolocal_cacheline_network_queue_delay'][0] / 10**6
    if cacheline_latencies[CachelineLatencies.NETWORK_BW_QUEUE_DELAY] > 0.0:
        cacheline_latencies[CachelineLatencies.NETWORK_BW_QUEUE_DELAY] -= cacheline_latencies[CachelineLatencies.NETWORK_LATENCY]
    else:
        cacheline_latencies[CachelineLatencies.NETWORK_LATENCY] = 0
    page_latencies[PageLatencies.NETWORK_BW_PROCESSING_TIME] = results['dram.avg_remotetolocal_page_network_processing_time'][0] / 10**6
    page_latencies[PageLatencies.NETWORK_BW_QUEUE_DELAY] = results['dram.avg_remotetolocal_page_network_queue_delay'][0] / 10**6
    if page_latencies[PageLatencies.NETWORK_BW_QUEUE_DELAY] > 0.0:
        page_latencies[PageLatencies.NETWORK_BW_QUEUE_DELAY] -= page_latencies[PageLatencies.NETWORK_LATENCY]
    else:
        page_latencies[PageLatencies.NETWORK_LATENCY] = 0

    results['dram.remoteavglatency'] = list(starmap(lambda a,b: a/b if b else float('inf'), zip(results['dram.total-remote-access-latency'], results['dram.remote-accesses'])))
    results['dram.remote_datamovement_avglatency'] = list(starmap(lambda a,b: a/b if b else 0.0, zip(results['dram.total-remote-datamovement-latency'], results['dram.remote-accesses'])))

    page_latencies[PageLatencies.COMPRESSION_LATENCY] = None
    page_latencies[PageLatencies.DECOMPRESSION_LATENCY] = None
    # Compression
    bytes_saved = results['compression.bytes-saved'][0] if 'compression.bytes-saved' in results else 0
    if bytes_saved != 0:
        data_moves = results['dram.page-moves'][0]
        total_compression_latency = results['compression.total-compression-latency'][0]
        total_decompression_latency = results['compression.total-decompression-latency'][0]

        gran_size = 64 if config['perf_model/dram/remote_use_cacheline_granularity'] == "true" else int(config['perf_model/dram/page_size'])
        results['compression.avg-compression-ratio'] = [float((data_moves * gran_size)) / float(((data_moves * gran_size) - bytes_saved))] + [0]*(ncores - 1)
        results['compression.avg-compression-latency'] = [total_compression_latency / data_moves] + [0]*(ncores - 1)
        results['compression.avg-decompression-latency'] = [total_decompression_latency / data_moves] + [0]*(ncores - 1)

        page_latencies[PageLatencies.COMPRESSION_LATENCY] = results['compression.avg-compression-latency'][0] / 10**6
        page_latencies[PageLatencies.DECOMPRESSION_LATENCY] = results['compression.avg-decompression-latency'][0] / 10**6

    return cacheline_latencies, page_latencies