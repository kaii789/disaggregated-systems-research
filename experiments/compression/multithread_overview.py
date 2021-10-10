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
            automation.ConfigEntry("general", "total_cores", "4"),
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
    # 0) No Compression
    automation.ExperimentRunConfig(
        [
            # automation.ConfigEntry("general", "magic", "false"),
            automation.ConfigEntry("general", "total_cores", "4"),
            automation.ConfigEntry("perf_model/l3_cache", "cache_size", "4096"),
            automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
            automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
            automation.ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
            automation.ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
            automation.ConfigEntry("perf_model/dram", "remote_init", "true"),
            # automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
            # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
        ]
    ),
    # 1 PQ On
    automation.ExperimentRunConfig(
        [
            # automation.ConfigEntry("general", "magic", "false"),
            automation.ConfigEntry("general", "total_cores", "4"),
            automation.ConfigEntry("perf_model/l3_cache", "cache_size", "4096"),
            automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
            automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "4"),
            automation.ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
            automation.ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
            automation.ConfigEntry("perf_model/dram", "remote_init", "true"),
            automation.ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.2"),
            automation.ConfigEntry("perf_model/dram", "use_dynamic_cacheline_queue_fraction_adjustment", "false"),
        ]
    ),
    # 2 Compression On
    automation.ExperimentRunConfig(
        [
            automation.ConfigEntry("general", "total_cores", "4"),
            automation.ConfigEntry("perf_model/l3_cache", "cache_size", "4096"),
            automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
            automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "adaptive"),
            automation.ConfigEntry("perf_model/dram/compression_model/zlib", "compression_latency", "5"),
            automation.ConfigEntry("perf_model/dram/compression_model/zlib", "decompression_latency", "5"),
            automation.ConfigEntry("perf_model/dram/compression_model/adaptive/dynamic_bw_threshold", "high_compression_rate", "5"),
            automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
            automation.ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
            automation.ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
            automation.ConfigEntry("perf_model/dram", "remote_init", "true"),
        ]
    ),
    # 3 PQ On, Compression On
    automation.ExperimentRunConfig(
        [
            automation.ConfigEntry("general", "total_cores", "4"),
            automation.ConfigEntry("perf_model/l3_cache", "cache_size", "4096"),
            automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
            automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "adaptive"),
            automation.ConfigEntry("perf_model/dram/compression_model/zlib", "compression_latency", "5"),
            automation.ConfigEntry("perf_model/dram/compression_model/zlib", "decompression_latency", "5"),
            automation.ConfigEntry("perf_model/dram/compression_model/adaptive/dynamic_bw_threshold", "high_compression_rate", "5"),
            automation.ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
            automation.ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
            automation.ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
            automation.ConfigEntry("perf_model/dram", "remote_init", "true"),
        ]
    ),

    # # 1) LZBDI
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lzbdi"),
    #         # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
    #     ]
    # ),
    # # 2) LZ78
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
    #         # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
    #     ]
    # ),
    # # 3) LZW
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lzw"),
    #         # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
    #     ]
    # ),
    # # 4) Deflate 1 GB/s
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "zlib"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "compression_latency", "1"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "decompression_latency", "1"),
    #         # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
    #     ]
    # ),
    # # 5) Deflate 2 GB/s
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "zlib"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "compression_latency", "2"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "decompression_latency", "2"),
    #         # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
    #     ]
    # ),
    # # 6) Deflate 5 GB/s
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "zlib"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "compression_latency", "5"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "decompression_latency", "5"),
    #         # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
    #     ]
    # ),
    # # 7) Adaptive LZ78
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "adaptive"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/adaptive", "high_compression_scheme", "lz78"),
    #         # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/adaptive/dynamic_bw_threshold", "high_compression_rate", "0.5"),
    #     ]
    # ),
    # # 8) Adaptive LZW
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "adaptive"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/adaptive", "high_compression_scheme", "lzw"),
    #         # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/adaptive/dynamic_bw_threshold", "high_compression_rate", "0.5"),
    #     ]
    # ),
    # # 9) Adaptive Deflate 1 GB/s
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "adaptive"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "compression_latency", "1"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "decompression_latency", "1"),
    #         # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/adaptive/dynamic_bw_threshold", "high_compression_rate", "1"),
    #     ]
    # ),
    # # 10) Adaptive Deflate 2 GB/s
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "adaptive"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "compression_latency", "2"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "decompression_latency", "2"),
    #         # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/adaptive/dynamic_bw_threshold", "high_compression_rate", "2"),
    #     ]
    # ),
    # # 11) Adaptive Deflate 5 GB/s
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "adaptive"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "compression_latency", "5"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "decompression_latency", "5"),
    #         # automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/adaptive/dynamic_bw_threshold", "high_compression_rate", "5"),
    #     ]
    # ),
    # 12) Adaptive Deflate 10 GB/s
    # automation.ExperimentRunConfig(
    #     [
    #         automation.ConfigEntry("perf_model/l3_cache", "cache_size", "512"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
    #         automation.ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "adaptive"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "compression_latency", "10"),
    #         automation.ConfigEntry("perf_model/dram/compression_model/zlib", "decompression_latency", "10"),
    #         automation.ConfigEntry("perf_model/dram", "use_dynamic_bandwidth", "true"),
    #     ]
    # ),
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
sssp_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/crono/apps/sssp/sssp_pthread {sniper_root}/benchmarks/crono/inputs/{{0}} 1".format(
    sniper_root=subfolder_sniper_root_relpath
)

stream_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/stream/stream_sniper {{0}}".format(
    sniper_root=subfolder_sniper_root_relpath
)
spmv_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/spmv/bench_spdmv {sniper_root}/benchmarks/crono/inputs/{{0}} 1 4".format(
    sniper_root=subfolder_sniper_root_relpath
)
nw_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/rodinia/bin/needle {{0}} 1 4".format(
    sniper_root=subfolder_sniper_root_relpath
)
hpcg_base_options = "export OMP_NUM_THREADS=4; cp {sniper_root}/benchmarks/hpcg/linux_multi/bin/hpcg.dat .;{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/hpcg/linux_multi/bin/xhpcg".format(
    sniper_root=subfolder_sniper_root_relpath
)
sls_base_options = "export OMP_NUM_THREADS=4; {sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/sls/bin/sls -f /home/shared/sls.in".format(
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
# ligra_base_str_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/apps/{{0}} -s -rounds 1 {0}/inputs/{{1}}".format(
#     ligra_home, sniper_root=subfolder_sniper_root_relpath
# )
ligra_base_str_options_sym = "export OMP_NUM_THREADS=4; {sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/apps/{{0}} -s -rounds 1 {0}/inputs/{{1}}".format(
        ligra_home, sniper_root=subfolder_sniper_root_relpath
    )
ligra_base_str_options_nonsym = "export OMP_NUM_THREADS=4; {sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/apps/{{0}} -rounds 1 {0}/inputs/{{1}}".format(
    ligra_home, sniper_root=subfolder_sniper_root_relpath
)
ligra_input_to_file = {
    "regular_input": "rMat_1000000",
    # "small_input": "rMat_100000",
    # "reg_10x": "rMat_10000000",
    # "reg_8x": "rMat_8000000",
    "regular_input_sym": "rMat_1000000sym",
    "regular_input_w": "rMat_1000000_w",
}

# TODO:
page_size_list = [4096] # 512, 1024, 2048, 64
bw_scalefactor_list = [1.536, 4, 16]
netlat_list = [120, 400, 1600] # 880, 1000

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
                            "stream": [],  # stream doesn't need an input file
                            "nw": [],  # stream doesn't need an input file
                            }
    input_missing = False
    for experiment in experiments:
        found = False
        for key in input_to_file_path.keys():
            if key.lower() in experiment.experiment_name.lower():
                found = True
                for file_path in input_to_file_path[key]:
                    if not os.path.exists(os.path.relpath(file_path, start="../..")):
                        print("Error: couldn't find input {} at {}".format(key, os.path.relpath(file_path, start="../..")))
                        input_missing = True
                break
        if not found:
            print("{} didn't match any of the input file patterns".format(experiment.experiment_name))
    if input_missing:
        raise FileNotFoundError()

# Ligra
def run_ligra_nonsym(application_name):
    ligra_input_selection = "regular_input" if application_name not in ["BellmanFord", "CF"] else "regular_input_w"
    experiments = []
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    app_to_local_dram_size = {
        "BFS": [20],
        "BC": [29],
        "Components": [26],
        "PageRank": [25],
        "KCore": [25],
        "MIS": [25],
        "Radii": [25],
        "BellmanFord": [36],
        "CF": [50],
    }
    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat= 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = ligra_base_str_options_nonsym.format(
        application_name,
        ligra_input_file,
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            int(bw_scalefactor),
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
            for bw_scalefactor in bw_scalefactor_list:
                for net_lat in netlat_list:
                    localdram_size_str = "{}MB".format(num_MB)
                    command_str = ligra_base_str_options_nonsym.format(
                        application_name,
                        ligra_input_file,
                        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                            page_size,
                            int(num_MB * ONE_MB_TO_BYTES),
                            int(net_lat),
                            int(bw_scalefactor),
                            int(1 * ONE_BILLION),
                        ),
                    )

                    experiments.append(
                        automation.Experiment(
                            experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_combo".format(
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
                            experiment_run_configs=config_list,
                            output_root_directory=".",
                        )
                    )

    return experiments

def run_ligra_sym(application_name):
    ligra_input_selection = "regular_input_sym"
    experiments = []
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    app_to_local_dram_size = {
        "Triangle": [30],
    }
    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat= 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = ligra_base_str_options_sym.format(
        application_name,
        ligra_input_file,
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            int(bw_scalefactor),
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
            for bw_scalefactor in bw_scalefactor_list:
                for net_lat in netlat_list:
                    localdram_size_str = "{}MB".format(num_MB)
                    command_str = ligra_base_str_options_sym.format(
                        application_name,
                        ligra_input_file,
                        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                            page_size,
                            int(num_MB * ONE_MB_TO_BYTES),
                            int(net_lat),
                            int(bw_scalefactor),
                            int(1 * ONE_BILLION),
                        ),
                    )

                    experiments.append(
                        automation.Experiment(
                            experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_combo".format(
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
                            experiment_run_configs=config_list,
                            output_root_directory=".",
                        )
                    )

    return experiments


def run_darknet(model_type):
    experiments = []

    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat= 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = darknet_base_str_options.format(
        model_type,
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            int(bw_scalefactor),
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
        "vgg-16": [24]
    }
    for num_MB in model_to_local_dram_size[model_type]:
        for page_size in page_size_list:
            for bw_scalefactor in bw_scalefactor_list:
                for net_lat in netlat_list:
                    localdram_size_str = "{}MB".format(num_MB)
                    command_str = darknet_base_str_options.format(
                        model_type,
                        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                            page_size,
                            int(num_MB * ONE_MB_TO_BYTES),
                            int(net_lat),
                            int(bw_scalefactor),
                            int(1 * ONE_BILLION),
                        ),
                    )
                    # 1 billion instructions cap

                    experiments.append(
                        automation.Experiment(
                            experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_combo".format(
                                model_type.lower().replace("-", ""), localdram_size_str, net_lat, bw_scalefactor, page_size
                            ),
                            command_str=command_str,
                            experiment_run_configs=config_list,
                            output_root_directory=".",
                        )
                    )

    return experiments


# Stream, 2 MB
def run_stream(type):
    experiments = []
    net_lat = 120
    for num_MB in [2]:
        for bw_scalefactor in [4]:
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


def run_nw(dimension):
    experiments = []

    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat= 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = nw_base_options.format(
        dimension,
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            int(bw_scalefactor),
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

    dimension_to_local_dram_size = {
        "2048": [6],
        "4096": [26],
        "6144": [58],
    }
    num_MB = dimension_to_local_dram_size[dimension][0]
    for page_size in page_size_list:
        for bw_scalefactor in bw_scalefactor_list:
            for net_lat in netlat_list:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = nw_base_options.format(
                    dimension,
                    sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                        page_size,
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        int(1 * ONE_BILLION),
                    ),
                )
                # 1 billion instructions cap

                experiments.append(
                    automation.Experiment(
                        experiment_name="nw_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_combo".format(
                            localdram_size_str, net_lat, bw_scalefactor, page_size
                        ),
                        command_str=command_str,
                        experiment_run_configs=config_list,
                        output_root_directory=".",
                    )
                )

    return experiments

def run_spmv(matrix):
    experiments = []
    roi_num_pages = 29462
    matrix_to_local_dram_size = {
        "pkustk14.mtx": [23],
    }
    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat= 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = spmv_base_options.format(
        matrix,
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            int(bw_scalefactor),
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
            for bw_scalefactor in bw_scalefactor_list:
                for net_lat in netlat_list:
                    localdram_size_str = "{}MB".format(num_MB)
                    command_str = spmv_base_options.format(
                        matrix,
                        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                            page_size,
                            int(num_MB * ONE_MB_TO_BYTES),
                            int(net_lat),
                            int(bw_scalefactor),
                            int(1 * ONE_BILLION),
                        ),
                    )

                    experiments.append(
                        automation.Experiment(
                            experiment_name="spmv_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_combo".format(
                                matrix[:matrix.find(".")].replace("-", ""),
                                localdram_size_str,
                                net_lat,
                                bw_scalefactor,
                                page_size
                            ),
                            command_str=command_str,
                            experiment_run_configs=config_list,
                            output_root_directory=".",
                        )
                    )
    return experiments

def run_sls():
    experiments = []

    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat= 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = sls_base_options.format(
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            int(bw_scalefactor),
            int(1 * ONE_BILLION),
        ),
    )
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

    num_MB = 2000
    for page_size in page_size_list:
        for bw_scalefactor in bw_scalefactor_list:
            for net_lat in netlat_list:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = sls_base_options.format(
                    sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                        page_size,
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        int(1 * ONE_BILLION),
                    ),
                )
                # 1 billion instructions cap

                experiments.append(
                    automation.Experiment(
                        experiment_name="sls_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_combo".format(
                            localdram_size_str, net_lat, bw_scalefactor, page_size
                        ),
                        command_str=command_str,
                        experiment_run_configs=config_list,
                        output_root_directory=".",
                    )
                )

    return experiments


def run_hpcg():
    experiments = []

    # Remote memory off case
    num_MB = 8
    page_size = 4096
    net_lat= 120
    bw_scalefactor = 4
    localdram_size_str = "{}MB".format(num_MB)
    command_str = hpcg_base_options.format(
        sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
            page_size,
            int(num_MB * ONE_MB_TO_BYTES),
            int(net_lat),
            int(bw_scalefactor),
            int(1 * ONE_BILLION),
        ),
    )
    experiments.append(
    automation.Experiment(
        experiment_name="hpcg_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_noremotemem".format(
            localdram_size_str, net_lat, bw_scalefactor, page_size
        ),
        command_str=command_str,
        experiment_run_configs=no_remote_memory_list,
        output_root_directory=".",
        )
    )

    num_MB = 200
    for page_size in page_size_list:
        for bw_scalefactor in bw_scalefactor_list:
            for net_lat in netlat_list:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = hpcg_base_options.format(
                    sniper_options="-g perf_model/dram/page_size={} -g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                        page_size,
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        int(1 * ONE_BILLION),
                    ),
                )
                # 1 billion instructions cap

                experiments.append(
                    automation.Experiment(
                        experiment_name="hpcg_localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_combo".format(
                            localdram_size_str, net_lat, bw_scalefactor, page_size
                        ),
                        command_str=command_str,
                        experiment_run_configs=config_list,
                        output_root_directory=".",
                    )
                )

    return experiments


# TODO: Experiment run
experiments = []

# experiments.extend(run_ligra_nonsym("BFS"))
# experiments.extend(run_ligra_nonsym("BC"))
# experiments.extend(run_ligra_nonsym("Components"))
# experiments.extend(run_ligra_sym("Triangle"))

# experiments.extend(run_ligra_nonsym("PageRank"))
# experiments.extend(run_ligra_nonsym("KCore"))
# experiments.extend(run_ligra_nonsym("MIS"))
# experiments.extend(run_ligra_nonsym("Radii"))

# experiments.extend(run_ligra_nonsym("BellmanFord"))
# experiments.extend(run_ligra_nonsym("CF"))
# experiments.extend(run_nw("4096"))
# experiments.extend(run_spmv("pkustk14.mtx"))

# experiments.extend(run_sls())
# experiments.extend(run_hpcg())

# For later
# experiments.extend(run_darknet("vgg-16"))
# experiments.extend(run_darknet("resnet50"))
# experiments.extend(run_darknet("darknet19"))

timezone = pytz.timezone("Canada/Eastern")
log_filename = "run-sniper-repeat2_1.log"
num = 2
while os.path.isfile(log_filename):
    log_filename = "run-sniper-repeat2_{}.log".format(num)
    num += 1

with open(log_filename, "w") as log_file:
    log_str = "Script start time: {}".format(automation.datetime.datetime.now().astimezone(timezone))
    print(log_str)
    print(log_str, file=log_file)

    experiment_manager = automation.ExperimentManager(
        output_root_directory=".", max_concurrent_processes=8, log_file=log_file
    )
    experiment_manager.add_experiments(experiments)
    # compiled_application_checker(experiments)
    input_file_checker(experiments)
    experiment_manager.start(
        manager_sleep_interval_seconds=30,
        timezone=timezone,
    )

    log_str = "Script end time: {}".format(automation.datetime.datetime.now().astimezone(timezone))
    print(log_str)
    print(log_str, file=log_file)


# TODO: the run functions below haven't been updated yet
# # sssp 512KB
# def run_sssp(input):
#     experiments = []
#     net_lat = 120
#     for remote_init in ["true"]:  # "false"
#         for num_B in [524288]:
#             for bw_scalefactor in [4, 16]:
#                 localdram_size_str = "{}B".format(num_B)
#                 command_str = sssp_base_options.format(
#                     input,
#                     sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
#                         int(num_B),
#                         int(net_lat),
#                         int(bw_scalefactor),
#                         str(remote_init),
#                     ),
#                 )

#                 experiments.append(
#                     automation.Experiment(
#                         experiment_name="sssp_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_combo".format(
#                             input,
#                             localdram_size_str,
#                             net_lat,
#                             bw_scalefactor,
#                             remote_init,
#                         ),
#                         command_str=command_str,
#                         experiment_run_configs=config_list,
#                         output_root_directory=".",
#                     )
#                 )

#     return experiments

# TODO: Generate graph
# def graph(res_name, benchmark_list, local_dram_list, bw_scalefactor_list):
#     # labels = ["Remote Bandwidth Scalefactor", "C0", "LZBDI", "LZ78", "LZW", "DF1", "DF2", "DF5", "A-LZ78", "A-LZW", "A-DF1", "A-DF2", "A-DF5", "A-DF10"]
#     labels = ["Page Size(bytes)", "120", "400", "800"]
#     # "stream_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_combo"

#     for factor in bw_scalefactor_list:
#         page_size_list = [512, 1024, 2048, 4096]

#         process = 0
#         num_bars = len(labels) - 1
#         res = [page_size_list[:]] + [[] for _ in range(num_bars)]
#         # compression_res = {}
#         for benchmark in benchmark_list:
#             for size in local_dram_list:
#                 for page_size in page_size_list:

#                     for i in range(1, 1 + num_bars):
#                         netlat = labels[i]
#                         dir1 = "{}localdram_{}_netlat_{}_bw_scalefactor_{}_page_size_{}_combo_output_files".format(benchmark, size, netlat, factor, page_size)
#                         try:
#                             run = 1
#                             # dir2 = "run_{}_process_{}_temp".format(run, process)
#                             dir2 = "run_{}".format(run)
#                             res_dir = "./{}/{}".format(dir1, dir2)
#                             print(res_dir)
#                             ipc = stats.get_ipc(res_dir)
#                             res[i].append(ipc)

#                             # Compression res
#                             # if run in range(1, 1 + num_bars):
#                             #     type = "{}-{}".format(run - 1, factor)
#                             #     compression_res[type] = {}
#                             #     cr, cl, dl, ccr, ccl, cdl = stats.get_compression_stats(res_dir)
#                             #     compression_res[type]['Compression Ratio'] = cr
#                             #     compression_res[type]['Compression Latency'] = cl
#                             #     compression_res[type]['Decompression Latency'] = dl
#                             #     if ccr:
#                             #         compression_res[type]['Cacheline Compression Ratio'] = ccr
#                             #         compression_res[type]['Cacheline Compression Latency'] = ccl
#                             #         compression_res[type]['Cacheline Decompression Latency'] = cdl

#                             # process += 1
#                         except Exception as e:
#                             print(e)
#                             res[run].append(0)
#                             process += 1

#         print(res)

#         data = {labels[i]: res[i] for i in range(len(labels))}
#         # print(data)
#         # print(compression_res)
#         title = "{}localdram_{}_bwsf_{}".format(benchmark, size, factor)
#         df = pd.DataFrame(data)
#         graph = df.plot(x=labels[0], y=labels[1:], kind="bar")
#         graph.set_title(title, loc='center', wrap=True)
#         fig = graph.get_figure()
#         plt.pyplot.tight_layout()
#         fig.savefig(title)

# def gen_settings_for_graph(benchmark_name):
#     if benchmark_name == "sssp":
#         res_name = "sssp_262144B_combo"
#         benchmark_list = []
#         for input in ["bcsstk05.mtx"]:
#             benchmark_list.append("sssp_{}_".format(input))
#         local_dram_list = ["262144B"]
#         bw_scalefactor_list = [4, 16]
#     if benchmark_name == "sssp_roadNet":
#         res_name = "sssp_524288B_combo"
#         benchmark_list = []
#         for input in ["roadNet-PA.mtx"]:
#             benchmark_list.append("sssp_{}_".format(input))
#         local_dram_list = ["524288B"]
#         bw_scalefactor_list = [4, 16]
#     elif benchmark_name == "bfs_reg":
#         res_name = "bfs_reg_50MB_ac"
#         benchmark_list = []
#         benchmark_list.append("ligra_{}_".format("bfs"))
#         local_dram_list = ["50MB"]
#         bw_scalefactor_list = [4, 16]
#     elif benchmark_name == "triangle_reg":
#         res_name = "triangle_reg_16MB_ac_dynamic_bw"
#         benchmark_list = []
#         benchmark_list.append("ligra_{}_".format("triangle"))
#         local_dram_list = ["16MB"]
#         bw_scalefactor_list = [4]
#     elif benchmark_name == "bc_reg":
#         res_name = "bc_reg_4MB_comparison"
#         benchmark_list = []
#         benchmark_list.append("ligra_{}_".format("bc"))
#         local_dram_list = ["4MB"]
#         bw_scalefactor_list = [4]
#     elif benchmark_name == "components_reg":
#         res_name = "components_reg_4MB_comparison"
#         benchmark_list = []
#         benchmark_list.append("ligra_{}_".format("components"))
#         local_dram_list = ["4MB"]
#         bw_scalefactor_list = [4]
#     elif benchmark_name == "tinynet":
#         res_name = "tinynet_2MB_comparison"
#         benchmark_list = []
#         for model in ["tiny"]:
#             benchmark_list.append("darknet_{}_".format(model))
#         local_dram_list = ["2MB"]
#         bw_scalefactor_list = [4]
#     elif benchmark_name == "darknet19":
#         res_name = "darknet19_2MB_ac_dynamic_bw"
#         benchmark_list = []
#         for model in ["darknet19"]:
#             benchmark_list.append("darknet_{}_".format(model))
#         local_dram_list = ["2MB"]
#         bw_scalefactor_list = [4]
#     elif benchmark_name == "vgg-16":
#         res_name = "vgg-16_2MB_ac_dynamic_bw"
#         benchmark_list = []
#         for model in ["vgg-16"]:
#             benchmark_list.append("darknet_{}_".format(model))
#         local_dram_list = ["2MB"]
#         bw_scalefactor_list = [4]
#     elif benchmark_name == "resnet50":
#         res_name = "resnet50_2MB_comparison"
#         benchmark_list = []
#         for model in ["resnet50"]:
#             benchmark_list.append("darknet_{}_".format(model))
#         local_dram_list = ["2MB"]
#         bw_scalefactor_list = [4]
#     elif benchmark_name == "stream_1":
#         res_name = "stream_1_2MB_comparison"
#         benchmark_list = []
#         benchmark_list.append("stream_1_")
#         local_dram_list = ["2MB"]
#         bw_scalefactor_list = [4, 16]
#     elif benchmark_name == "stream_0":
#         res_name = "stream_0_2MB_ac_dynamic_bw"
#         benchmark_list = []
#         benchmark_list.append("stream_0_")
#         local_dram_list = ["2MB"]
#         bw_scalefactor_list = [4]
#     elif benchmark_name == "hpcg":
#         res_name = "hpcg_32MB_ac_dynamic_bw"
#         benchmark_list = []
#         benchmark_list.append("hpcg_")
#         local_dram_list = ["32MB"]
#         bw_scalefactor_list = [4]
#     elif benchmark_name == "sls":
#         res_name = "sls_16MB_comparison"
#         benchmark_list = []
#         benchmark_list.append("sls_")
#         local_dram_list = ["16MB"]
#         bw_scalefactor_list = [4]
#     elif benchmark_name == "nw":
#         res_name = "nw_4MB_ac_dynamic_bw"
#         benchmark_list = []
#         benchmark_list.append("nw_")
#         local_dram_list = ["4MB"]
#         bw_scalefactor_list = [4]

#     return res_name, benchmark_list, local_dram_list, bw_scalefactor_list

# res_name, benchmark_list, local_dram_list, bw_scalefactor_list = gen_settings_for_graph("bfs_reg")
# graph(res_name, benchmark_list, local_dram_list, bw_scalefactor_list)