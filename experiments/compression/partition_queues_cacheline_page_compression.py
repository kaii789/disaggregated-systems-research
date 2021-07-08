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
import sniper_lib
import run_sniper_repeat_base as automation

# Sweep BW 4, 32
# Test P1C0, P1C1 no cacheline ideal, P1C1 cacheline ideal, P1C1 no cacheline, P1C1 cacheline
config_list = [
    # 1) Compression Off
    automation.ExperimentRunConfig(
        [
            automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
            automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
        ]
    ),
    # 2) Page Compression(ideal)
    automation.ExperimentRunConfig(
        [
            automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
            automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
            automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
            automation.ConfigEntry("perf_model/dram/compression_model/lz4", "compression_latency", "0"),
            automation.ConfigEntry("perf_model/dram/compression_model/lz4", "decompression_latency", "0"),
        ]
    ),
    # 3) Cacheline + Page Compression(ideal)
    automation.ExperimentRunConfig(
        [
            automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
            automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
            automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "true"),
            automation.ConfigEntry("perf_model/dram/compression_model/lz4", "compression_latency", "0"),
            automation.ConfigEntry("perf_model/dram/compression_model/lz4", "decompression_latency", "0"),
        ]
    ),
    # 4) Page Compression
    automation.ExperimentRunConfig(
        [
            automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
            automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
            automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
        ]
    ),
    # 5) Cacheline + Page Compression
    automation.ExperimentRunConfig(
        [
            automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
            automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
            automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "true"),
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

# Previous test strings; assumes the program is compiled
command_str1a_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -n 1 -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/test/a_disagg_test/mem_test".format(
    sniper_root=subfolder_sniper_root_relpath
)
command_str1b_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -n 1 -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/test/a_disagg_test/mem_test_varied".format(
    sniper_root=subfolder_sniper_root_relpath
)
command_str2a_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/test/crono/apps/sssp/sssp {sniper_root}/test/crono/inputs/bcsstk05.mtx 1".format(
    sniper_root=subfolder_sniper_root_relpath
)
command_str2b_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/test/crono/apps/sssp/sssp {sniper_root}/test/crono/inputs/bcsstk25.mtx 1".format(
    sniper_root=subfolder_sniper_root_relpath
)
command_str2c_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/test/crono/apps/sssp/sssp {sniper_root}/test/crono/inputs/bcsstk32.mtx 1".format(
    sniper_root=subfolder_sniper_root_relpath
)

# Assumes input matrices are in the {sniper_root}/test/crono/inputs directory
sssp_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/test/crono/apps/sssp/sssp_pthread {sniper_root}/test/crono/inputs/{{0}} 1".format(
    sniper_root=subfolder_sniper_root_relpath
)

stream_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/stream/stream_sniper {{0}}".format(
    sniper_root=subfolder_sniper_root_relpath
)
spmv_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/spmv/bench_spdmv {sniper_root}/test/crono/inputs/{{0}} 1 1".format(
    sniper_root=subfolder_sniper_root_relpath
)

command_strs = {}

###  Darknet command strings  ###
# Note: using os.system(), the 'cd' of working directory doesn't persist to the next call to os.system()
darknet_base_str_options = "cd {1} && ../../run-sniper -d {{{{sniper_output_dir}}}} -c ../../disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/darknet classifier predict {0}/cfg/imagenet1k.data {0}/cfg/{{0}}.cfg {0}/{{0}}.weights {0}/data/dog.jpg".format(
    ".", darknet_home
)
command_strs["darknet_tiny"] = darknet_base_str_options.format(
    "tiny", sniper_options=""
)
command_strs["darknet_darknet"] = darknet_base_str_options.format(
    "darknet", sniper_options=""
)
command_strs["darknet_darknet19"] = darknet_base_str_options.format(
    "darknet19", sniper_options=""
)
command_strs["darknet_vgg-16"] = darknet_base_str_options.format(
    "vgg-16", sniper_options=""
)
command_strs["darknet_resnet50"] = darknet_base_str_options.format(
    "resnet50", sniper_options=""
)
# cd ../benchmarks/darknet && ../../run-sniper -c ../../disaggr_config/local_memory_cache.cfg -- ./darknet classifier predict ./cfg/imagenet1k.data ./cfg/tiny.cfg ./tiny.weights ./data/dog.jpg

###  Ligra command strings  ###
# Do only 1 timed round to save time during initial experiments
ligra_base_str_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/apps/{{0}} -s -rounds 1 {0}/inputs/{{1}}".format(
    ligra_home, sniper_root=subfolder_sniper_root_relpath
)
ligra_input_to_file = {
    "regular_input": "rMat_1000000",
    "small_input": "rMat_100000",
    "reg_10x": "rMat_10000000",
    "reg_8x": "rMat_8000000",
}
command_strs["ligra_bfs"] = ligra_base_str_options.format(
    "BFS", ligra_input_to_file["regular_input"], sniper_options=""
)
command_strs["ligra_pagerank"] = ligra_base_str_options.format(
    "PageRank", ligra_input_to_file["regular_input"], sniper_options=""
)

# Small input: first run some tests with smaller input size
command_strs["ligra_bfs_small_input"] = ligra_base_str_options.format(
    "BFS", ligra_input_to_file["small_input"], sniper_options=""
)
command_strs["ligra_pagerank_small_input"] = ligra_base_str_options.format(
    "PageRank", ligra_input_to_file["small_input"], sniper_options=""
)
# ../run-sniper -c ../disaggr_config/local_memory_cache.cfg -- ../benchmarks/ligra/apps/BFS -s ../benchmarks/ligra/inputs/rMat_1000000

# Stop around 100 Million instructions after entering ROI (magic = true in config so don't need --roi flag)
command_strs["ligra_bfs_instrs_100mil"] = ligra_base_str_options.format(
    "BFS",
    ligra_input_to_file["regular_input"],
    sniper_options="-s stop-by-icount:{}".format(100 * ONE_MILLION),
)

# 8 MB for ligra_bfs + rMat_1000000
command_strs["ligra_bfs_localdram_8MB"] = ligra_base_str_options.format(
    "BFS",
    ligra_input_to_file["regular_input"],
    sniper_options="-g perf_model/dram/localdram_size={}".format(
        int(8 * ONE_MB_TO_BYTES)
    ),
)
# 1 MB for ligra_bfs + rMat_100000
command_strs["ligra_bfs_small_input_localdram_1MB"] = ligra_base_str_options.format(
    "BFS",
    ligra_input_to_file["small_input"],
    sniper_options="-g perf_model/dram/localdram_size={}".format(
        int(1 * ONE_MB_TO_BYTES)
    ),
)


# TODO: BFS, 8 MB
def run_bfs(ligra_input_selection, num_MB):
    experiments = []
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    net_lat = 120
    for remote_init in ["false"]:  # "false"
        for bw_scalefactor in [4, 32]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = ligra_base_str_options.format(
                application_name,
                ligra_input_file,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                    int(num_MB * ONE_MB_TO_BYTES),
                    int(net_lat),
                    int(bw_scalefactor),
                    str(remote_init),
                ),
            )

            experiments.append(
                automation.Experiment(
                    experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_combo".format(
                        application_name.lower(),
                        ""
                        if ligra_input_selection == "regular_input"
                        else ligra_input_selection + "_",
                        localdram_size_str,
                        net_lat,
                        bw_scalefactor,
                    ),
                    command_str=command_str,
                    experiment_run_configs=config_list,
                    output_root_directory=".",
                )
            )

    return experiments


# TODO: Darknet tiny, 2 MB
def run_tinynet(model_type):
    experiments = []
    net_lat = 120
    for num_MB in [2]:
        for bw_scalefactor in [4, 32]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = darknet_base_str_options.format(
                model_type,
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
                    experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_combo".format(
                        model_type.lower(), localdram_size_str, net_lat, bw_scalefactor
                    ),
                    command_str=command_str,
                    experiment_run_configs=config_list,
                    output_root_directory=".",
                )
            )

    return experiments


# TODO: Stream, 2 MB
def run_stream(type):
    experiments = []
    net_lat = 120
    for num_MB in [2]:
        for bw_scalefactor in [4, 32]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = stream_base_options.format(
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
                    experiment_name="stream_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_combo".format(
                        type, localdram_size_str, net_lat, bw_scalefactor
                    ),
                    command_str=command_str,
                    experiment_run_configs=config_list,
                    output_root_directory=".",
                )
            )

    return experiments


# TODO: sssp 256KB
def run_sssp(input):
    experiments = []
    net_lat = 120
    for remote_init in ["true"]:  # "false"
        for num_B in [262144]:
            for bw_scalefactor in [4, 32]:
                localdram_size_str = "{}B".format(num_B)
                command_str = sssp_base_options.format(
                    input,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                        int(num_B),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                    ),
                )

                experiments.append(
                    automation.Experiment(
                        experiment_name="sssp_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_pq_cacheline_combined_series".format(
                            input,
                            localdram_size_str,
                            net_lat,
                            bw_scalefactor,
                            remote_init,
                        ),
                        command_str=command_str,
                        experiment_run_configs=config_list,
                        output_root_directory=".",
                    )
                )

    return experiments

experiments = []
# experiments.extend(run_bfs("regular_input", 8))
# experiments.extend(run_tinynet("tiny"))
# experiments.extend(run_tinynet("darknet19"))
# experiments.extend(run_stream("0")) # Scale

# experiments.extend(run_sssp("bcsstk05.mtx"))
# experiments.extend(run_bfs("reg_8x", 32))
# experiments.extend(run_tinynet("resnet50"))

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