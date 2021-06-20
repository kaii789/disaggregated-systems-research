#!/usr/bin/env python
import pandas as pd
import numpy as np
import matplotlib as plt
plt.use('Agg')
import os
import subprocess
import threading

import sys
sys.path.insert(1, '../../tools')
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

def log_compression_stats(res_directory, result_filename, program_command, config_param, val):
    res = sniper_lib.get_results(resultsdir=res_directory)
    results = res['results']
    config = res['config']

    # Compression
    bytes_saved = results['compression.bytes-saved'][0] if 'compression.bytes-saved' in results else 0
    if bytes_saved != 0:
        data_moves = results['dram.data-moves'][0]
        total_compression_latency = results['compression.total-compression-latency'][0] / 10**6 # convert to ns
        total_decompression_latency = results['compression.total-decompression-latency'][0] / 10**6 # convert to ns

        gran_size = 64 if config['perf_model/dram/remote_use_cacheline_granularity'] == "true" else 4096
        avg_compression_ratio = float((data_moves * gran_size)) / float(((data_moves * gran_size) - bytes_saved))
        avg_compression_latency = total_compression_latency / data_moves
        avg_decompression_latency = total_decompression_latency / data_moves

        f = open(result_filename, "a")
        f.write("Program Command: {}\n".format(program_command))
        f.write("Config Param: {}, Val: {}\n".format(config_param, val))
        f.write("Data Moves: {}\n".format(data_moves))
        f.write("Bytes Saved: {}\n".format(bytes_saved))
        f.write("Average Compression Ratio: {}\n".format(avg_compression_ratio))
        f.write("Average Compression Latency(ns): {}\n".format(avg_compression_latency))
        f.write("Average Decompression Latency(ns): {}\n\n".format(avg_decompression_latency))
        f.close()


def run_experiment(x_axis, x_axis_init, result_filename, config_name, config_param, program_command, cwd):

    data = {x_axis:x_axis_init,
            'IPC':[]}

    for val in x_axis_init:
        run_directory = "./{}-{}-{}".format(result_filename, config_param.split("/")[-1], val)
        sniper_path = os.path.abspath("../../run-sniper")
        output_directory = os.path.abspath("./{}".format(run_directory))
        if not cwd: cwd = run_directory
        command = "{} -v -n 1 -c {} -g --{}={} -d {} -- {}".format(sniper_path, config_name, config_param, val, output_directory, program_command)
        subprocess.call("mkdir {}".format(run_directory), shell=True)
        subprocess.call(command, shell=True, cwd=cwd)
        ipc = get_ipc(run_directory)
        print(ipc)
        data['IPC'].append(ipc)
        log_compression_stats(run_directory, "{}.log".format(result_filename), program_command, config_param, val)
        # subprocess.call("rm -r {}".format(run_directory), shell=True)

    # df = pd.DataFrame(data)
    # graph = df.plot(x=x_axis, y="IPC")
    # fig = graph.get_figure()
    # fig.savefig(result_filename)

    return data['IPC']

def thread_experiment(x_axis, x_axis_init, result_filename, config_name, config_param, program_command, res, cwd
):
    experiment_res = run_experiment(x_axis, x_axis_init, result_filename, config_name, config_param, program_command, cwd) # "{}-{}".format(result_filename, program_command)
    res.append(experiment_res)

def run_compression_queue_experiment(x_axis, x_axis_label, x_axis_config_param, program_command, result_name, cwd=None
):
    # Multithread
    res1, res2, res3 = [], [], []
    t1 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "c0p0", os.path.abspath("./no_compression_no_partition_queues"), x_axis_config_param, program_command, res1, cwd))
    t2 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "c0p1", os.path.abspath("./no_compression_yes_partition_queues"), x_axis_config_param, program_command, res2, cwd))
    t3 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "c1p1", os.path.abspath("./yes_compression_yes_partition_queues"), x_axis_config_param, program_command, res3, cwd))

    for t in [t1, t2, t3]:
        t.start()

    for t in [t1, t2, t3]:
        t.join()

    no_compression_no_partition_queues = res1[0]
    no_compression_yes_partition_queues = res2[0]
    yes_compression_yes_partition_queues = res3[0]

    # Single Thread
    # no_compression_no_partition_queues = run_experiment(x_axis_label, bandwidth_scalefactor, None, "no_compression_no_partition_queues", x_axis_config_param, program_command)
    # no_compression_yes_partition_queues = run_experiment(x_axis_label, bandwidth_scalefactor, None, "no_compression_yes_partition_queues", x_axis_config_param, program_command)
    # yes_compression_yes_partition_queues = run_experiment(x_axis_label, bandwidth_scalefactor, None, "yes_compression_yes_partition_queues", x_axis_config_param, program_command)

    data = {
        x_axis_label: x_axis,
        'C: Off, P: Off': no_compression_no_partition_queues,
        'C: Off, P: On': no_compression_yes_partition_queues,
        'C: On, P: On': yes_compression_yes_partition_queues
    }
    df = pd.DataFrame(data)
    graph = df.plot(x=x_axis_label, y=["C: Off, P: Off", "C: Off, P: On", "C: On, P: On"], kind="bar")
    fig = graph.get_figure()
    fig.savefig(result_name)

if __name__ == "__main__":
    # Note: sniper is run in test/compression/{thread id}

    # IPC vs Bandwidth
    bandwidth_scalefactor = [4, 8, 16, 32]
    x_axis_label = "Remote Bandwidth Scalefactor"
    x_axis_config_param = "perf_model/dram/remote_mem_bw_scalefactor"
    # program_command = "../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/bcsstk05.mtx 1"
    # program_command = "../../../benchmarks/ligra/apps/BFS -s -rounds 1 ../../../benchmarks/ligra/inputs/rMat_1000000" # TODO: change me
    result_name = "ipc_vs_bandwidth_scalefactor_bar"
    # t1 = threading.Thread(target=run_compression_queue_experiment, args=(bandwidth_scalefactor, x_axis_label, x_axis_config_param, program_command, result_name))

    # Darknet
    program_command = "./darknet classifier predict cfg/imagenet1k.data cfg/darknet19.cfg tiny.weights data/dog.jpg" # TODO: change me
    cwd = "../../benchmarks/darknet"
    t1 = threading.Thread(target=run_compression_queue_experiment, args=(bandwidth_scalefactor, x_axis_label, x_axis_config_param, program_command, result_name, cwd))

    # IPC vs Local DRAM Size
    local_dram_size = [4194304, 8388608, 16777216, 33554432]
    # local_dram_size = [4000, 8000, 16000, 32000]
    x_axis_label = "Local DRAM Size(bytes)"
    x_axis_config_param = "perf_model/dram/localdram_size"
    program_command = "../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/bcsstk05.mtx 1"
    # program_command = "../../../benchmarks/ligra/apps/BFS -s -rounds 1 ../../../benchmarks/ligra/inputs/rMat_1000000" # TODO: change me
    result_name = "ipc_vs_local_dram_size_bar"
    # t2 = threading.Thread(target=run_compression_queue_experiment, args=(local_dram_size, x_axis_label, x_axis_config_param, program_command, result_name))

    t1.start()
    # t2.start()

