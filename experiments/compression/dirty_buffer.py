#!/usr/bin/env python3

import pandas as pd
import numpy as np
import matplotlib as plt
plt.use('Agg')
import os
# For timezones
import pytz

import sys
sys.path.insert(1, '../../disaggr_scripts')
import stats
import run_sniper_repeat_base as automation

no_remote_memory_list = [
    automation.ExperimentRunConfig(
        [
            # automation.ConfigEntry("general", "magic", "false"),
            automation.ConfigEntry("perf_model/l3_cache", "cache_size", "4096"),
            automation.ConfigEntry("perf_model/dram", "enable_remote_mem", "false"),
            automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
            automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
            automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
            automation.ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
            automation.ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
            automation.ConfigEntry("perf_model/dram", "remote_init", "true"),
            # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
        ]
    ),
]

config_list = [
     # 1) No Compression
     automation.ExperimentRunConfig(
         [
             # automation.ConfigEntry("general", "magic", "false"),
             automation.ConfigEntry("perf_model/l3_cache", "cache_size", "4096"),
             automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
             automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
             automation.ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
             automation.ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
             automation.ConfigEntry("perf_model/dram", "remote_init", "true"),
             # automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
             # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
             automation.ConfigEntry("perf_model/dram", "speed_up_disagg_simulation", "true"),
         ]
     ),
    # # 2 LZBDI
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "4096"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lzbdi"),
    #         automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
    #         automation.ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
    #         automation.ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
    #         automation.ConfigEntry("perf_model/dram", "remote_init", "true"),
    #         automation.ConfigEntry("perf_model/dram", "speed_up_disagg_simulation", "true"),
    #     ]
    # ),
     # 3 Deflate
     automation.ExperimentRunConfig(
         [
             automation.ConfigEntry("perf_model/l3_cache", "cache_size", "4096"),
             automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
             automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "zlib"),
             automation.ConfigEntry("perf_model/dram/compression_model/zlib", "compression_latency", "15"),
             automation.ConfigEntry("perf_model/dram/compression_model/zlib", "decompression_latency", "15"),
             automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
             automation.ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
             automation.ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
             automation.ConfigEntry("perf_model/dram", "remote_init", "true"),
             automation.ConfigEntry("perf_model/dram", "speed_up_disagg_simulation", "true"),
         ]
     ),
    # 4 PQ On
    automation.ExperimentRunConfig(
        [
            automation.ConfigEntry("perf_model/l3_cache", "cache_size", "4096"),
            automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
            automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "4"),
            automation.ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.2"),
            automation.ConfigEntry("perf_model/dram", "use_dynamic_cacheline_queue_fraction_adjustment", "false"),
            automation.ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
            automation.ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
            automation.ConfigEntry("perf_model/dram", "remote_init", "true"),
            automation.ConfigEntry("perf_model/dram", "speed_up_disagg_simulation", "true"),
        ]
    ),
    # # 5 PQ On, Compression On: LZBDI
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "4096"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lzbdi"),
    #         automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "4"),
    #         automation.ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.2"),
    #         automation.ConfigEntry("perf_model/dram", "use_dynamic_cacheline_queue_fraction_adjustment", "false"),
    #         automation.ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
    #         automation.ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
    #         automation.ConfigEntry("perf_model/dram", "remote_init", "true"),
    #         automation.ConfigEntry("perf_model/dram", "speed_up_disagg_simulation", "true"),
    #     ]
    # ),
     # 6 PQ On, Compression On: Deflate
     automation.ExperimentRunConfig(
         [
             automation.ConfigEntry("perf_model/l3_cache", "cache_size", "4096"),
             automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
             automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "zlib"),
             automation.ConfigEntry("perf_model/dram/compression_model/zlib", "compression_latency", "15"),
             automation.ConfigEntry("perf_model/dram/compression_model/zlib", "decompression_latency", "15"),
             automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "4"),
             automation.ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.2"),
             automation.ConfigEntry("perf_model/dram", "use_dynamic_cacheline_queue_fraction_adjustment", "false"),
             automation.ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
             automation.ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
             automation.ConfigEntry("perf_model/dram", "remote_init", "true"),
             automation.ConfigEntry("perf_model/dram", "speed_up_disagg_simulation", "true"),
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

# Assumes input matrices are in the {sniper_root}/test/crono/inputs directory
sssp_int_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/crono/apps/sssp/sssp_int {sniper_root}/benchmarks/crono/inputs/{{0}} 1".format(
    sniper_root=subfolder_sniper_root_relpath
)

stream_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/stream/stream_sniper {{0}}".format(
    sniper_root=subfolder_sniper_root_relpath
)
spmv_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/spmv/bench_spdmv {sniper_root}/benchmarks/crono/inputs/{{0}} 1 1".format(
    sniper_root=subfolder_sniper_root_relpath
)
nw_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/rodinia/bin/needle {{0}} 1 1".format(
    sniper_root=subfolder_sniper_root_relpath
)
hpcg_base_options = "cp {sniper_root}/benchmarks/hpcg/linux_serial/bin/hpcg.dat .;{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/hpcg/linux_serial/bin/xhpcg".format(
    sniper_root=subfolder_sniper_root_relpath
)
sls_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/sls/bin/sls -f /home/shared/sls.in".format(
    sniper_root=subfolder_sniper_root_relpath
)
sql_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- sqlite3 /home/shared/tpch.db < {sniper_root}/benchmarks/tpch/in-mem-queries/{{0}}.sql".format(
    sniper_root=subfolder_sniper_root_relpath
)

command_strs = {}

###  Darknet command strings  ###
# Note: using os.system(), the 'cd' of working directory doesn't persist to the next call to os.system()
darknet_base_str_options = "cd {1} && ../../run-sniper -d {{{{sniper_output_dir}}}} -c ../../disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/darknet classifier predict {0}/cfg/imagenet1k.data {0}/cfg/{{0}}.cfg {0}/{{0}}.weights {0}/data/dog.jpg && cd {{{{sniper_output_dir}}}}".format(
    ".", darknet_home
)

###  Ligra command strings  ###
# Do only 1 timed round to save time during initial experiments
# ligra_base_str_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/apps/{{0}} -s -rounds 1 {0}/inputs/{{1}}".format(
#     ligra_home, sniper_root=subfolder_sniper_root_relpath
# )
ligra_base_str_options_sym = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/apps/{{0}} -s -rounds 1 {0}/inputs/{{1}}".format(
        ligra_home, sniper_root=subfolder_sniper_root_relpath
    )
ligra_base_str_options_nonsym = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/apps/{{0}} -rounds 1 {0}/inputs/{{1}}".format(
    ligra_home, sniper_root=subfolder_sniper_root_relpath
)
ligra_input_to_file = {
    "regular_input": "rMat_1000000",
    # "small_input": "rMat_100000",
    # "reg_10x": "rMat_10000000",
    # "reg_8x": "rMat_8000000",
    "regular_input_sym": "rMat_1000000sym",
}

# TODO:
# page_size_list = [4096, 512, 1024, 2048, 64]
# bw_scalefactor_list = [1.536, 4, 16]
# netlat_list = [120, 400, 880, 1000, 1600]
page_size_list = [4096]
remote_dram_bus_scalefactor_list = [1]
bw_scalefactor_list = [4, 8]
netlat_list = [100, 400] # 120

def input_file_checker(experiments):
    # Temporary function
    # Assumes the cwd is this file's containing directory
    input_to_file_path = {"roadnetPA": ["{sniper_root}/benchmarks/crono/inputs/roadNet-PA.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                            "roadnetCA": ["{sniper_root}/benchmarks/crono/inputs/roadNet-CA.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                            "bcsstk32": ["{sniper_root}/benchmarks/crono/inputs/bcsstk32.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                            "citPatents": ["{sniper_root}/benchmarks/crono/inputs/cit-Patents.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                            "socPokec": ["{sniper_root}/benchmarks/crono/inputs/soc-Pokec.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                            "comOrkut": ["{sniper_root}/benchmarks/crono/inputs/com-Orkut.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                            "pkustk14": ["{sniper_root}/benchmarks/crono/inputs/pkustk14.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                        #   "small_input": ["{0}/inputs/{1}".format(ligra_home, ligra_input_to_file["small_input"])],
                            # "reg_8x": ["{0}/inputs/{1}".format(ligra_home, ligra_input_to_file["reg_8x"])],
                            # "reg_10x": ["{0}/inputs/{1}".format(ligra_home, ligra_input_to_file["reg_10x"])],
                            "regular_input_sym": ["{0}/inputs/{1}".format(ligra_home, ligra_input_to_file["regular_input_sym"])],
                            "ligra": ["{0}/inputs/{1}".format(ligra_home, ligra_input_to_file["regular_input"])],
                            "darknet_tiny": ["{0}/{1}.weights".format(darknet_home, "tiny"), "{0}/cfg/{1}.cfg".format(darknet_home, "tiny"), "{0}/cfg/imagenet1k.data".format(darknet_home), "{0}/data/dog.jpg".format(darknet_home)],
                            "darknet_darknet19": ["{0}/{1}.weights".format(darknet_home, "darknet19"), "{0}/cfg/{1}.cfg".format(darknet_home, "darknet19"), "{0}/cfg/imagenet1k.data".format(darknet_home), "{0}/data/dog.jpg".format(darknet_home)],
                            "darknet_resnet50": ["{0}/{1}.weights".format(darknet_home, "resnet50"), "{0}/cfg/{1}.cfg".format(darknet_home, "resnet50"), "{0}/cfg/imagenet1k.data".format(darknet_home), "{0}/data/dog.jpg".format(darknet_home)],
                            "darknet_vgg16": ["{0}/{1}.weights".format(darknet_home, "vgg-16"), "{0}/cfg/{1}.cfg".format(darknet_home, "vgg-16"), "{0}/cfg/imagenet1k.data".format(darknet_home), "{0}/data/dog.jpg".format(darknet_home)],
                            "darknet_resnet152": ["{0}/{1}.weights".format(darknet_home, "resnet152"), "{0}/cfg/{1}.cfg".format(darknet_home, "resnet152"), "{0}/cfg/imagenet1k.data".format(darknet_home), "{0}/data/dog.jpg".format(darknet_home)],
                            "darknet_yolov3": ["{0}/{1}.weights".format(darknet_home, "yolov3"), "{0}/cfg/{1}.cfg".format(darknet_home, "yolov3"), "{0}/cfg/imagenet1k.data".format(darknet_home), "{0}/data/dog.jpg".format(darknet_home)],
                            "stream": [],  # stream doesn't need an input file
                            "nw": [],  # stream doesn't need an input file
                            "sls": ["/home/shared/sls.in"],
                            "hpcg": ["{sniper_root}/benchmarks/hpcg/linux_serial/bin/hpcg.dat".format(sniper_root=subfolder_sniper_root_relpath)], 
                            "sql_5": ["/home/shared/tpch.db", "{sniper_root}/benchmarks/tpch/in-mem-queries/5.sql".format(sniper_root=subfolder_sniper_root_relpath)],  # TPCH
                            }
    input_missing = False
    for experiment in experiments:
        found = False
        for key in input_to_file_path.keys():
            if key.lower() in experiment.experiment_name.lower():
                found = True
                for file_path in input_to_file_path[key]:
                    full_file_path = file_path if file_path.startswith("/") else os.path.relpath(file_path, start="../..")
                    if not os.path.exists(full_file_path):
                        print("Error: couldn't find input {} at {}".format(key, full_file_path))
                        input_missing = True
                break
        if not found:
            print("{} didn't match any of the input file patterns".format(experiment.experiment_name))
    if input_missing:
        raise FileNotFoundError()

# Ligra
def run_ligra_nonsym(application_name):
    ligra_input_selection = "regular_input"
    experiments = []
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    app_to_local_dram_size = {
        "BFS": [20],
        "BC": [29],
        "Components": [26],
        "PageRank": [16],
        "MIS": [20],
        "Radii": [30],
    }
    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat = 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = ligra_base_str_options_nonsym.format(
        application_name,
        ligra_input_file,
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            float(bw_scalefactor),
            int(1 * ONE_BILLION),
        ),
    )
    experiments.append(
        automation.Experiment(
            experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_noremotemem".format(
                application_name.lower(),
                ""
                if ligra_input_selection == "regular_input"
                else ligra_input_selection + "_",
                localdram_size_str,
                net_lat,
                bw_scalefactor,
                page_size
            ),
            command_str=command_str,
            experiment_run_configs=no_remote_memory_list,
            output_root_directory=".",
        )
    )
    # Everything else
    for num_MB in app_to_local_dram_size[application_name]:
        for page_size in page_size_list:
            for net_lat in netlat_list:
                for bw_scalefactor in bw_scalefactor_list:
                    for rbus_scalefactor in remote_dram_bus_scalefactor_list:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = ligra_base_str_options_nonsym.format(
                            application_name,
                            ligra_input_file,
                            sniper_options="-g perf_model/dram/remote_dram_bus_scalefactor={} -g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                                rbus_scalefactor,
                                page_size,
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                float(bw_scalefactor),
                                int(1 * ONE_BILLION),
                            ),
                        )

                        experiments.append(
                            automation.Experiment(
                                experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_rbus_scalefactor_{}_combo".format(
                                    application_name.lower(),
                                    ""
                                    if ligra_input_selection == "regular_input"
                                    else ligra_input_selection + "_",
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    page_size,
                                    rbus_scalefactor
                                ),
                                command_str=command_str,
                                experiment_run_configs=config_list,
                                output_root_directory=".",
                                start_experiment_no=1,
                            )
                        )

    return experiments

def run_ligra_sym(application_name):
    ligra_input_selection = "regular_input_sym"
    experiments = []
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    app_to_local_dram_size = {
        "Triangle": [30],
        "KCore": [12],
    }
    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat = 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = ligra_base_str_options_sym.format(
        application_name,
        ligra_input_file,
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            float(bw_scalefactor),
            int(1 * ONE_BILLION),
        ),
    )
    experiments.append(
        automation.Experiment(
            experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_noremotemem".format(
                application_name.lower(),
                ""
                if ligra_input_selection == "regular_input"
                else ligra_input_selection + "_",
                localdram_size_str,
                net_lat,
                bw_scalefactor,
                page_size
            ),
            command_str=command_str,
            experiment_run_configs=no_remote_memory_list,
            output_root_directory=".",
        )
    )
    # Everything else
    for num_MB in app_to_local_dram_size[application_name]:
        for page_size in page_size_list:
            for net_lat in netlat_list:
                for bw_scalefactor in bw_scalefactor_list:
                    for rbus_scalefactor in remote_dram_bus_scalefactor_list:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = ligra_base_str_options_sym.format(
                            application_name,
                            ligra_input_file,
                            sniper_options="-g perf_model/dram/remote_dram_bus_scalefactor={} -g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                                rbus_scalefactor,
                                page_size,
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                float(bw_scalefactor),
                                int(1 * ONE_BILLION),
                            ),
                        )

                        experiments.append(
                            automation.Experiment(
                                experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_rbus_scalefactor_{}_combo".format(
                                    application_name.lower(),
                                    ""
                                    if ligra_input_selection == "regular_input"
                                    else ligra_input_selection + "_",
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    page_size,
                                    rbus_scalefactor
                                ),
                                command_str=command_str,
                                experiment_run_configs=config_list,
                                output_root_directory=".",
                                start_experiment_no=1,
                            )
                        )

    return experiments


def run_darknet(model_type):
    experiments = []

    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat = 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = darknet_base_str_options.format(
        model_type,
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            float(bw_scalefactor),
            int(1 * ONE_BILLION),
        ),
    )
    experiments.append(
        automation.Experiment(
            experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_noremotemem".format(
                model_type.lower().replace("-", ""), localdram_size_str, net_lat, bw_scalefactor, page_size
            ),
            command_str=command_str,
            experiment_run_configs=no_remote_memory_list,
            output_root_directory=".",
        )
    )

    # Everything else
    model_to_local_dram_size = {
        "darknet19": [11],
        "resnet50": [8],
        "resnet152": [8],
        "vgg-16": [24],
        "yolov3": [27]
    }
    for num_MB in model_to_local_dram_size[model_type]:
        for page_size in page_size_list:
            for net_lat in netlat_list:
                for bw_scalefactor in bw_scalefactor_list:
                    for rbus_scalefactor in remote_dram_bus_scalefactor_list:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = darknet_base_str_options.format(
                            model_type,
                            sniper_options="-g perf_model/dram/remote_dram_bus_scalefactor={} -g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                                rbus_scalefactor,
                                page_size,
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                float(bw_scalefactor),
                                int(1 * ONE_BILLION),
                            ),
                        )
                        # 1 billion instructions cap

                        experiments.append(
                            automation.Experiment(
                                experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_rbus_scalefactor_{}_combo".format(
                                    model_type.lower().replace("-", ""), localdram_size_str, net_lat, bw_scalefactor, page_size, rbus_scalefactor
                                ),
                                command_str=command_str,
                                experiment_run_configs=config_list,
                                output_root_directory=".",
                                start_experiment_no=1,
                            )
                        )


    # Everything else
    model_to_local_dram_size = {
        "darknet19": [8],
        "resnet50": [6],
        "resnet152": [6],
        "vgg-16": [12],
        "yolov3": [12]
    }
    for num_MB in model_to_local_dram_size[model_type]:
        for page_size in page_size_list:
            for net_lat in netlat_list:
                for bw_scalefactor in bw_scalefactor_list:
                    for rbus_scalefactor in remote_dram_bus_scalefactor_list:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = darknet_base_str_options.format(
                            model_type,
                            sniper_options="-g perf_model/dram/remote_dram_bus_scalefactor={} -g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                                rbus_scalefactor,
                                page_size,
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                float(bw_scalefactor),
                                int(1 * ONE_BILLION),
                            ),
                        )
                        # 1 billion instructions cap

                        experiments.append(
                            automation.Experiment(
                                experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_rbus_scalefactor_{}_combo".format(
                                    model_type.lower().replace("-", ""), localdram_size_str, net_lat, bw_scalefactor, page_size, rbus_scalefactor
                                ),
                                command_str=command_str,
                                experiment_run_configs=config_list,
                                output_root_directory=".",
                                start_experiment_no=1,
                            )
                        )


    # Everything else
    model_to_local_dram_size = {
        "darknet19": [16],
        "resnet50": [12],
        "resnet152": [8],
        "vgg-16": [28],
        "yolov3": [27]
    }
    for num_MB in model_to_local_dram_size[model_type]:
        for page_size in page_size_list:
            for net_lat in netlat_list:
                for bw_scalefactor in bw_scalefactor_list:
                    for rbus_scalefactor in remote_dram_bus_scalefactor_list:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = darknet_base_str_options.format(
                            model_type,
                            sniper_options="-g perf_model/dram/remote_dram_bus_scalefactor={} -g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                                rbus_scalefactor,
                                page_size,
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                float(bw_scalefactor),
                                int(1 * ONE_BILLION),
                            ),
                        )
                        # 1 billion instructions cap

                        experiments.append(
                            automation.Experiment(
                                experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_rbus_scalefactor_{}_combo".format(
                                    model_type.lower().replace("-", ""), localdram_size_str, net_lat, bw_scalefactor, page_size, rbus_scalefactor
                                ),
                                command_str=command_str,
                                experiment_run_configs=config_list,
                                output_root_directory=".",
                                start_experiment_no=1,
                            )
                        )



    return experiments


def run_nw(dimension):
    experiments = []
    dimension_to_local_dram_size = {
        "2048": [6],
        "4096": [26],
        "6144": [58],
    }

    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat = 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = nw_base_options.format(
        dimension,
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            float(bw_scalefactor),
            int(1 * ONE_BILLION),
        ),
    )
    experiments.append(
    automation.Experiment(
        experiment_name="nw_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_noremotemem".format(
            localdram_size_str, net_lat, bw_scalefactor, page_size
        ),
        command_str=command_str,
        experiment_run_configs=no_remote_memory_list,
        output_root_directory=".",
        )
    )

    # Everything else
    for num_MB in dimension_to_local_dram_size[dimension]:
        for page_size in page_size_list:  # put 64 byte page size in another file
            for net_lat in netlat_list:
                for bw_scalefactor in bw_scalefactor_list:
                    for rbus_scalefactor in remote_dram_bus_scalefactor_list:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = nw_base_options.format(
                            dimension,
                            sniper_options="-g perf_model/dram/remote_dram_bus_scalefactor={} -g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                                rbus_scalefactor,
                                page_size,
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                float(bw_scalefactor),
                                int(1 * ONE_BILLION),
                            ),
                        )
                        # 1 billion instructions cap

                        experiments.append(
                            automation.Experiment(
                                experiment_name="nw_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_rbus_scalefactor_{}_combo".format(
                                    localdram_size_str, net_lat, bw_scalefactor, page_size, rbus_scalefactor
                                ),
                                command_str=command_str,
                                experiment_run_configs=config_list,
                                output_root_directory=".",
                                start_experiment_no=1,
                            )
                        )

    return experiments

def run_spmv(matrix):
    experiments = []
    matrix_to_local_dram_size = {
        "pkustk14.mtx": [23],
        "socPokec.mtx": [51],
    }
    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat = 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = spmv_base_options.format(
        matrix,
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            float(bw_scalefactor),
            int(1 * ONE_BILLION),
        ),
    )
    experiments.append(
        automation.Experiment(
            experiment_name="spmv_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_noremotemem".format(
                matrix[:matrix.find(".")].replace("-", ""),
                localdram_size_str,
                net_lat,
                bw_scalefactor,
                page_size
            ),
            command_str=command_str,
            experiment_run_configs=no_remote_memory_list,
            output_root_directory=".",
        )
    )

    # Everything else
    for num_MB in matrix_to_local_dram_size[matrix]:
        for page_size in page_size_list:
            for net_lat in netlat_list:
                for bw_scalefactor in bw_scalefactor_list:
                    for rbus_scalefactor in remote_dram_bus_scalefactor_list:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = spmv_base_options.format(
                            matrix,
                            sniper_options="-g perf_model/dram/remote_dram_bus_scalefactor={} -g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                                rbus_scalefactor,
                                page_size,
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                float(bw_scalefactor),
                                int(1 * ONE_BILLION),
                            ),
                        )

                        experiments.append(
                            automation.Experiment(
                                experiment_name="spmv_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_rbus_scalefactor_{}_combo".format(
                                    matrix[:matrix.find(".")].replace("-", ""),
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    page_size,
                                    rbus_scalefactor
                                ),
                                command_str=command_str,
                                experiment_run_configs=config_list,
                                output_root_directory=".",
                                start_experiment_no=1,
                            )
                        )

    return experiments


def run_sssp_int(matrix):
    experiments = []
    matrix_to_local_dram_size = {
        "roadNet-PA.mtx": [53],
    }
    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat = 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = sssp_int_base_options.format(
        matrix,
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            float(bw_scalefactor),
            int(1 * ONE_BILLION),
        ),
    )
    experiments.append(
        automation.Experiment(
            experiment_name="sssp_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_noremotemem".format(
                matrix[:matrix.find(".")].replace("-", ""),
                localdram_size_str,
                net_lat,
                bw_scalefactor,
                page_size
            ),
            command_str=command_str,
            experiment_run_configs=no_remote_memory_list,
            output_root_directory=".",
        )
    )

    # Everything else
    for num_MB in matrix_to_local_dram_size[matrix]:
        for page_size in page_size_list:
            for net_lat in netlat_list:
                for bw_scalefactor in bw_scalefactor_list:
                    for rbus_scalefactor in remote_dram_bus_scalefactor_list:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = sssp_int_base_options.format(
                            matrix,
                            sniper_options="-g perf_model/dram/remote_dram_bus_scalefactor={} -g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                                rbus_scalefactor,
                                page_size,
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                float(bw_scalefactor),
                                int(1 * ONE_BILLION),
                            ),
                        )

                        experiments.append(
                            automation.Experiment(
                                experiment_name="sssp_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_rbus_scalefactor_{}_combo".format(
                                    matrix[:matrix.find(".")].replace("-", ""),
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    page_size,
                                    rbus_scalefactor
                                ),
                                command_str=command_str,
                                experiment_run_configs=config_list,
                                output_root_directory=".",
                                start_experiment_no=1,
                            )
                        )
    return experiments


def run_stream(type):
    experiments = []

    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat = 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = stream_base_options.format(
        type,
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            float(bw_scalefactor),
            int(1 * ONE_BILLION),
        ),
    )
    # 1 billion instructions cap
    experiments.append(
        automation.Experiment(
            experiment_name="stream_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_noremotemem".format(
                type, localdram_size_str, net_lat, bw_scalefactor, page_size
            ),
            command_str=command_str,
            experiment_run_configs=no_remote_memory_list,
            output_root_directory=".",
        )
    )

    # Everything else
    model_to_local_dram_size = {
        "1": [305],
        "3": [458],
    }
    for num_MB in model_to_local_dram_size[type]:
        for page_size in page_size_list:
            for net_lat in netlat_list:
                for bw_scalefactor in bw_scalefactor_list:
                    for rbus_scalefactor in remote_dram_bus_scalefactor_list:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = stream_base_options.format(
                            type,
                            sniper_options="-g perf_model/dram/remote_dram_bus_scalefactor={} -g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                                rbus_scalefactor,
                                page_size,
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                float(bw_scalefactor),
                                int(1 * ONE_BILLION),
                            ),
                        )
                        # 1 billion instructions cap

                        experiments.append(
                            automation.Experiment(
                                experiment_name="stream_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_rbus_scalefactor_{}_combo".format(
                                    type, localdram_size_str, net_lat, bw_scalefactor, page_size, rbus_scalefactor
                                ),
                                command_str=command_str,
                                experiment_run_configs=config_list,
                                output_root_directory=".",
                                start_experiment_no=1,
                            )
                        )

    return experiments


def run_hpcg():
    experiments = []

    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat = 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = hpcg_base_options.format(
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            float(bw_scalefactor),
            int(1 * ONE_BILLION),
        ),
    )
    # 1 billion instructions cap
    experiments.append(
        automation.Experiment(
            experiment_name="hpcgupdated_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_noremotemem".format(
                localdram_size_str, net_lat, bw_scalefactor, page_size
            ),
            command_str=command_str,
            experiment_run_configs=no_remote_memory_list,
            output_root_directory=".",
        )
    )

    # Everything else
    for num_MB in [89]:  # 89 MB for hpcgupdated
        for page_size in page_size_list:
            for net_lat in netlat_list:
                for bw_scalefactor in bw_scalefactor_list:
                    for rbus_scalefactor in remote_dram_bus_scalefactor_list:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = hpcg_base_options.format(
                            sniper_options="-g perf_model/dram/remote_dram_bus_scalefactor={} -g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                                rbus_scalefactor,
                                page_size,
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                float(bw_scalefactor),
                                int(1 * ONE_BILLION),
                            ),
                        )
                        # 1 billion instructions cap

                        experiments.append(
                            automation.Experiment(
                                experiment_name="hpcgupdated_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_rbus_scalefactor_{}_combo".format(
                                    localdram_size_str, net_lat, bw_scalefactor, page_size, rbus_scalefactor
                                ),
                                command_str=command_str,
                                experiment_run_configs=config_list,
                                output_root_directory=".",
                                start_experiment_no=1,
                            )
                        )

    return experiments

def run_sls():
    experiments = []

    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat = 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = sls_base_options.format(
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            float(bw_scalefactor),
            int(1 * ONE_BILLION),
        ),
    )
    # 1 billion instructions cap
    experiments.append(
        automation.Experiment(
            experiment_name="sls_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_noremotemem".format(
                localdram_size_str, net_lat, bw_scalefactor, page_size
            ),
            command_str=command_str,
            experiment_run_configs=no_remote_memory_list,
            output_root_directory=".",
        )
    )

    # Everything else
    for num_MB in [246]:  # 246 MB for SLS
        for page_size in page_size_list:
            for net_lat in netlat_list:
                for bw_scalefactor in bw_scalefactor_list:
                    for rbus_scalefactor in remote_dram_bus_scalefactor_list:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = sls_base_options.format(
                            sniper_options="-g perf_model/dram/remote_dram_bus_scalefactor={} -g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                                rbus_scalefactor,
                                page_size,
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                float(bw_scalefactor),
                                int(1 * ONE_BILLION),
                            ),
                        )
                        # 1 billion instructions cap

                        experiments.append(
                            automation.Experiment(
                                experiment_name="sls_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_rbus_scalefactor_{}_combo".format(
                                    localdram_size_str, net_lat, bw_scalefactor, page_size, rbus_scalefactor
                                ),
                                command_str=command_str,
                                experiment_run_configs=config_list,
                                output_root_directory=".",
                                start_experiment_no=1,
                            )
                        )

    return experiments

def run_sql(sql_filename):  # TPCH
    experiments = []

    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat = 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = sql_base_options.format(
        sql_filename,
        # Set magic=false since sqlite3 currently doesn't have ROI markers
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{} -g general/magic=false".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            float(bw_scalefactor),
            int(1 * ONE_BILLION),
        ),
    )
    # 1 billion instructions cap
    experiments.append(
        automation.Experiment(
            experiment_name="sql_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_noremotemem".format(
                sql_filename, localdram_size_str, net_lat, bw_scalefactor, page_size
            ),
            command_str=command_str,
            experiment_run_configs=no_remote_memory_list,
            output_root_directory=".",
        )
    )

    sql_filename_to_local_dram_size = {
        "5": [22],
    }
    # Everything else
    for num_MB in sql_filename_to_local_dram_size[sql_filename]:
        for page_size in page_size_list:
            for net_lat in netlat_list:
                for bw_scalefactor in bw_scalefactor_list:
                    for rbus_scalefactor in remote_dram_bus_scalefactor_list:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = sql_base_options.format(
                            sql_filename,
                            # Set magic=false since sqlite3 currently doesn't have ROI markers
                            sniper_options="-g perf_model/dram/remote_dram_bus_scalefactor={} -g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{} -g general/magic=false".format(
                                rbus_scalefactor,
                                page_size,
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                float(bw_scalefactor),
                                int(1 * ONE_BILLION),
                            ),
                        )
                        # 1 billion instructions cap

                        experiments.append(
                            automation.Experiment(
                                experiment_name="sql_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_rbus_scalefactor_{}_combo".format(
                                    sql_filename, localdram_size_str, net_lat, bw_scalefactor, page_size, rbus_scalefactor
                                ),
                                command_str=command_str,
                                experiment_run_configs=config_list,
                                output_root_directory=".",
                                start_experiment_no=1,
                            )
                        )

    return experiments

# TODO: Experiment run
experiments = []
experiments.extend(run_darknet("resnet50"))
#experiments.extend(run_darknet("resnet152"))
experiments.extend(run_darknet("darknet19"))
experiments.extend(run_darknet("vgg-16"))
#experiments.extend(run_darknet("yolov3"))
# experiments.extend(run_spmv("pkustk14.mtx"))
# experiments.extend(run_ligra_nonsym("MIS"))
# experiments.extend(run_ligra_nonsym("Radii"))
# experiments.extend(run_ligra_sym("KCore"))

# experiments.extend(run_ligra_sym("Triangle"))
# experiments.extend(run_ligra_nonsym("Components"))
# experiments.extend(run_ligra_nonsym("BFS"))
# experiments.extend(run_ligra_nonsym("BC"))
# experiments.extend(run_nw("4096"))
# experiments.extend(run_ligra_nonsym("PageRank"))


# experiments.extend(run_darknet("yolov3"))

# experiments.extend(run_sls())
# experiments.extend(run_darknet("resnet152"))
# experiments.extend(run_hpcg())
# experiments.extend(run_sql("5"))  # TPCH

# experiments.extend(run_stream("3"))  # Stream?

timezone = pytz.timezone("Canada/Eastern")
log_filename = "run-sniper-repeat_1.log"
num = 2
while os.path.isfile(log_filename):
    log_filename = "run-sniper-repeat_{}.log".format(num)
    num += 1

with open(log_filename, "w") as log_file:
    log_str = "Script start time: {}".format(automation.datetime.datetime.now().astimezone(timezone))
    print(log_str)
    print(log_str, file=log_file)

    experiment_manager = automation.ExperimentManager(
        output_root_directory=".", max_concurrent_processes=24, log_file=log_file
    )
    experiment_manager.add_experiments(experiments)
    # compiled_application_checker(experiments)
    input_file_checker(experiments)
    experiment_manager.start(
        manager_sleep_interval_seconds=60,
        timezone=timezone,
    )

    log_str = "Script end time: {}".format(automation.datetime.datetime.now().astimezone(timezone))
    print(log_str)
    print(log_str, file=log_file)
