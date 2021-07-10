# Python 3
from run_sniper_repeat_base import *

# Post experiment processing functions
# import plot_graph
# import plot_graph_pq


def generate_one_varying_param_experiment_run_configs(
    config_param_category: str,
    config_param_name: str,
    config_param_values: Iterable[str],
) -> List[ExperimentRunConfig]:
    experiment_run_configs = []
    for param_value in config_param_values:
        config_entry = ConfigEntry(
            config_param_category, config_param_name, param_value
        )
        experiment_run_configs.append(ExperimentRunConfig([config_entry]))
    return experiment_run_configs


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
    sssp_int_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/test/crono/apps/sssp/sssp_int {sniper_root}/test/crono/inputs/{{0}} 1".format(
        sniper_root=subfolder_sniper_root_relpath
    )
    sssp_bcsstk32_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/test/crono/apps/sssp/sssp {sniper_root}/test/crono/inputs/bcsstk32.mtx 1".format(
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
    ligra_input_to_file = {
        "regular_input": "rMat_1000000",
        "small_input": "rMat_100000",
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
    # # ../run-sniper -c ../disaggr_config/local_memory_cache.cfg -- ../benchmarks/ligra/apps/BFS -s ../benchmarks/ligra/inputs/rMat_1000000

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

    bandwidth_verification_configs = [
        # 1) test_bandwidth = 0, pq = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "test_bandwidth", "0"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
            ]
        ),
        # 2) test_bandwidth = 2, pq = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "test_bandwidth", "2"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
            ]
        ),
        # 3) test_bandwidth = 0, pq = 1
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "test_bandwidth", "0"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
                ConfigEntry(
                    "perf_model/dram", "remote_cacheline_queue_fraction", "0.5"
                ),
            ]
        ),
        # 4) test_bandwidth = 2, pq = 1
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "test_bandwidth", "2"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
                ConfigEntry(
                    "perf_model/dram", "remote_cacheline_queue_fraction", "0.5"
                ),
            ]
        ),
    ]

    queue_delay_cap_configs_base = [
        # 1) test_bandwidth = 0, default
        ExperimentRunConfig(
            [
                ConfigEntry("queue_model/windowed_mg1_remote", "window_size", "10000"),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "queue_delay_cap", "10000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote",
                    "use_separate_queue_delay_cap",
                    "false",
                ),
            ]
        ),
        # 2) test_bandwidth = 0, window_size 10x larger (adjust queue_delay_cap too)
        ExperimentRunConfig(
            [
                ConfigEntry("queue_model/windowed_mg1_remote", "window_size", "100000"),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "queue_delay_cap", "100000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote",
                    "use_separate_queue_delay_cap",
                    "false",
                ),
            ]
        ),
        # 3) test_bandwidth = 0, window_size 100x larger (adjust queue_delay_cap too)
        ExperimentRunConfig(
            [
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "window_size", "1000000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "queue_delay_cap", "1000000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote",
                    "use_separate_queue_delay_cap",
                    "false",
                ),
            ]
        ),
        # 4) test_bandwidth = 0, window_size 1000x larger (adjust queue_delay_cap too)
        ExperimentRunConfig(
            [
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "window_size", "10000000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "queue_delay_cap", "10000000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote",
                    "use_separate_queue_delay_cap",
                    "false",
                ),
            ]
        ),
        # 5) test_bandwidth = 0, window_size 10000x larger (adjust queue_delay_cap too)
        ExperimentRunConfig(
            [
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "window_size", "100000000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "queue_delay_cap", "100000000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote",
                    "use_separate_queue_delay_cap",
                    "false",
                ),
            ]
        ),
        # 6) test_bandwidth = 0, window_size orig, queue_delay_cap 10x larger
        ExperimentRunConfig(
            [
                ConfigEntry("queue_model/windowed_mg1_remote", "window_size", "10000"),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "queue_delay_cap", "100000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote",
                    "use_separate_queue_delay_cap",
                    "true",
                ),
            ]
        ),
        # 7) test_bandwidth = 0, window_size orig, queue_delay_cap 100x larger
        ExperimentRunConfig(
            [
                ConfigEntry("queue_model/windowed_mg1_remote", "window_size", "10000"),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "queue_delay_cap", "1000000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote",
                    "use_separate_queue_delay_cap",
                    "true",
                ),
            ]
        ),
        # 8) test_bandwidth = 0,window_size orig, queue_delay_cap 1000x larger
        ExperimentRunConfig(
            [
                ConfigEntry("queue_model/windowed_mg1_remote", "window_size", "10000"),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "queue_delay_cap", "10000000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote",
                    "use_separate_queue_delay_cap",
                    "true",
                ),
            ]
        ),
        # 9) test_bandwidth = 0,window_size 10x, queue_delay_cap 100x larger
        ExperimentRunConfig(
            [
                ConfigEntry("queue_model/windowed_mg1_remote", "window_size", "100000"),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "queue_delay_cap", "1000000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote",
                    "use_separate_queue_delay_cap",
                    "true",
                ),
            ]
        ),
        # 10) test_bandwidth = 0,window_size 10x, queue_delay_cap 1000x larger
        ExperimentRunConfig(
            [
                ConfigEntry("queue_model/windowed_mg1_remote", "window_size", "100000"),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote", "queue_delay_cap", "10000000"
                ),
                ConfigEntry(
                    "queue_model/windowed_mg1_remote",
                    "use_separate_queue_delay_cap",
                    "true",
                ),
            ]
        ),
    ]

    # Alternate with pq0 then pq1, etc
    queue_delay_cap_configs = []
    for base_run_config in queue_delay_cap_configs_base:
        pq0_version = copy.deepcopy(base_run_config)
        pq0_version.add_config_entry(
            ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0")
        )
        queue_delay_cap_configs.append(pq0_version)
        pq1_version = copy.deepcopy(base_run_config)
        pq1_version.add_config_entry(
            ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1")
        )
        queue_delay_cap_configs.append(pq1_version)

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
    # Only want runs number 1-5 in partition_queue_series_experiment_run_configs
    for config in (
        partition_queue_series_experiment_run_configs[0:5]
        + cacheline_queue_ratio_configs
    ):
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entries(
            [
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
                ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
                # remote_init  specified in individual experiments
            ]
        )
        pq_cacheline_combined_rmode1_configs.append(config_copy)

    pq_cacheline_combined_rmode2_configs = []
    # Only want runs number 1-5 in partition_queue_series_experiment_run_configs
    for config in (
        partition_queue_series_experiment_run_configs[0:5]
        + cacheline_queue_ratio_configs
    ):
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entries(
            [
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
                ConfigEntry("perf_model/dram", "remote_memory_mode", "2"),
                # remote_init  specified in individual experiments
                # remote_datamov_threshold  specified in individual experiments
            ]
        )
        pq_cacheline_combined_rmode2_configs.append(config_copy)

    pq_cacheline_combined_rmode5_configs = []
    # Only want runs number 1-5 in partition_queue_series_experiment_run_configs
    for config in (
        partition_queue_series_experiment_run_configs[0:5]
        + cacheline_queue_ratio_configs
    ):
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entries(
            [
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
                ConfigEntry("perf_model/dram", "remote_memory_mode", "5"),
                # remote_init  specified in individual experiments
                # remote_datamov_threshold  specified in individual experiments
                # r_mode_5_page_queue_utilization_mode_switch_threshold  specified in individual experiments
                ConfigEntry("perf_model/dram", "r_mode_5_remote_access_history_window_size", "100000"),
            ]
        )
        pq_cacheline_combined_rmode5_configs.append(config_copy)

    pq_cacheline_combined_rmode5_access_history_50k_configs = []
    # Only want runs number 1-5 in partition_queue_series_experiment_run_configs
    for config in (
        partition_queue_series_experiment_run_configs[0:5]
        + cacheline_queue_ratio_configs
    ):
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entries(
            [
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
                ConfigEntry("perf_model/dram", "remote_memory_mode", "5"),
                # remote_init  specified in individual experiments
                # remote_datamov_threshold  specified in individual experiments
                # r_mode_5_page_queue_utilization_mode_switch_threshold  specified in individual experiments
                ConfigEntry("perf_model/dram", "r_mode_5_remote_access_history_window_size", "50000"),
            ]
        )
        pq_cacheline_combined_rmode5_access_history_50k_configs.append(config_copy)

    pq_cacheline_combined_rmode5_access_history_500k_configs = []
    # Only want runs number 1-5 in partition_queue_series_experiment_run_configs
    for config in (
        partition_queue_series_experiment_run_configs[0:5]
        + cacheline_queue_ratio_configs
    ):
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entries(
            [
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
                ConfigEntry("perf_model/dram", "remote_memory_mode", "5"),
                # remote_init  specified in individual experiments
                # remote_datamov_threshold  specified in individual experiments
                # r_mode_5_page_queue_utilization_mode_switch_threshold  specified in individual experiments
                ConfigEntry("perf_model/dram", "r_mode_5_remote_access_history_window_size", "500000"),
            ]
        )
        pq_cacheline_combined_rmode5_access_history_500k_configs.append(config_copy)


    pq_cacheline_combined_rmode1_configs_ideal_page_throttling = []
    # Only want runs number 1-5 in partition_queue_series_experiment_run_configs
    for config in pq_cacheline_combined_rmode1_configs:
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entries(
            [
                ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "true"),
                # remote_init  specified in individual experiments
            ]
        )
        pq_cacheline_combined_rmode1_configs_ideal_page_throttling.append(config_copy)

    pq_cacheline_combined_rmode2_configs_ideal_page_throttling = []
    # Only want runs number 1-5 in partition_queue_series_experiment_run_configs
    for config in pq_cacheline_combined_rmode2_configs:
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entries(
            [
                ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "true"),
                # remote_init  specified in individual experiments
                # remote_datamov_threshold  specified in individual experiments
            ]
        )
        pq_cacheline_combined_rmode2_configs_ideal_page_throttling.append(config_copy)


    #################################

    experiments = []


    # BFS, reg_8x, 64 & 32 MB, 2 Billion instructions cap
    bfs_reg_8x_pq_experiments = []
    ligra_input_selection = "reg_8x"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    net_lat = 120
    for num_MB in [64, 32]:
        for bw_scalefactor in [4]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = ligra_base_str_options.format(
                application_name,
                ligra_input_file,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                    int(num_MB * ONE_MB_TO_BYTES), int(net_lat), int(bw_scalefactor), int(2 * ONE_BILLION)
                ),
            )

            bfs_reg_8x_pq_experiments.append(
                Experiment(
                    experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_8x_test".format(
                        application_name.lower(),
                        ""
                        if ligra_input_selection == "regular_input"
                        else ligra_input_selection + "_",
                        localdram_size_str,
                        net_lat,
                        bw_scalefactor,
                    ),
                    command_str=command_str,
                    experiment_run_configs=[
                        pq_cacheline_combined_rmode1_configs[4],
                        pq_cacheline_combined_rmode1_configs[-3],
                    ],  # pq=0 + pq=1 w/ 0.5 cacheline
                    output_root_directory=".",
                )
            )
    # experiments.extend(bfs_reg_8x_pq_experiments)



    # SSSP bcsstk32, 12 8KB and 256 KB (can probably remove 128 KB)
    bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode1 = []
    net_lat = 120
    for remote_init in ["true"]:  # "false"
        for num_B in [131072, 262144]:
            for bw_scalefactor in [4, 8, 32]:
                localdram_size_str = "{}B".format(num_B)
                command_str = sssp_bcsstk32_base_options.format(
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
    bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode2_thresholds = []
    net_lat = 120
    for remote_init in ["true"]:
        for datamov_threshold in [5, 10]:
            for num_B in [131072, 262144]:
                for bw_scalefactor in [4, 8, 32]:
                    localdram_size_str = "{}B".format(num_B)
                    command_str = sssp_bcsstk32_base_options.format(
                        sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/remote_datamov_threshold={}".format(
                            int(num_B),
                            int(net_lat),
                            int(bw_scalefactor),
                            str(remote_init),
                            int(datamov_threshold),
                        ),
                    )

                    bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode2_thresholds.append(
                        Experiment(
                            experiment_name="bcsstk32_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode2_threshold_{}_pq_cacheline_combined_series".format(
                                localdram_size_str,
                                net_lat,
                                bw_scalefactor,
                                remote_init,
                                datamov_threshold,
                            ),
                            command_str=command_str,
                            experiment_run_configs=pq_cacheline_combined_rmode2_configs,
                            output_root_directory=".",
                        )
                    )
    bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds = []
    net_lat = 120
    for remote_init in ["true"]:
        for mode_switch_threshold in ["0.6", "0.7", "0.8"]:
            for datamov_threshold in [5, 10]:
                for num_B in [131072, 262144]:
                    for bw_scalefactor in [4, 8, 32]:
                        localdram_size_str = "{}B".format(num_B)
                        command_str = sssp_bcsstk32_base_options.format(
                            sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/r_mode_5_page_queue_utilization_mode_switch_threshold={} -g perf_model/dram/remote_datamov_threshold={}".format(
                                int(num_B),
                                int(net_lat),
                                int(bw_scalefactor),
                                str(remote_init),
                                str(mode_switch_threshold),
                                int(datamov_threshold),
                            ),
                        )

                        bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds.append(
                            Experiment(
                                experiment_name="bcsstk32_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_pq_cacheline_combined_series".format(
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    remote_init,
                                    mode_switch_threshold,
                                    datamov_threshold,
                                ),
                                command_str=command_str,
                                experiment_run_configs=pq_cacheline_combined_rmode5_configs,
                                output_root_directory=".",
                            )
                        )


    # BFS, 8 MB
    bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode1 = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    net_lat = 120
    for remote_init in ["true"]:  # "false"
        for num_MB in [8]:
            for bw_scalefactor in [4, 8, 32]:
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

                bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode1.append(
                    Experiment(
                        experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_pq_cacheline_combined_series".format(
                            application_name.lower(),
                            ""
                            if ligra_input_selection == "regular_input"
                            else ligra_input_selection + "_",
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
    
    bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode2_thresholds = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    net_lat = 120
    for remote_init in ["true"]:
        for datamov_threshold in [5, 10]:
            for num_MB in [8]:  # 16
                for bw_scalefactor in [4, 32]:  # 8
                    localdram_size_str = "{}MB".format(num_MB)
                    command_str = ligra_base_str_options.format(
                        application_name,
                        ligra_input_file,
                        sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/remote_datamov_threshold={}".format(
                            int(num_MB * ONE_MB_TO_BYTES),
                            int(net_lat),
                            int(bw_scalefactor),
                            str(remote_init),
                            int(datamov_threshold),
                        ),
                    )

                    bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode2_thresholds.append(
                        Experiment(
                            experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode2_threshold_{}_pq_cacheline_combined_series".format(
                                application_name.lower(),
                                ""
                                if ligra_input_selection == "regular_input"
                                else ligra_input_selection + "_",
                                localdram_size_str,
                                net_lat,
                                bw_scalefactor,
                                remote_init,
                                datamov_threshold,
                            ),
                            command_str=command_str,
                            experiment_run_configs=pq_cacheline_combined_rmode2_configs,
                            output_root_directory=".",
                        )
                    )
    bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    net_lat = 120
    for remote_init in ["true"]:
        for mode_switch_threshold in ["0.7"]:
            for datamov_threshold in [5, 10]:
                for num_MB in [8]:  # 16
                    for bw_scalefactor in [4, 8, 32]:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = ligra_base_str_options.format(
                            application_name,
                            ligra_input_file,
                            sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/r_mode_5_page_queue_utilization_mode_switch_threshold={} -g perf_model/dram/remote_datamov_threshold={}".format(
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                int(bw_scalefactor),
                                str(remote_init),
                                str(mode_switch_threshold),
                                int(datamov_threshold),
                            ),
                        )

                        bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds.append(
                            Experiment(
                                experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_pq_cacheline_combined_series".format(
                                    application_name.lower(),
                                    ""
                                    if ligra_input_selection == "regular_input"
                                    else ligra_input_selection + "_",
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    remote_init,
                                    mode_switch_threshold,
                                    datamov_threshold,
                                ),
                                command_str=command_str,
                                experiment_run_configs=pq_cacheline_combined_rmode5_configs,
                                output_root_directory=".",
                            )
                        )
    bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds_add = []
    net_lat = 120
    for remote_init in ["true"]:
        for mode_switch_threshold in ["0.6", "0.8", "0.9"]:
            for datamov_threshold in [5, 10]:
                for num_MB in [8]:  # 16
                    for bw_scalefactor in [4, 32]:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = ligra_base_str_options.format(
                            application_name,
                            ligra_input_file,
                            sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/r_mode_5_page_queue_utilization_mode_switch_threshold={} -g perf_model/dram/remote_datamov_threshold={}".format(
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                int(bw_scalefactor),
                                str(remote_init),
                                str(mode_switch_threshold),
                                int(datamov_threshold),
                            ),
                        )

                        bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds_add.append(
                            Experiment(
                                experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_pq_cacheline_combined_series".format(
                                    application_name.lower(),
                                    ""
                                    if ligra_input_selection == "regular_input"
                                    else ligra_input_selection + "_",
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    remote_init,
                                    mode_switch_threshold,
                                    datamov_threshold,
                                ),
                                command_str=command_str,
                                experiment_run_configs=pq_cacheline_combined_rmode5_configs,
                                output_root_directory=".",
                            )
                        )


    # Darknet tiny, 2 MB
    darknet_all_models_pq_cacheline_combined_experiments = []
    net_lat = 120
    for model_type in ["tiny", "darknet19", "resnet50"]:
        for num_MB in [2]:
            for bw_scalefactor in [4, 8, 32]:
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

                darknet_all_models_pq_cacheline_combined_experiments.append(
                    Experiment(
                        experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_pq_cacheline_combined_series".format(
                            model_type.lower(), localdram_size_str, net_lat, bw_scalefactor
                        ),
                        command_str=command_str,
                        experiment_run_configs=pq_cacheline_combined_rmode1_configs,
                        output_root_directory=".",
                    )
                )

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

    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode2_thresholds = []
    net_lat = 120
    for model_type in ["tiny"]:
        for remote_init in ["true"]:
            for datamov_threshold in [5, 10]:
                for num_MB in [2]:
                    for bw_scalefactor in [4, 32]:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = darknet_base_str_options.format(
                            model_type,
                            sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/remote_datamov_threshold={} -s stop-by-icount:{}".format(
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                int(bw_scalefactor),
                                str(remote_init),
                                int(datamov_threshold),
                                int(1 * ONE_BILLION),
                            ),
                        )
                        # 1 billion instructions cap

                        darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode2_thresholds.append(
                            Experiment(
                                experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode2_threshold_{}_pq_cacheline_combined_series".format(
                                    model_type.lower(),
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    remote_init,
                                    datamov_threshold,
                                ),
                                command_str=command_str,
                                experiment_run_configs=pq_cacheline_combined_rmode2_configs,
                                output_root_directory=".",
                            )
                        )
    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds = []
    net_lat = 120
    for model_type in ["tiny"]:
        for remote_init in ["true"]:
            for mode_switch_threshold in ["0.7"]:
                for datamov_threshold in [5, 10]:
                    for num_MB in [2]:
                        for bw_scalefactor in [4, 8, 32]:
                            localdram_size_str = "{}MB".format(num_MB)
                            command_str = darknet_base_str_options.format(
                                model_type,
                                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/r_mode_5_page_queue_utilization_mode_switch_threshold={} -g perf_model/dram/remote_datamov_threshold={} -s stop-by-icount:{}".format(
                                    int(num_MB * ONE_MB_TO_BYTES),
                                    int(net_lat),
                                    int(bw_scalefactor),
                                    str(remote_init),
                                    str(mode_switch_threshold),
                                    int(datamov_threshold),
                                    int(1 * ONE_BILLION),
                                ),
                            )
                            # 1 billion instructions cap

                            darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds.append(
                                Experiment(
                                    experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_pq_cacheline_combined_series".format(
                                        model_type.lower(),
                                        localdram_size_str,
                                        net_lat,
                                        bw_scalefactor,
                                        remote_init,
                                        mode_switch_threshold,
                                        datamov_threshold,
                                    ),
                                    command_str=command_str,
                                    experiment_run_configs=pq_cacheline_combined_rmode5_configs,
                                    output_root_directory=".",
                                )
                            )
    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds_add = []
    net_lat = 120
    for model_type in ["tiny"]:
        for remote_init in ["true"]:
            for mode_switch_threshold in ["0.6", "0.8", "0.9"]:
                for datamov_threshold in [5, 10]:
                    for num_MB in [2]:
                        for bw_scalefactor in [4, 32]:
                            localdram_size_str = "{}MB".format(num_MB)
                            command_str = darknet_base_str_options.format(
                                model_type,
                                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/r_mode_5_page_queue_utilization_mode_switch_threshold={} -g perf_model/dram/remote_datamov_threshold={} -s stop-by-icount:{}".format(
                                    int(num_MB * ONE_MB_TO_BYTES),
                                    int(net_lat),
                                    int(bw_scalefactor),
                                    str(remote_init),
                                    str(mode_switch_threshold),
                                    int(datamov_threshold),
                                    int(1 * ONE_BILLION),
                                ),
                            )
                            # 1 billion instructions cap

                            darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds.append(
                                Experiment(
                                    experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_pq_cacheline_combined_series".format(
                                        model_type.lower(),
                                        localdram_size_str,
                                        net_lat,
                                        bw_scalefactor,
                                        remote_init,
                                        mode_switch_threshold,
                                        datamov_threshold,
                                    ),
                                    command_str=command_str,
                                    experiment_run_configs=pq_cacheline_combined_rmode5_configs,
                                    output_root_directory=".",
                                )
                            )


    # Bandwidth Verification experiments
    queue_delay_cap_configs_99 = []
    for config in queue_delay_cap_configs:
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entry(
            ConfigEntry(
                "perf_model/dram",
                "remote_page_queue_utilization_threshold",
                "0.99",
            )
        )
        queue_delay_cap_configs_99.append(config_copy)
    
    queue_delay_cap_configs_95 = []
    for config in queue_delay_cap_configs:
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entry(
            ConfigEntry(
                "perf_model/dram",
                "remote_page_queue_utilization_threshold",
                "0.95",
            )
        )
        queue_delay_cap_configs_95.append(config_copy)

    bcsstk32_bw_verification_experiments_99 = []
    net_lat = 120
    for num_B in [131072, 262144]:
        for bw_scalefactor in [4, 8, 32]:
            localdram_size_str = "{}B".format(num_B)
            command_str = sssp_bcsstk32_base_options.format(
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={}".format(
                    int(num_B), int(net_lat), int(bw_scalefactor),
                ),
            )

            bcsstk32_bw_verification_experiments_99.append(
                Experiment(
                    experiment_name="bcsstk32_localdram_{}_netlat_{}_bw_scalefactor_{}_verification_series".format(
                        localdram_size_str, net_lat, bw_scalefactor,
                    ),
                    command_str=command_str,
                    experiment_run_configs=queue_delay_cap_configs_99,
                    output_root_directory=".",
                )
            )

    # BFS, 8 MB
    bfs_bw_verification_experiments_99 = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    net_lat = 120
    for num_MB in [8]:
        for bw_scalefactor in [4, 8, 32]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = ligra_base_str_options.format(
                application_name,
                ligra_input_file,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={}".format(
                    int(num_MB * ONE_MB_TO_BYTES), int(net_lat), int(bw_scalefactor),
                ),
            )

            bfs_bw_verification_experiments_99.append(
                Experiment(
                    experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_verification_series".format(
                        application_name.lower(),
                        ""
                        if ligra_input_selection == "regular_input"
                        else ligra_input_selection + "_",
                        localdram_size_str,
                        net_lat,
                        bw_scalefactor,
                    ),
                    command_str=command_str,
                    experiment_run_configs=queue_delay_cap_configs_99,
                    output_root_directory=".",
                )
            )

    darknet_tiny_2MB_bw_verification_experiments_99 = []
    net_lat = 120
    for model_type in ["tiny"]:
        for num_MB in [2]:
            for bw_scalefactor in [4, 8, 32]:
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

                darknet_tiny_2MB_bw_verification_experiments_99.append(
                    Experiment(
                        experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_pq_cacheline_combined_series".format(
                            model_type.lower(), localdram_size_str, net_lat, bw_scalefactor
                        ),
                        command_str=command_str,
                        experiment_run_configs=queue_delay_cap_configs_99,
                        output_root_directory=".",
                    )
                )


    bcsstk32_bw_verification_experiments_95 = []
    net_lat = 120
    for num_B in [131072, 262144]:
        for bw_scalefactor in [4, 8, 32]:
            localdram_size_str = "{}B".format(num_B)
            command_str = sssp_bcsstk32_base_options.format(
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={}".format(
                    int(num_B), int(net_lat), int(bw_scalefactor),
                ),
            )

            bcsstk32_bw_verification_experiments_95.append(
                Experiment(
                    experiment_name="bcsstk32_localdram_{}_netlat_{}_bw_scalefactor_{}_verification_95_series".format(
                        localdram_size_str, net_lat, bw_scalefactor
                    ),
                    command_str=command_str,
                    experiment_run_configs=queue_delay_cap_configs_95,
                    output_root_directory=".",
                )
            )

    # BFS, 8, 16 MB
    bfs_bw_verification_experiments_95 = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    net_lat = 120
    for num_MB in [8]:  # 16
        for bw_scalefactor in [4, 8, 32]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = ligra_base_str_options.format(
                application_name,
                ligra_input_file,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={}".format(
                    int(num_MB * ONE_MB_TO_BYTES), int(net_lat), int(bw_scalefactor),
                ),
            )

            bfs_bw_verification_experiments_95.append(
                Experiment(
                    experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_verification_95_series".format(
                        application_name.lower(),
                        ""
                        if ligra_input_selection == "regular_input"
                        else ligra_input_selection + "_",
                        localdram_size_str,
                        net_lat,
                        bw_scalefactor,
                    ),
                    command_str=command_str,
                    experiment_run_configs=queue_delay_cap_configs_95,
                    output_root_directory=".",
                )
            )

    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_ideal_pagethrottling_window_size = []
    net_lat = 120
    remote_init = "true"
    for model_type in ["tiny"]:
        for window_size in [10**4, 10**5 / 5, 10**5 * 5, 10**6]:
            for num_MB in [2]:
                for bw_scalefactor in [4, 32]:
                    localdram_size_str = "{}MB".format(num_MB)
                    command_str = darknet_base_str_options.format(
                        model_type,
                        sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/m_r_ideal_pagethrottle_remote_access_history_window_size={} -s stop-by-icount:{}".format(
                            int(num_MB * ONE_MB_TO_BYTES),
                            int(net_lat),
                            int(bw_scalefactor),
                            str(remote_init),
                            int(window_size),
                            int(1 * ONE_BILLION),
                        ),
                    )
                    # 1 billion instructions cap

                    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_ideal_pagethrottling_window_size.append(
                        Experiment(
                            experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_cacheline_combined_series".format(
                                model_type.lower(), localdram_size_str, net_lat, bw_scalefactor, remote_init, int(window_size)
                            ),
                            command_str=command_str,
                            experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                            output_root_directory=".",
                        )
                    )
    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode2_ideal_pagethrottling_window_size_add = []
    net_lat = 120
    for model_type in ["tiny"]:
        for remote_init in ["true"]:
            for window_size in [10**4, 10**6]:
                for datamov_threshold in [10, 20]:
                    for num_MB in [2]:
                        for bw_scalefactor in [4, 32]:
                            localdram_size_str = "{}MB".format(num_MB)
                            command_str = darknet_base_str_options.format(
                                model_type,
                                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/remote_datamov_threshold={} -g perf_model/dram/m_r_ideal_pagethrottle_remote_access_history_window_size={} -s stop-by-icount:{}".format(
                                    int(num_MB * ONE_MB_TO_BYTES),
                                    int(net_lat),
                                    int(bw_scalefactor),
                                    str(remote_init),
                                    int(datamov_threshold),
                                    int(window_size),
                                    int(1 * ONE_BILLION),
                                ),
                            )
                            # 1 billion instructions cap

                            darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode2_ideal_pagethrottling_window_size_add.append(
                                Experiment(
                                    experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode2_threshold_{}_idealwinsize_{}_pq_cacheline_combined_series".format(
                                        model_type.lower(),
                                        localdram_size_str,
                                        net_lat,
                                        bw_scalefactor,
                                        remote_init,
                                        datamov_threshold,
                                        int(window_size)
                                    ),
                                    command_str=command_str,
                                    experiment_run_configs=pq_cacheline_combined_rmode2_configs_ideal_page_throttling,
                                    output_root_directory=".",
                                )
                            )
    bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_ideal_pagethrottling_window_size = []
    net_lat = 120
    remote_init = "true"
    for window_size in [10**4, 10**5 / 5, 10**5 * 5, 10**6]:
        for num_B in [131072, 262144]:
            for bw_scalefactor in [4, 8, 32]:
                localdram_size_str = "{}B".format(num_B)
                command_str = sssp_bcsstk32_base_options.format(
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/m_r_ideal_pagethrottle_remote_access_history_window_size={}".format(
                        int(num_B), int(net_lat), int(bw_scalefactor), str(remote_init), int(window_size),
                    ),
                )

                bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_ideal_pagethrottling_window_size.append(
                    Experiment(
                        experiment_name="bcsstk32_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_cacheline_combined_series".format(
                            localdram_size_str, net_lat, bw_scalefactor, remote_init, int(window_size)
                        ),
                        command_str=command_str,
                        experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                        output_root_directory=".",
                    )
                )
    bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode2_ideal_pagethrottling_window_size_add = []
    net_lat = 120
    for remote_init in ["true"]:
        for window_size in [10**4, 10**6]:
            for datamov_threshold in [5, 10]:
                for num_B in [262144]:
                    for bw_scalefactor in [4, 8, 32]:
                        localdram_size_str = "{}B".format(num_B)
                        command_str = sssp_bcsstk32_base_options.format(
                            sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/remote_datamov_threshold={} -g perf_model/dram/m_r_ideal_pagethrottle_remote_access_history_window_size={}".format(
                                int(num_B),
                                int(net_lat),
                                int(bw_scalefactor),
                                str(remote_init),
                                int(datamov_threshold),
                                int(window_size)
                            ),
                        )

                        bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode2_ideal_pagethrottling_window_size_add.append(
                            Experiment(
                                experiment_name="bcsstk32_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode2_threshold_{}_idealwinsize_{}_pq_cacheline_combined_series".format(
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    remote_init,
                                    datamov_threshold,
                                    int(window_size),
                                ),
                                command_str=command_str,
                                experiment_run_configs=pq_cacheline_combined_rmode2_configs_ideal_page_throttling,
                                output_root_directory=".",
                            )
                        )
    bfs_pq_cacheline_combined_experiments_remoteinit_true_ideal_pagethrottling_window_size = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    net_lat = 120
    remote_init = "true"
    for num_MB in [8]:  # 16
        for window_size in [10**4, 10**5 / 5, 10**5 * 5, 10**6]:
            for bw_scalefactor in [4, 8, 32]:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = ligra_base_str_options.format(
                    application_name,
                    ligra_input_file,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/m_r_ideal_pagethrottle_remote_access_history_window_size={}".format(
                        int(num_MB * ONE_MB_TO_BYTES), int(net_lat), int(bw_scalefactor), str(remote_init), int(window_size)
                    ),
                )

                bfs_pq_cacheline_combined_experiments_remoteinit_true_ideal_pagethrottling_window_size.append(
                    Experiment(
                        experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_cacheline_combined_series".format(
                            application_name.lower(),
                            ""
                            if ligra_input_selection == "regular_input"
                            else ligra_input_selection + "_",
                            localdram_size_str,
                            net_lat,
                            bw_scalefactor,
                            remote_init,
                            int(window_size)
                        ),
                        command_str=command_str,
                        experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                        output_root_directory=".",
                    )
                )
    bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode2_ideal_pagethrottling_window_size_add = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    net_lat = 120
    for remote_init in ["true"]:
        for window_size in [10**4, 10**6]:
            for datamov_threshold in [5, 10]:
                for num_MB in [8]:  # 16
                    for bw_scalefactor in [4, 32]:  # 8
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = ligra_base_str_options.format(
                            application_name,
                            ligra_input_file,
                            sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/remote_datamov_threshold={} -g perf_model/dram/m_r_ideal_pagethrottle_remote_access_history_window_size={}".format(
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                int(bw_scalefactor),
                                str(remote_init),
                                int(datamov_threshold),
                                int(window_size),
                            ),
                        )

                        bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode2_ideal_pagethrottling_window_size_add.append(
                            Experiment(
                                experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode2_threshold_{}_idealwinsize_{}_pq_cacheline_combined_series".format(
                                    application_name.lower(),
                                    ""
                                    if ligra_input_selection == "regular_input"
                                    else ligra_input_selection + "_",
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    remote_init,
                                    datamov_threshold,
                                    int(window_size)
                                ),
                                command_str=command_str,
                                experiment_run_configs=pq_cacheline_combined_rmode2_configs_ideal_page_throttling,
                                output_root_directory=".",
                            )
                        )


    # experiments.extend(bcsstk32_bw_verification_experiments_99)
    # experiments.extend(bfs_bw_verification_experiments_99)
    # experiments.extend(darknet_tiny_2MB_bw_verification_experiments_99)
    # experiments.extend(bcsstk32_bw_verification_experiments_95)
    # experiments.extend(bfs_bw_verification_experiments_95)


    # experiments.extend(bcsstk32_pq_cacheline_combined_experiments_remoteinit_false)
    # experiments.extend(bcsstk32_pq_cacheline_combined_experiments_remoteinit_true)
    # experiments.extend(bcsstk32_pq_cacheline_combined_experiments_remoteinit_false_rmode2_thresholds)

    # experiments.extend(bfs_pq_cacheline_combined_experiments_remoteinit_false)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_false)

    # experiments.extend(bfs_pq_cacheline_combined_experiments_remoteinit_false_rmode2_thresholds)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_false_rmode2_thresholds)
    
    # experiments.extend(bfs_pq_cacheline_combined_experiments_remoteinit_true)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true)


    # experiments.extend(bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode2_thresholds)
    # experiments.extend(bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode2_thresholds)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode2_thresholds

    # experiments.extend(bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds)
    # experiments.extend(bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds)

    # experiments.extend(bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds_add)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds_add)


    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_window_size)
    # experiments.extend(bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_window_size)
    # experiments.extend(bfs_pq_cacheline_combined_experiments_remoteinit_true_window_size)

    # experiments.extend(bcsstk32_pq_cacheline_combined_experiments_remoteinit_true_rmode2_window_size_add)
    # experiments.extend(bfs_pq_cacheline_combined_experiments_remoteinit_true_rmode2_window_size_add)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode2_window_size_add)

 
  
    ### Run Sniper experiments using ExperimentManager ###
    # Find log filename, to not overwrite previous logs
    log_filename = "run-sniper-repeat_1.log"
    num = 2
    while os.path.isfile(log_filename):
        log_filename = "run-sniper-repeat_{}.log".format(num)
        num += 1

    with open(log_filename, "w") as log_file:
        log_str = "Script start time: {}".format(datetime.datetime.now().astimezone())
        print(log_str)
        print(log_str, file=log_file)

        experiment_manager = ExperimentManager(
            output_root_directory=".", max_concurrent_processes=16, log_file=log_file
        )
        experiment_manager.add_experiments(experiments)
        experiment_manager.start(
            manager_sleep_interval_seconds=60
        )  # main thread sleep for 60 second intervals while waiting

        log_str = "Script end time: {}".format(datetime.datetime.now().astimezone())
        print(log_str)
        print(log_str, file=log_file)
