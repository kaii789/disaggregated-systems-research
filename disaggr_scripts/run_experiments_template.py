# Python 3
from run_sniper_repeat_base import *

# import pytz

if __name__ == "__main__":
    # Relative to directory where command_str will be executed, ie subfolder of subfolder of this file's containing directory
    subfolder_sniper_root_relpath = "../../.."
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
    # Assumes input matrices are in the {sniper_root}/test/crono/inputs directory
    sssp_int_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/crono/apps/sssp/sssp_int {sniper_root}/benchmarks/crono/inputs/{{0}} 1".format(
        sniper_root=subfolder_sniper_root_relpath
    )
    stream_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/stream/stream_sniper {{0}}".format(
        sniper_root=subfolder_sniper_root_relpath
    )
    spmv_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/spmv/bench_spdmv {sniper_root}/test/crono/inputs/{{0}} 1 1".format(
        sniper_root=subfolder_sniper_root_relpath
    )
    nw_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/rodinia/bin/needle {{0}} 1 1".format(
        sniper_root=subfolder_sniper_root_relpath
    )

    ###  Darknet command strings  ###
    # Note: using os.system(), the 'cd' of working directory doesn't persist to the next call to os.system()
    darknet_base_str_options = "cd {1} && ../../run-sniper -d {{{{sniper_output_dir}}}} -c ../../disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/darknet classifier predict {0}/cfg/imagenet1k.data {0}/cfg/{{0}}.cfg {0}/{{0}}.weights {0}/data/dog.jpg && cd {{{{sniper_output_dir}}}}".format(
        ".", darknet_home
    )
    # Examples:
    # command_strs["darknet_tiny"] = darknet_base_str_options.format(
    #     "tiny", sniper_options=""
    # )
    # command_strs["darknet_darknet"] = darknet_base_str_options.format(
    #     "darknet", sniper_options=""
    # )
    # command_strs["darknet_darknet19"] = darknet_base_str_options.format(
    #     "darknet19", sniper_options=""
    # )
    # command_strs["darknet_vgg-16"] = darknet_base_str_options.format(
    #     "vgg-16", sniper_options=""
    # )
    # command_strs["darknet_resnet50"] = darknet_base_str_options.format(
    #     "resnet50", sniper_options=""
    # )
    # cd ../benchmarks/darknet && ../../run-sniper -c ../../disaggr_config/local_memory_cache.cfg -- ./darknet classifier predict ./cfg/imagenet1k.data ./cfg/tiny.cfg ./tiny.weights ./data/dog.jpg

    ###  Ligra command strings  ###
    # Do only 1 timed round to save time during initial experiments
    ligra_base_str_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/apps/{{0}} -s -rounds 1 {0}/inputs/{{1}}".format(
        ligra_home, sniper_root=subfolder_sniper_root_relpath
    )
    ligra_base_str_options_nonsym = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/apps/{{0}} -rounds 1 {0}/inputs/{{1}}".format(
        ligra_home, sniper_root=subfolder_sniper_root_relpath
    )
    ligra_input_to_file = {
        "regular_input": "rMat_1000000",
        # "small_input": "rMat_100000",
        "reg_10x": "rMat_10000000",
        "reg_8x": "rMat_8000000",
    }
    # Examples:
    # command_strs["ligra_bfs"] = ligra_base_str_options.format(
    #     "BFS", ligra_input_to_file["regular_input"], sniper_options=""
    # )
    # command_strs["ligra_pagerank"] = ligra_base_str_options.format(
    #     "PageRank", ligra_input_to_file["regular_input"], sniper_options=""
    # )

    # # Small input: first run some tests with smaller input size
    # command_strs["ligra_bfs_small_input"] = ligra_base_str_options.format(
    #     "BFS", ligra_input_to_file["small_input"], sniper_options=""
    # )
    # command_strs["ligra_pagerank_small_input"] = ligra_base_str_options.format(
    #     "PageRank", ligra_input_to_file["small_input"], sniper_options=""
    # )

    # # Stop around 100 Million instructions after entering ROI (magic = true in config so don't need --roi flag)
    # command_strs["ligra_bfs_instrs_100mil"] = ligra_base_str_options.format(
    #     "BFS",
    #     ligra_input_to_file["regular_input"],
    #     sniper_options="-s stop-by-icount:{}".format(100 * ONE_MILLION),
    # )

    # # 8 MB for ligra_bfs + rMat_1000000
    # command_strs["ligra_bfs_localdram_8MB"] = ligra_base_str_options.format(
    #     "BFS",
    #     ligra_input_to_file["regular_input"],
    #     sniper_options="-g perf_model/dram/localdram_size={}".format(
    #         int(8 * ONE_MB_TO_BYTES)
    #     ),
    # )
    # # 1 MB for ligra_bfs + rMat_100000
    # command_strs["ligra_bfs_small_input_localdram_1MB"] = ligra_base_str_options.format(
    #     "BFS",
    #     ligra_input_to_file["small_input"],
    #     sniper_options="-g perf_model/dram/localdram_size={}".format(
    #         int(1 * ONE_MB_TO_BYTES)
    #     ),
    # )

    partition_queue_series_experiment_run_configs = [
        # 1) Remote off
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "false"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
            ]
        ),
        # 2) Remote on, don't simulate page movement time
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry(
                    "perf_model/dram", "simulate_datamov_overhead", "false"
                ),  # default is true
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry(
                    "perf_model/dram", "remote_mem_add_lat", "0"
                ),  # default is somewhere around 100-3000
            ]
        ),
        # 3) Remote on, simulate page movement time with only network latency (ie ignore bandwidth)
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry(
                    "perf_model/dram", "simulate_datamov_overhead", "true"
                ),  # default is true
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry(
                    "perf_model/dram/queue_model",
                    "remote_queue_model_type",
                    "network_latency_only",
                ),  # default is windowed_mg1_remote
            ]
        ),
        # 4) Remote on, simulate page movement time with only bandwidth (ie 0 network latency)
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram", "remote_mem_add_lat", "0"),
            ]
        ),
        # 5) Remote on, simulate page movement time with both bandwidth and network latency, PQ = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
            ]
        ),
        # # 6) Remote on, simulate page movement time with both bandwidth and network latency, PQ = 1
        # ExperimentRunConfig(
        #     [
        #         ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
        #         ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
        #         ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.5"),
        #     ]
        # ),
    ]

    # Cacheline queue ratio configs
    cacheline_queue_ratio_config_base = ExperimentRunConfig(
        [
            ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
        ]
    )
    cacheline_queue_ratio_configs = []
    for cacheline_queue_ratio in [
        "0.1",
        "0.15",
        "0.2",
        "0.25",
        "0.3",
        "0.35",
        "0.4",
        "0.45",
        "0.5",
        "0.55",
        "0.6",
    ]:
        config_copy = copy.deepcopy(cacheline_queue_ratio_config_base)
        config_copy.add_config_entry(
            ConfigEntry(
                "perf_model/dram",
                "remote_cacheline_queue_fraction",
                cacheline_queue_ratio,
            )
        )
        cacheline_queue_ratio_configs.append(config_copy)

    pq_cacheline_combined_rmode1_configs = []
    for config in (
        partition_queue_series_experiment_run_configs[0:5]
        + cacheline_queue_ratio_configs
    ):
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entries(
            [
                ConfigEntry(
                    "perf_model/dram/compression_model", "use_compression", "false"
                ),
                ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
                # remote_init  specified in individual experiments
            ]
        )
        pq_cacheline_combined_rmode1_configs.append(config_copy)

    #################################

    experiments = []

    # SSSP bcsstk32, 12 8KB and 256 KB (can probably remove 128 KB)
    bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode1 = []
    net_lat = 120
    for remote_init in ["true"]:  # "false"
        for num_B in [131072, 262144]:
            for bw_scalefactor in [4, 8, 32]:
                localdram_size_str = "{}B".format(num_B)
                command_str = sssp_int_base_options.format(
                    "bcsstk32.mtx",
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                        int(num_B),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                    ),
                )

                bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode1.append(
                    Experiment(
                        experiment_name="bcsstk32_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_pq_cacheline_combined_series".format(
                            localdram_size_str,
                            net_lat,
                            bw_scalefactor,
                            remote_init,
                        ),
                        command_str=command_str,
                        experiment_run_configs=pq_cacheline_combined_rmode1_configs,
                        output_root_directory=".",
                    )
                )

    # Darknet tiny, 2 MB
    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1 = []
    net_lat = 120
    for model_type in ["tiny"]:
        for remote_init in ["true"]:  # "false"
            for num_MB in [2]:
                for bw_scalefactor in [4, 8, 32]:
                    localdram_size_str = "{}MB".format(num_MB)
                    command_str = darknet_base_str_options.format(
                        model_type,
                        sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                            int(num_MB * ONE_MB_TO_BYTES),
                            int(net_lat),
                            int(bw_scalefactor),
                            str(remote_init),
                            int(1 * ONE_BILLION),
                        ),
                    )
                    # 1 billion instructions cap

                    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1.append(
                        Experiment(
                            experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_pq_cacheline_combined_series".format(
                                model_type.lower(),
                                localdram_size_str,
                                net_lat,
                                bw_scalefactor,
                                remote_init,
                            ),
                            command_str=command_str,
                            experiment_run_configs=pq_cacheline_combined_rmode1_configs,
                            output_root_directory=".",
                        )
                    )

    # experiments.extend(bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode1)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1)


    ### Run Sniper experiments using ExperimentManager ###
    # Find log filename, to not overwrite previous logs
    timezone = None
    # timezone = pytz.timezone("Canada/Eastern")
    log_filename = "run-sniper-repeat_1.log"
    num = 2
    while os.path.isfile(log_filename):
        log_filename = "run-sniper-repeat_{}.log".format(num)
        num += 1

    with open(log_filename, "w") as log_file:
        log_str = "Script start time: {}".format(datetime.datetime.now().astimezone(timezone))
        print(log_str)
        print(log_str, file=log_file)

        experiment_manager = ExperimentManager(
            output_root_directory=".", max_concurrent_processes=16, log_file=log_file
        )
        experiment_manager.add_experiments(experiments)
        experiment_manager.start(
            manager_sleep_interval_seconds=60,
            timezone=timezone,
        )  # main thread sleep for 60 second intervals while waiting

        log_str = "Script end time: {}".format(datetime.datetime.now().astimezone(timezone))
        print(log_str)
        print(log_str, file=log_file)
