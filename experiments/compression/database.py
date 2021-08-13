#!/usr/bin/env python3

import pandas as pd
import numpy as np
import matplotlib as plt
plt.use('Agg')
import os
import subprocess
import threading

import sys
sys.path.insert(1, '../../disaggr_scripts')
import stats
import run_sniper_repeat_base as automation

baseline_config_list = [
    # 1 Remote off
    automation.ExperimentRunConfig(
        [
            automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
            automation.ConfigEntry("perf_model/dram", "enable_remote_mem", "false"),
            automation.ConfigEntry("perf_model/dram", "localdram_size", "16777216000"),
        ]
    ),
]

config_list = [
    automation.ExperimentRunConfig(
        [
            automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
            automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
            automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
        ]
    ),
]

# TODO: Temp
# Relative to directory where command_str will be executed, ie subfolder of subfolder of this file's containing directory
subfolder_sniper_root_relpath = "../../../.."
# Relative to subfolder of disaggr_scripts directory
darknet_home = "{sniper_root}/benchmarks/darknet".format(
    sniper_root=subfolder_sniper_root_relpath
)
ligra_home = "{sniper_root}/benchmarks/ligra".format(
    sniper_root=subfolder_sniper_root_relpath
)
ONE_MILLION = 1000000              # eg to specify how many instructions to run
ONE_BILLION = 1000 * ONE_MILLION   # eg to specify how many instructions to run
ONE_MB_TO_BYTES = 1024 * 1024      # eg to specify localdram_size


# sql_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- sqlite3 {sniper_root}/benchmarks/tpch-kit/dbgen/tpch.db < {sniper_root}/benchmarks/tpch-kit/dbgen/results/{{0}}.sql".format(
#     sniper_root=subfolder_sniper_root_relpath
# )
sql_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- sqlite3 /home/shared/tpch.db < {sniper_root}/benchmarks/tpch/in-mem-queries/{{0}}.sql".format(
    sniper_root=subfolder_sniper_root_relpath
)

command_strs = {}

def run_sql(type):
    experiments = []
    net_lat = 120
    for num_MB in [64]:
        for bw_scalefactor in [4]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = sql_base_options.format(
                type,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                    int(num_MB * ONE_MB_TO_BYTES),
                    int(net_lat),
                    int(bw_scalefactor),
                    int(1 * ONE_BILLION),
                ),
            )
            # 1 billion instructions cap

            experiments.append(
                automation.Experiment(
                    experiment_name="sql_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_combo".format(
                        type, localdram_size_str, net_lat, bw_scalefactor
                    ),
                    command_str=command_str,
                    experiment_run_configs=config_list,
                    output_root_directory=".",
                )
            )

    return experiments

def run_sql_baseline(type):
    experiments = []
    net_lat = 120
    for num_MB in [16384]:
        for bw_scalefactor in [4]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = sql_base_options.format(
                type,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                    int(num_MB * ONE_MB_TO_BYTES),
                    int(net_lat),
                    int(bw_scalefactor),
                    int(1 * ONE_BILLION),
                ),
            )
            # 1 billion instructions cap

            experiments.append(
                automation.Experiment(
                    experiment_name="sql_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_combo".format(
                        type, localdram_size_str, net_lat, bw_scalefactor
                    ),
                    command_str=command_str,
                    experiment_run_configs=baseline_config_list,
                    output_root_directory=".",
                )
            )

    return experiments


def graph(res_name, benchmark_list, local_dram_list, bw_scalefactor_list):
    labels = ["Remote Bandwidth Scalefactor", "P0C0", "P1C0", "P0C1", "P1C1"]
    # "stream_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_combo"

    process = 0
    num_bars = len(labels) - 1
    res = [bw_scalefactor_list[:]] + [[] for _ in range(num_bars)]
    compression_res = {}
    for benchmark in benchmark_list:
        for size in local_dram_list:
            for factor in bw_scalefactor_list:
                dir1 = "{}localdram_{}_netlat_120_bw_scalefactor_{}_combo_output_files".format(benchmark, size, factor)
                for run in range(1, 1 + num_bars):
                    try:
                        dir2 = "run_{}_process_{}_temp".format(run, process)
                        res_dir = "./{}/{}".format(dir1, dir2)
                        # print(res_dir)
                        ipc = stats.get_ipc(res_dir)
                        res[run].append(ipc)

                        # Compression res
                        if run in range(2, 1 + num_bars):
                            type = "{}-{}".format(run - 1, factor)
                            compression_res[type] = {}
                            cr, cl, dl, ccr, ccl, cdl = stats.get_compression_stats(res_dir)
                            compression_res[type]['Compression Ratio'] = cr
                            compression_res[type]['Compression Latency'] = cl
                            compression_res[type]['Decompression Latency'] = dl
                            if ccr:
                                compression_res[type]['Cacheline Compression Ratio'] = ccr
                                compression_res[type]['Cacheline Compression Latency'] = ccl
                                compression_res[type]['Cacheline Decompression Latency'] = cdl

                        process += 1
                    except Exception as e:
                        print(e)
                        res[run].append(0)
                        process += 1

    data = {labels[i]: res[i] for i in range(len(labels))}
    # print(data)
    print(compression_res)
    df = pd.DataFrame(data)
    graph = df.plot(x=labels[0], y=labels[1:], kind="bar", title=res_name)
    fig = graph.get_figure()
    fig.savefig(res_name)

def gen_settings_for_graph(benchmark_name):
    if benchmark_name == "sssp":
        res_name = "sssp_262144B_combo"
        benchmark_list = []
        for input in ["bcsstk05.mtx"]:
            benchmark_list.append("sssp_{}_".format(input))
        local_dram_list = ["262144B"]
        bw_scalefactor_list = [4, 16]
    if benchmark_name == "sssp_roadNet":
        res_name = "sssp_524288B_combo"
        benchmark_list = []
        for input in ["roadNet-PA.mtx"]:
            benchmark_list.append("sssp_{}_".format(input))
        local_dram_list = ["524288B"]
        bw_scalefactor_list = [4, 16]
    elif benchmark_name == "bfs_reg":
        res_name = "bfs_reg_4MB_combo"
        benchmark_list = []
        benchmark_list.append("ligra_{}_".format("bfs"))
        local_dram_list = ["4MB"]
        bw_scalefactor_list = [4, 16]
    elif benchmark_name == "triangle_reg":
        res_name = "triangle_reg_16MB_combo"
        benchmark_list = []
        benchmark_list.append("ligra_{}_".format("triangle"))
        local_dram_list = ["16MB"]
        bw_scalefactor_list = [4, 16]
    elif benchmark_name == "tinynet":
        res_name = "tinynet_2MB_combo"
        benchmark_list = []
        for model in ["tiny"]:
            benchmark_list.append("darknet_{}_".format(model))
        local_dram_list = ["2MB"]
        bw_scalefactor_list = [4, 16]
    elif benchmark_name == "darknet19":
        res_name = "tinynet_2MB_combo"
        benchmark_list = []
        for model in ["darknet19"]:
            benchmark_list.append("darknet_{}_".format(model))
        local_dram_list = ["2MB"]
        bw_scalefactor_list = [4, 16]
    elif benchmark_name == "stream_1":
        res_name = "stream_1_2MB_combo"
        benchmark_list = []
        benchmark_list.append("stream_1_")
        local_dram_list = ["2MB"]
        bw_scalefactor_list = [4, 16]
    elif benchmark_name == "sql_10":
        res_name = "sql_10_4MB_combo"
        benchmark_list = []
        benchmark_list.append("sql_10_")
        local_dram_list = ["4MB"]
        bw_scalefactor_list = [4, 16]
    elif benchmark_name == "sql_21":
        res_name = "sql_21_16MB_combo"
        benchmark_list = []
        benchmark_list.append("sql_21_")
        local_dram_list = ["16MB"]
        bw_scalefactor_list = [4, 16]
    elif benchmark_name == "sql_5":
        res_name = "sql_5_1GB-DB_16MB"
        benchmark_list = []
        benchmark_list.append("sql_5_")
        local_dram_list = ["16MB"]
        bw_scalefactor_list = [4, 16]

    return res_name, benchmark_list, local_dram_list, bw_scalefactor_list


# TODO: Experiment run
experiments = []
# experiments.extend(run_ligra("BFS", "regular_input", 4))
# experiments.extend(run_ligra("Triangle", "regular_input", 16))
# experiments.extend(run_tinynet("tiny"))
# experiments.extend(run_tinynet("darknet19"))
# experiments.extend(run_stream("0")) # Scale

# experiments.extend(run_sssp("bcsstk05.mtx"))
# experiments.extend(run_bfs("reg_8x", 32))
# experiments.extend(run_tinynet("resnet50"))

# 2 10 11 16 17 18 19 21
# Long: 17 19 21
experiments.extend(run_sql_baseline("5"))
experiments.extend(run_sql("5"))

log_filename = "run-sniper-repeat2_1.log"
num = 2
while os.path.isfile(log_filename):
    log_filename = "run-sniper-repeat2_{}.log".format(num)
    num += 1

with open(log_filename, "w") as log_file:
    log_str = "Script start time: {}".format(automation.datetime.datetime.now().astimezone())
    print(log_str)
    print(log_str, file=log_file)

    experiment_manager = automation.ExperimentManager(
        output_root_directory=".", max_concurrent_processes=16, log_file=log_file
    )
    experiment_manager.add_experiments(experiments)
    experiment_manager.start()

    log_str = "Script end time: {}".format(automation.datetime.datetime.now().astimezone())
    print(log_str)
    print(log_str, file=log_file)

# TODO: Generate graph
# res_name, benchmark_list, local_dram_list, bw_scalefactor_list = gen_settings_for_graph("sql_5")
# graph(res_name, benchmark_list, local_dram_list, bw_scalefactor_list)