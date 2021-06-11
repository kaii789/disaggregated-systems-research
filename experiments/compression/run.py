#!/usr/bin/env python
import pandas as pd
import numpy as np
import matplotlib as plt
plt.use('Agg')
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

def run_experiment(x_axis, x_axis_init, result_filename, config_name, config_param, program_command):

    data = {x_axis:x_axis_init,
            'IPC':[]}

    for val in x_axis_init:
        command = "../../../run-sniper -v -n 1 -c {} -g --{}={} -- {}".format(config_name, config_param, val, program_command)
        tid = threading.current_thread().ident
        subprocess.call("mkdir {}".format(tid), shell=True)
        run_directory = "./{}".format(tid)
        subprocess.call(command, shell=True, cwd=run_directory)
        ipc = get_ipc(run_directory)
        print(ipc)
        data['IPC'].append(ipc)
        subprocess.call("rm -r {}".format(tid), shell=True)

    # df = pd.DataFrame(data)
    # graph = df.plot(x=x_axis, y="IPC")
    # fig = graph.get_figure()
    # fig.savefig(result_filename)

    return data['IPC']

def thread_experiment(x_axis, x_axis_init, result_filename, config_name, config_param, program_command, res):
    experiment_res = run_experiment(x_axis, x_axis_init, result_filename, config_name, config_param, program_command)
    res.append(experiment_res)

def run_compression_queue_experiment(x_axis, x_axis_label, x_axis_config_param, program_command, result_name):
    # Multithread
    res1, res2, res3 = [], [], []
    t1 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, None, "../no_compression_no_partition_queues", x_axis_config_param, program_command, res1))
    t2 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, None, "../no_compression_yes_partition_queues", x_axis_config_param, program_command, res2))
    t3 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, None, "../yes_compression_yes_partition_queues", x_axis_config_param, program_command, res3))

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
        x_axis_label: bandwidth_scalefactor,
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
    x_axis_label = "Remote Bandwidth Scalefactor(gb/s)"
    x_axis_config_param = "perf_model/dram/remote_mem_bw_scalefactor"
    # program_command = "../../../benchmarks/darknet/darknet classifier predict ../../../benchmarks/darknet/cfg/imagenet1k.data ../../../benchmarks/darknet/cfg/darknet19.cfg ../../../benchmarks/darknet/tiny.weights ../../../benchmarks/darknet/data/dog.jpg" # TODO: change me
    program_command = " ../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/bcsstk05.mtx 1" # TODO: change me
    result_name = "ipc_vs_bandwidth_scalefactor_bar"
    t1 = threading.Thread(target=run_compression_queue_experiment, args=(bandwidth_scalefactor, x_axis_label, x_axis_config_param, program_command, result_name))

    # IPC vs Local DRAM Size
    # local_dram_size = [4194304, 8388608, 16777216, 33554432]
    local_dram_size = [4000, 8000, 16000, 32000]
    x_axis_label = "Local DRAM Size(bytes)"
    x_axis_config_param = "perf_model/dram/localdram_size"
    program_command = " ../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/bcsstk05.mtx 1" # TODO: change me
    result_name = "ipc_vs_local_dram_size_bar"
    t2 = threading.Thread(target=run_compression_queue_experiment, args=(local_dram_size, x_axis_label, x_axis_config_param, program_command, result_name))

    t1.start()
    t2.start()

