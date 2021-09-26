import sniper_lib

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
