# Python 3
from run_sniper_repeat_base import *

# For timezones
import pytz

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
    sssp_int_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/crono/apps/sssp/sssp_int {sniper_root}/benchmarks/crono/inputs/{{0}} 1".format(
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
    nw_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/rodinia/bin/needle {{0}} 1 1".format(
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
    ligra_base_str_options_sym = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/apps/{{0}} -s -rounds 1 {0}/inputs/{{1}}".format(
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
        "regular_input_sym": "rMat_1000000sym",
    }

    def compiled_application_checker(experiments: List[Experiment]):
        # Temporary function
        # Assumes the cwd is this file's containing directory
        compiled_application_to_file_path = {"spmv": ["{sniper_root}/benchmarks/spmv/bench_spdmv".format(sniper_root=subfolder_sniper_root_relpath)],
                                             "stream": ["{sniper_root}/benchmarks/stream/stream_sniper".format(sniper_root=subfolder_sniper_root_relpath)],
                                             "darknet": ["{0}/darknet".format(darknet_home)],
                                            }
        for ligra_application in ["BFS", "BC", "Components", "Triangle", "PageRank"]:
            compiled_application_to_file_path["ligra_" + ligra_application] = ["{0}/apps/{1}".format(ligra_home, ligra_application)]
        # if it's not any of the above, it's sssp
        compiled_application_to_file_path[""] = ["{sniper_root}/benchmarks/crono/apps/sssp/sssp_int".format(sniper_root=subfolder_sniper_root_relpath)]

        compiled_application_missing = False
        for experiment in experiments:
            found = False
            for key in compiled_application_to_file_path.keys():
                if key.lower() in experiment.experiment_name.lower():
                    found = True
                    for file_path in compiled_application_to_file_path[key]:
                        if not os.path.exists(os.path.relpath(file_path, start="../..")):
                            print("Error: couldn't find input {} at {}".format(key, os.path.relpath(file_path, start="../..")))
                            compiled_application_missing = True
                    break
            if not found:
                print("{} didn't match any of the input file patterns".format(experiment.experiment_name))
        if compiled_application_missing:
            raise FileNotFoundError()

    def input_file_checker(experiments: List[Experiment]):
        # Temporary function
        # Assumes the cwd is this file's containing directory
        input_to_file_path = {"roadnetPA": ["{sniper_root}/benchmarks/crono/inputs/roadNet-PA.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                              "roadnetCA": ["{sniper_root}/benchmarks/crono/inputs/roadNet-CA.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                              "bcsstk32": ["{sniper_root}/benchmarks/crono/inputs/bcsstk32.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                              "citPatents": ["{sniper_root}/benchmarks/crono/inputs/cit-Patents.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                              "socPokec": ["{sniper_root}/benchmarks/crono/inputs/soc-Pokec.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                              "comOrkut": ["{sniper_root}/benchmarks/crono/inputs/com-Orkut.mtx".format(sniper_root=subfolder_sniper_root_relpath)],
                            #   "small_input": ["{0}/inputs/{1}".format(ligra_home, ligra_input_to_file["small_input"])],
                              "reg_8x": ["{0}/inputs/{1}".format(ligra_home, ligra_input_to_file["reg_8x"])],
                              "reg_10x": ["{0}/inputs/{1}".format(ligra_home, ligra_input_to_file["reg_10x"])],
                              "regular_input_sym": ["{0}/inputs/{1}".format(ligra_home, ligra_input_to_file["regular_input_sym"])],
                              "ligra": ["{0}/inputs/{1}".format(ligra_home, ligra_input_to_file["regular_input"])],
                              "darknet_tiny": ["{0}/{1}.weights".format(darknet_home, "tiny"), "{0}/cfg/{1}.cfg".format(darknet_home, "tiny"), "{0}/cfg/imagenet1k.data".format(darknet_home), "{0}/data/dog.jpg".format(darknet_home)],
                              "darknet_darknet19": ["{0}/{1}.weights".format(darknet_home, "darknet19"), "{0}/cfg/{1}.cfg".format(darknet_home, "darknet19"), "{0}/cfg/imagenet1k.data".format(darknet_home), "{0}/data/dog.jpg".format(darknet_home)],
                              "darknet_resnet50": ["{0}/{1}.weights".format(darknet_home, "resnet50"), "{0}/cfg/{1}.cfg".format(darknet_home, "resnet50"), "{0}/cfg/imagenet1k.data".format(darknet_home), "{0}/data/dog.jpg".format(darknet_home)],
                              "darknet_vgg16": ["{0}/{1}.weights".format(darknet_home, "vgg-16"), "{0}/cfg/{1}.cfg".format(darknet_home, "vgg-16"), "{0}/cfg/imagenet1k.data".format(darknet_home), "{0}/data/dog.jpg".format(darknet_home)],
                              "stream": [],  # stream doesn't need an input file
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

    # pq_cacheline_combined_base_configs = partition_queue_series_experiment_run_configs[0:5] + cacheline_queue_ratio_configs

    # remote mem off, page move instant, pq0, pq1 with cacheline ratio 0.01, 0.025, 0.05, 0.075 + 0.1, 0.15, 0.2, 0.3, 0.5
    cacheline_queue_ratio_additional = []
    for cacheline_queue_ratio in [
        "0.01",
        "0.025",
        "0.05",
        "0.075",
    ]:
        config_copy = copy.deepcopy(cacheline_queue_ratio_config_base)
        config_copy.add_config_entry(
            ConfigEntry(
                "perf_model/dram",
                "remote_cacheline_queue_fraction",
                cacheline_queue_ratio,
            )
        )
        cacheline_queue_ratio_additional.append(config_copy)
    pq_cacheline_combined_base_configs = [partition_queue_series_experiment_run_configs[0],
                                          partition_queue_series_experiment_run_configs[1],
                                          partition_queue_series_experiment_run_configs[4],
                                          cacheline_queue_ratio_additional[0],
                                          cacheline_queue_ratio_additional[1],
                                          cacheline_queue_ratio_additional[2],
                                          cacheline_queue_ratio_additional[3],
                                          cacheline_queue_ratio_configs[0],
                                          cacheline_queue_ratio_configs[1],
                                          cacheline_queue_ratio_configs[2],
                                          cacheline_queue_ratio_configs[4],
                                          cacheline_queue_ratio_configs[8],
                                         ]
    # pq_cacheline_combined_base_configs = [cacheline_queue_ratio_additional[0],
    #                                       cacheline_queue_ratio_additional[1],
    #                                       cacheline_queue_ratio_additional[2],
    #                                       cacheline_queue_ratio_additional[3],
    #                                       cacheline_queue_ratio_additional[4],
    #                                       cacheline_queue_ratio_configs[0],
    #                                      ]

    pq_cacheline_combined_rmode1_configs = []
    # Only want runs number 1-5 in partition_queue_series_experiment_run_configs
    for config in pq_cacheline_combined_base_configs:
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entries(
            [
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
                ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
                ConfigEntry("perf_model/dram", "enable_remote_prefetcher", "false"),
                ConfigEntry("perf_model/dram", "remote_memory_mode", "1"),
                # remote_init  specified in individual experiments
            ]
        )
        pq_cacheline_combined_rmode1_configs.append(config_copy)

    pq_cacheline_combined_rmode1_configs_prefetch = []
    # Only want runs number 1-5 in partition_queue_series_experiment_run_configs
    for config in pq_cacheline_combined_rmode1_configs:
        config_copy = copy.deepcopy(config)
        config_copy.replace_config_entries(
            [
                ConfigEntry("perf_model/dram", "enable_remote_prefetcher", "true"),
                # remote_init  specified in individual experiments
            ]
        )
        pq_cacheline_combined_rmode1_configs_prefetch.append(config_copy)

    pq_cacheline_combined_rmode2_configs = []
    # Only want runs number 1-5 in partition_queue_series_experiment_run_configs
    for config in pq_cacheline_combined_base_configs:
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entries(
            [
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
                ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
                ConfigEntry("perf_model/dram", "enable_remote_prefetcher", "false"),
                ConfigEntry("perf_model/dram", "remote_memory_mode", "2"),
                # remote_init  specified in individual experiments
                # remote_datamov_threshold  specified in individual experiments
            ]
        )
        pq_cacheline_combined_rmode2_configs.append(config_copy)

    pq_cacheline_combined_rmode5_configs = []
    # Only want runs number 1-5 in partition_queue_series_experiment_run_configs
    for config in pq_cacheline_combined_base_configs:
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entries(
            [
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
                ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "false"),
                ConfigEntry("perf_model/dram", "enable_remote_prefetcher", "false"),
                ConfigEntry("perf_model/dram", "remote_memory_mode", "5"),
                # remote_init  specified in individual experiments
                # remote_datamov_threshold  specified in individual experiments
                # r_mode_5_page_queue_utilization_mode_switch_threshold  specified in individual experiments
                ConfigEntry("perf_model/dram", "r_mode_5_remote_access_history_window_size", "100000"),
            ]
        )
        pq_cacheline_combined_rmode5_configs.append(config_copy)

    pq_cacheline_combined_rmode1_configs_ideal_page_throttling = []
    # Only want runs number 1-5 in partition_queue_series_experiment_run_configs
    for config in pq_cacheline_combined_rmode1_configs:
        config_copy = copy.deepcopy(config)
        config_copy.replace_config_entries(
            [
                ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "true"),
                ConfigEntry("perf_model/dram", "enable_remote_prefetcher", "false"),
                # remote_init  specified in individual experiments
            ]
        )
        pq_cacheline_combined_rmode1_configs_ideal_page_throttling.append(config_copy)

    pq_cacheline_combined_rmode2_configs_ideal_page_throttling = []
    for config in pq_cacheline_combined_rmode2_configs:
        config_copy = copy.deepcopy(config)
        config_copy.replace_config_entries(
            [
                ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "true"),
                ConfigEntry("perf_model/dram", "enable_remote_prefetcher", "false"),
                # remote_init  specified in individual experiments
                # remote_datamov_threshold  specified in individual experiments
            ]
        )
        pq_cacheline_combined_rmode2_configs_ideal_page_throttling.append(config_copy)

    pq_cacheline_combined_rmode5_configs_ideal_page_throttling = []
    for config in pq_cacheline_combined_rmode5_configs:
        config_copy = copy.deepcopy(config)
        config_copy.replace_config_entries(
            [
                ConfigEntry("perf_model/dram", "r_use_ideal_page_throttling", "true"),
                ConfigEntry("perf_model/dram", "enable_remote_prefetcher", "false"),
                # remote_init  specified in individual experiments
                # remote_datamov_threshold  specified in individual experiments
                # r_mode_5_page_queue_utilization_mode_switch_threshold  specified in individual experiments
            ]
        )
        pq_cacheline_combined_rmode5_configs_ideal_page_throttling.append(config_copy)



    #################################

    experiments = []


    # SSSP, SPMV test, with larger matrices
    spmv_new_pq_cacheline_combined_experiments_remoteinit_true_rmode1_test = []
    net_lat = 120
    remote_init = "true"
    for matrix, num_MB in [("com-Orkut.mtx", 8), ("com-Orkut.mtx", 16), ("soc-Pokec.mtx", 4), ("soc-Pokec.mtx", 8), ("soc-Pokec.mtx", 12)]:
        for bw_scalefactor in [4]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = spmv_base_options.format(
                matrix,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                    int(num_MB * ONE_MB_TO_BYTES),
                    int(net_lat),
                    int(bw_scalefactor),
                    str(remote_init),
                ),
            )

            spmv_new_pq_cacheline_combined_experiments_remoteinit_true_rmode1_test.append(
                Experiment(
                    experiment_name="spmv_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_test".format(
                        matrix[:matrix.find(".")].replace("-", ""),
                        localdram_size_str,
                        net_lat,
                        bw_scalefactor,
                        remote_init,
                    ),
                    command_str=command_str,
                    experiment_run_configs=[
                        pq_cacheline_combined_rmode1_configs[2],
                        pq_cacheline_combined_rmode1_configs[-3],
                    ],  # pq=0 + pq=1 w/ 0.2 cacheline
                    output_root_directory=".",
                )
            )
    sssp_new_pq_cacheline_combined_experiments_remoteinit_true_rmode1_test = []
    net_lat = 120
    remote_init = "true"  # "false"
    for matrix in ["cit-Patents.mtx"]:
        for num_MB in [8, 16]:
            for bw_scalefactor in [4]:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = sssp_int_base_options.format(
                    matrix,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                    ),
                )

                sssp_new_pq_cacheline_combined_experiments_remoteinit_true_rmode1_test.append(
                    Experiment(
                        experiment_name="{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_test".format(
                            matrix[:matrix.find(".")].replace("-", ""),
                            localdram_size_str,
                            net_lat,
                            bw_scalefactor,
                            remote_init,
                        ),
                        command_str=command_str,
                        experiment_run_configs=[
                            pq_cacheline_combined_rmode1_configs[2],
                            pq_cacheline_combined_rmode1_configs[-3],
                        ],  # pq=0 + pq=1 w/ 0.2 cacheline
                        output_root_directory=".",
                    )
                )


    # BFS, reg_8x, 1 Billion instructions cap
    bfs_reg_8x_pq_experiments = []
    ligra_input_selection = "reg_8x"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    net_lat = 120
    for num_MB in [8, 12, 16]:
        for bw_scalefactor in [4]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = ligra_base_str_options_sym.format(
                application_name,
                ligra_input_file,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                    int(num_MB * ONE_MB_TO_BYTES), int(net_lat), int(bw_scalefactor), int(1 * ONE_BILLION)
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
                        pq_cacheline_combined_rmode1_configs[2],
                        pq_cacheline_combined_rmode1_configs[-3],
                    ],  # pq=0 + pq=1 w/ 0.2 cacheline
                    output_root_directory=".",
                )
            )
    # experiments.extend(bfs_reg_8x_pq_experiments)

    # SSSP Roadnet
    sssp_roadNetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode1 = []
    net_lat = 120
    matrix = "roadNet-CA.mtx"
    for remote_init in ["true"]:  # "false"
        for num_MB in [2, 3]:
            for bw_scalefactor in [4, 8, 16, 32]:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = sssp_int_base_options.format(
                    matrix,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                    ),
                )

                sssp_roadNetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode1.append(
                    Experiment(
                        experiment_name="{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_pq_newer_series".format(
                            matrix[:matrix.find(".")].replace("-", ""),
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
    sssp_roadNetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling = []
    net_lat = 120
    matrix = "roadNet-CA.mtx"
    for remote_init in ["true"]:  # "false"
        for num_MB in [2, 3]:
            for bw_scalefactor in [4, 8, 16, 32]:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = sssp_int_base_options.format(
                    matrix,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                    ),
                )

                sssp_roadNetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling.append(
                    Experiment(
                        experiment_name="{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_newer_series".format(
                            matrix[:matrix.find(".")].replace("-", ""),
                            localdram_size_str,
                            net_lat,
                            bw_scalefactor,
                            remote_init,
                            int(10**5)
                        ),
                        command_str=command_str,
                        experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                        output_root_directory=".",
                    )
                )
    sssp_roadNetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds = []
    net_lat = 120
    remote_init = "true"
    matrix = "roadNet-CA.mtx"
    for num_MB in [2, 3]:
        for mode_switch_threshold in ["0.6", "0.7", "0.8", "0.9"]:
            for datamov_threshold in [2, 5, 10]:
                for bw_scalefactor in [4, 8, 16, 32]:
                    localdram_size_str = "{}MB".format(num_MB)
                    command_str = sssp_int_base_options.format(
                        matrix,
                        sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/r_mode_5_page_queue_utilization_mode_switch_threshold={} -g perf_model/dram/remote_datamov_threshold={}".format(
                            int(num_MB * ONE_MB_TO_BYTES),
                            int(net_lat),
                            int(bw_scalefactor),
                            str(remote_init),
                            str(mode_switch_threshold),
                            int(datamov_threshold),
                        ),
                    )

                    sssp_roadNetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds.append(
                        Experiment(
                            experiment_name="{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_pq_newer_series".format(
                                matrix[:matrix.find(".")].replace("-", ""),
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
    sssp_roadNetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds_ideal_page_throttling = []
    net_lat = 120
    remote_init = "true"
    matrix = "roadNet-CA.mtx"
    for num_MB in [2, 3]:
        for mode_switch_threshold in ["0.6", "0.7", "0.8", "0.9"]:
            for datamov_threshold in [2, 5, 10]:
                for bw_scalefactor in [4, 8, 16, 32]:
                    localdram_size_str = "{}MB".format(num_MB)
                    command_str = sssp_int_base_options.format(
                        matrix,
                        sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/r_mode_5_page_queue_utilization_mode_switch_threshold={} -g perf_model/dram/remote_datamov_threshold={}".format(
                            int(num_MB * ONE_MB_TO_BYTES),
                            int(net_lat),
                            int(bw_scalefactor),
                            str(remote_init),
                            str(mode_switch_threshold),
                            int(datamov_threshold),
                        ),
                    )

                    sssp_roadNetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds_ideal_page_throttling.append(
                        Experiment(
                            experiment_name="{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_idealwinsize_{}_pq_newer_series".format(
                                matrix[:matrix.find(".")].replace("-", ""),
                                localdram_size_str,
                                net_lat,
                                bw_scalefactor,
                                remote_init,
                                mode_switch_threshold,
                                datamov_threshold,
                                int(10**5),
                            ),
                            command_str=command_str,
                            experiment_run_configs=pq_cacheline_combined_rmode5_configs,
                            output_root_directory=".",
                        )
                    )
    


    sssp_roadNetPA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds = []
    net_lat = 120
    remote_init = "true"
    matrix = "roadNet-PA.mtx"
    for num_MB in [1, 2]:
        for mode_switch_threshold in ["0.6", "0.7", "0.8", "0.9"]:
            for datamov_threshold in [2, 5, 10]:
                for bw_scalefactor in [4, 8, 16, 32]:
                    localdram_size_str = "{}MB".format(num_MB)
                    command_str = sssp_int_base_options.format(
                        matrix,
                        sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/r_mode_5_page_queue_utilization_mode_switch_threshold={} -g perf_model/dram/remote_datamov_threshold={}".format(
                            int(num_MB * ONE_MB_TO_BYTES),
                            int(net_lat),
                            int(bw_scalefactor),
                            str(remote_init),
                            str(mode_switch_threshold),
                            int(datamov_threshold),
                        ),
                    )

                    sssp_roadNetPA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds.append(
                        Experiment(
                            experiment_name="{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_pq_newer_series".format(
                                matrix[:matrix.find(".")].replace("-", ""),
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

    sssp_roadNetPA_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling = []
    net_lat = 120
    matrix = "roadNet-PA.mtx"
    for remote_init in ["true"]:  # "false"
        for num_MB in [0.5, 1, 2]:
            for bw_scalefactor in [8, 16, 32]:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = sssp_int_base_options.format(
                    matrix,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                    ),
                )

                sssp_roadNetPA_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling.append(
                    Experiment(
                        experiment_name="{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_newer_series".format(
                            matrix[:matrix.find(".")].replace("-", ""),
                            localdram_size_str,
                            net_lat,
                            bw_scalefactor,
                            remote_init,
                            int(10**5)
                        ),
                        command_str=command_str,
                        experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                        output_root_directory=".",
                    )
                )

    # SPMV, Sparse matrix multiplication
    spmv_roadnetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode1 = []
    net_lat = 120
    remote_init = "true"
    for matrix in ["roadNet-CA.mtx"]:
        for num_MB in [0.5]:
            for bw_scalefactor in [4, 8, 16, 32]:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = spmv_base_options.format(
                    matrix,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                    ),
                )

                spmv_roadnetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode1.append(
                    Experiment(
                        experiment_name="spmv_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_pq_newer_series".format(
                            matrix[:matrix.find(".")].replace("-", ""),
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
    spmv_roadnetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling = []
    net_lat = 120
    remote_init = "true"
    for matrix in ["roadNet-CA.mtx"]:
        for num_MB in [0.5]:
            for bw_scalefactor in [4, 8, 16, 32]:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = spmv_base_options.format(
                    matrix,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                    ),
                )

                spmv_roadnetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling.append(
                    Experiment(
                        experiment_name="spmv_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_newer_series".format(
                            matrix[:matrix.find(".")].replace("-", ""),
                            localdram_size_str,
                            net_lat,
                            bw_scalefactor,
                            remote_init,
                            int(10**5),
                        ),
                        command_str=command_str,
                        experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                        output_root_directory=".",
                    )
                )
    spmv_roadnetCA_roadnetPA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds = []
    net_lat = 120
    remote_init = "true"
    for matrix in ["roadNet-CA.mtx", "roadNet-PA.mtx"]:
        for mode_switch_threshold in ["0.7", "0.8", "0.9"]:
            for datamov_threshold in [2, 5, 10]:
                for num_MB in [0.5]:
                    for bw_scalefactor in [4, 8, 16, 32]:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = spmv_base_options.format(
                            matrix,
                            sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/r_mode_5_page_queue_utilization_mode_switch_threshold={} -g perf_model/dram/remote_datamov_threshold={}".format(
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                int(bw_scalefactor),
                                str(remote_init),
                                str(mode_switch_threshold),
                                int(datamov_threshold),
                            ),
                        )

                        spmv_roadnetCA_roadnetPA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds.append(
                            Experiment(
                                experiment_name="spmv_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_pq_newer_series".format(
                                    matrix[:matrix.find(".")].replace("-", ""),
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
    spmv_roadnetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds_ideal_page_throttling = []
    net_lat = 120
    remote_init = "true"
    for matrix in ["roadNet-CA.mtx"]:
        for mode_switch_threshold in ["0.7", "0.8", "0.9"]:
            for datamov_threshold in [2, 5, 10]:
                for num_MB in [0.5]:
                    for bw_scalefactor in [4, 8, 16, 32]:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = spmv_base_options.format(
                            matrix,
                            sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/r_mode_5_page_queue_utilization_mode_switch_threshold={} -g perf_model/dram/remote_datamov_threshold={}".format(
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                int(bw_scalefactor),
                                str(remote_init),
                                str(mode_switch_threshold),
                                int(datamov_threshold),
                            ),
                        )

                        spmv_roadnetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds_ideal_page_throttling.append(
                            Experiment(
                                experiment_name="spmv_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_idealwinsize_{}_pq_newer_series".format(
                                    matrix[:matrix.find(".")].replace("-", ""),
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    remote_init,
                                    mode_switch_threshold,
                                    datamov_threshold,
                                    int(10**5),
                                ),
                                command_str=command_str,
                                experiment_run_configs=pq_cacheline_combined_rmode5_configs_ideal_page_throttling,
                                output_root_directory=".",
                            )
                        )

    spmv_roadnet_pq_cacheline_combined_experiments_remoteinit_true_rmode1 = []
    net_lat = 120
    remote_init = "true"
    for matrix in ["roadNet-PA.mtx"]:
        for num_B in [524288]:
            for bw_scalefactor in [4, 8, 16, 32]:
                localdram_size_str = "{}B".format(num_B)
                command_str = spmv_base_options.format(
                    matrix,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                        int(num_B),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                    ),
                )

                spmv_roadnet_pq_cacheline_combined_experiments_remoteinit_true_rmode1.append(
                    Experiment(
                        experiment_name="spmv_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_pq_newer_series".format(
                            matrix[:matrix.find(".")].replace("-", ""),
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
    spmv_roadnet_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling = []
    net_lat = 120
    remote_init = "true"
    for matrix in ["roadNet-PA.mtx"]:
        for num_B in [524288]:
            for bw_scalefactor in [4, 8, 16, 32]:
                localdram_size_str = "{}B".format(num_B)
                command_str = spmv_base_options.format(
                    matrix,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                        int(num_B),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                    ),
                )

                spmv_roadnet_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling.append(
                    Experiment(
                        experiment_name="spmv_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_newer_series".format(
                            matrix[:matrix.find(".")].replace("-", ""),
                            localdram_size_str,
                            net_lat,
                            bw_scalefactor,
                            remote_init,
                            int(10**5),
                        ),
                        command_str=command_str,
                        experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                        output_root_directory=".",
                    )
                )

    # Ligra non-symmetric, 4, 8 MB
    ligra_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    net_lat = 120
    remote_init = "true"
    for application_name in ["BC", "Components"]:  # Full execution: Triangle takes a long time, PageRank takes a very long time
        for num_MB in [4, 8]:
            for bw_scalefactor in [4, 8]:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = ligra_base_str_options_nonsym.format(
                    application_name,
                    ligra_input_file,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                        int(1 * ONE_BILLION),
                    ),
                )

                ligra_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal.append(
                    Experiment(
                        experiment_name="ligra_{}_nonsym_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_newer_series".format(
                            application_name.lower(),
                            ""
                            if ligra_input_selection == "regular_input"
                            else ligra_input_selection + "_",
                            localdram_size_str,
                            net_lat,
                            bw_scalefactor,
                            remote_init,
                            int(10**5),
                        ),
                        command_str=command_str,
                        experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                        output_root_directory=".",
                    )
                )
    # Ligra non-symmetric, 4, 8 MB
    ligra_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_pagerank = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    net_lat = 120
    remote_init = "true"
    for application_name in ["PageRank"]:  # Full execution: Triangle takes a long time, PageRank takes a very long time
        for num_MB in [4, 8]:
            for bw_scalefactor in [4, 8]:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = ligra_base_str_options_nonsym.format(
                    application_name,
                    ligra_input_file,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                        int(1 * ONE_BILLION),
                    ),
                )

                ligra_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_pagerank.append(
                    Experiment(
                        experiment_name="ligra_{}_nonsym_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_newer_series".format(
                            application_name.lower(),
                            ""
                            if ligra_input_selection == "regular_input"
                            else ligra_input_selection + "_",
                            localdram_size_str,
                            net_lat,
                            bw_scalefactor,
                            remote_init,
                            int(10**5),
                        ),
                        command_str=command_str,
                        experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                        output_root_directory=".",
                    )
                )
    # Ligra symmetric, 4, 8 MB
    ligra_sym_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal = []
    ligra_input_selection = "regular_input_sym"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    net_lat = 120
    remote_init = "true"
    for application_name in ["Triangle"]:  # "BC", "Components", "Triangle" # Full execution: Triangle takes a long time, PageRank takes a very long time
        for num_MB in [4, 8]:
            for bw_scalefactor in [4, 8]:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = ligra_base_str_options_sym.format(
                    application_name,
                    ligra_input_file,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                        int(1 * ONE_BILLION),
                    ),
                )

                ligra_sym_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal.append(
                    Experiment(
                        experiment_name="ligra_{}_sym_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_newer_series".format(
                            application_name.lower(),
                            ""
                            if ligra_input_selection == "regular_input"
                            else ligra_input_selection + "_",
                            localdram_size_str,
                            net_lat,
                            bw_scalefactor,
                            remote_init,
                            int(10**5),
                        ),
                        command_str=command_str,
                        experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
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
                command_str = ligra_base_str_options_nonsym.format(
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
                        experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_pq_newer_series".format(
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
                    command_str = ligra_base_str_options_nonsym.format(
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
                            experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode2_threshold_{}_pq_newer_series".format(
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
                        command_str = ligra_base_str_options_nonsym.format(
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
                                experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_pq_newer_series".format(
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
                        command_str = ligra_base_str_options_nonsym.format(
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
                                experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_pq_newer_series".format(
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


    # Some other darknet models, 4 MB 
    darknet_others_pq_cacheline_combined_experiments_remoteinit_true_rmode1 = []
    net_lat = 120
    for model_type in ["darknet19", "resnet50", "vgg-16"]:
        for remote_init in ["true"]:  # "false"
            for num_MB in [4]:
                for bw_scalefactor in [32]: # 32
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

                    darknet_others_pq_cacheline_combined_experiments_remoteinit_true_rmode1.append(
                        Experiment(
                            experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_pq_newer_series".format(
                                model_type.lower().replace("-", ""),
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
    darknet_others_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling = []
    net_lat = 120
    for model_type in ["darknet19", "resnet50", "vgg-16"]:
        for remote_init in ["true"]:  # "false"
            for num_MB in [4]:
                for bw_scalefactor in [8, 32]:
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

                    darknet_others_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling.append(
                        Experiment(
                            experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_newer_series".format(
                                model_type.lower().replace("-", ""),
                                localdram_size_str,
                                net_lat,
                                bw_scalefactor,
                                remote_init,
                                int(10**5),
                            ),
                            command_str=command_str,
                            experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                            output_root_directory=".",
                        )
                    )

    # Darknet tiny, 2 MB
    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1_limit_redundant_moves = []
    net_lat = 120
    for model_type in ["tiny"]:
        for remote_init in ["true"]:  # "false"
            for redundant_moves_limit in [2, 5, 10, 40]:
                for num_MB in [2]:
                    for bw_scalefactor in [4, 8, 32]:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = darknet_base_str_options.format(
                            model_type,
                            sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/remote_limit_redundant_moves={} -s stop-by-icount:{}".format(
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                int(bw_scalefactor),
                                str(remote_init),
                                int(redundant_moves_limit),
                                int(1 * ONE_BILLION),
                            ),
                        )
                        # 1 billion instructions cap

                        darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1_limit_redundant_moves.append(
                            Experiment(
                                experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_limredundantmoves_{}_pq_newer_series".format(
                                    model_type.lower(),
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    remote_init,
                                    redundant_moves_limit,
                                ),
                                command_str=command_str,
                                experiment_run_configs=pq_cacheline_combined_rmode1_configs,
                                output_root_directory=".",
                            )
                        )
    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1_limit_redundant_moves_ideal_throttling = []
    net_lat = 120
    for model_type in ["tiny"]:
        for remote_init in ["true"]:  # "false"
            for redundant_moves_limit in [2, 5, 10, 40]:
                for num_MB in [2]:
                    for bw_scalefactor in [4, 8, 32]:
                        localdram_size_str = "{}MB".format(num_MB)
                        command_str = darknet_base_str_options.format(
                            model_type,
                            sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/remote_limit_redundant_moves={} -s stop-by-icount:{}".format(
                                int(num_MB * ONE_MB_TO_BYTES),
                                int(net_lat),
                                int(bw_scalefactor),
                                str(remote_init),
                                int(redundant_moves_limit),
                                int(1 * ONE_BILLION),
                            ),
                        )
                        # 1 billion instructions cap

                        darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1_limit_redundant_moves_ideal_throttling.append(
                            Experiment(
                                experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_limredundantmoves_{}_idealwinsize_100000_pq_newer_series".format(
                                    model_type.lower(),
                                    localdram_size_str,
                                    net_lat,
                                    bw_scalefactor,
                                    remote_init,
                                    redundant_moves_limit,
                                ),
                                command_str=command_str,
                                experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                                output_root_directory=".",
                            )
                        )

    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1 = []
    net_lat = 120
    for model_type in ["tiny"]:
        for remote_init in ["true"]:  # "false"
            for num_MB in [2]:
                for bw_scalefactor in [4]:
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
                            experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_pq_newer_series".format(
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
    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling = []
    net_lat = 120
    for model_type in ["tiny"]:
        for remote_init in ["true"]:  # "false"
            for num_MB in [2]:
                for bw_scalefactor in [4]:
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

                    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling.append(
                        Experiment(
                            experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_newer_series".format(
                                model_type.lower(),
                                localdram_size_str,
                                net_lat,
                                bw_scalefactor,
                                remote_init,
                                int(10**5),
                            ),
                            command_str=command_str,
                            experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                            output_root_directory=".",
                        )
                    )

    darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode2_thresholds = []
    net_lat = 120
    for model_type in ["tiny"]:
        for remote_init in ["true"]:
            for datamov_threshold in [2, 5]:
                for num_MB in [2]:
                    for bw_scalefactor in [4, 8, 32]:
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
                                experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode2_threshold_{}_pq_newer_series".format(
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
            for mode_switch_threshold in ["0.7", "0.8", "0.9"]:
                for datamov_threshold in [2, 5]:
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
                                    experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_pq_newer_series".format(
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
                                    experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode5_threshold_{}_{}_pq_newer_series".format(
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


    # Stream benchmark
    stream_modes_pq_cacheline_combined_experiments_remoteinit_true_rmode1 = []
    net_lat = 120
    remote_init = "true"
    for bw_scalefactor in [16]:  # 4, 16
        for num_MB in [4]:  # other size??
            for mode in [1, 3]:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = stream_base_options.format(
                    mode,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                    ),
                )

                stream_modes_pq_cacheline_combined_experiments_remoteinit_true_rmode1.append(
                    Experiment(
                        experiment_name="stream_mode{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_pq_cacheline_newer_series".format(
                            mode,
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
    stream_modes_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling = []
    net_lat = 120
    remote_init = "true"
    for bw_scalefactor in [16]:  # 4, 16
        for num_MB in [4]:  # other size??
            for mode in [1, 3]:
                localdram_size_str = "{}MB".format(num_MB)
                command_str = stream_base_options.format(
                    mode,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={}".format(
                        int(num_MB * ONE_MB_TO_BYTES),
                        int(net_lat),
                        int(bw_scalefactor),
                        str(remote_init),
                    ),
                )

                stream_modes_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling.append(
                    Experiment(
                        experiment_name="stream_mode{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_cacheline_newer_series".format(
                            mode,
                            localdram_size_str,
                            net_lat,
                            bw_scalefactor,
                            remote_init,
                            int(10**5),
                        ),
                        command_str=command_str,
                        experiment_run_configs=pq_cacheline_combined_rmode1_configs_ideal_page_throttling,
                        output_root_directory=".",
                    )
                )


    """
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
            command_str = ligra_base_str_options_nonsym.format(
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
                        experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_pq_newer_series".format(
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
            command_str = ligra_base_str_options_nonsym.format(
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
                            experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_newer_series".format(
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
                                    experiment_name="darknet_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode2_threshold_{}_idealwinsize_{}_pq_newer_series".format(
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
                        experiment_name="bcsstk32_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_newer_series".format(
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
                                experiment_name="bcsstk32_localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode2_threshold_{}_idealwinsize_{}_pq_newer_series".format(
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
                command_str = ligra_base_str_options_nonsym.format(
                    application_name,
                    ligra_input_file,
                    sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -g perf_model/dram/m_r_ideal_pagethrottle_remote_access_history_window_size={}".format(
                        int(num_MB * ONE_MB_TO_BYTES), int(net_lat), int(bw_scalefactor), str(remote_init), int(window_size)
                    ),
                )

                bfs_pq_cacheline_combined_experiments_remoteinit_true_ideal_pagethrottling_window_size.append(
                    Experiment(
                        experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_idealwinsize_{}_pq_newer_series".format(
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
                        command_str = ligra_base_str_options_nonsym.format(
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
                                experiment_name="ligra_{}_{}localdram_{}_netlat_{}_bw_scalefactor_{}_remoteinit_{}_rmode2_threshold_{}_idealwinsize_{}_pq_newer_series".format(
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
    """

    # experiments.extend(bcsstk32_bw_verification_experiments_99)
    # experiments.extend(bfs_bw_verification_experiments_99)
    # experiments.extend(darknet_tiny_2MB_bw_verification_experiments_99)
    # experiments.extend(bcsstk32_bw_verification_experiments_95)
    # experiments.extend(bfs_bw_verification_experiments_95)


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


    # experiments.extend(darknet_others_pq_cacheline_combined_experiments_remoteinit_true_rmode1)
    # experiments.extend(darknet_others_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling)
    # experiments.extend(spmv_roadnet_pq_cacheline_combined_experiments_remoteinit_true_rmode1)
    # experiments.extend(spmv_roadnet_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling)
    # experiments.extend(sssp_roadNetPA_pq_cacheline_combined_experiments_remoteinit_true_rmode1)
    # experiments.extend(sssp_roadNetPA_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling)

    # experiments.extend(ligra_sym_pq_cacheline_combined_experiments_remoteinit_true_rmode1_test)
    # experiments.extend(ligra_pq_cacheline_combined_experiments_remoteinit_true_rmode1_test[0:3])


    # experiments.extend(spmv_roadnetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode1)
    # experiments.extend(spmv_roadnetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling)
    # experiments.extend(spmv_roadnetCA_roadnetPA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds)
    # experiments.extend(spmv_roadnetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds_ideal_page_throttling)

    # experiments.extend(sssp_roadNetPA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds)
    # experiments.extend(sssp_roadNetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds)
    # experiments.extend(sssp_roadNetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode1)
    # experiments.extend(sssp_roadNetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling)
    # experiments.extend(sssp_roadNetCA_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds_ideal_page_throttling)

    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1_limit_redundant_moves)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode1_limit_redundant_moves_ideal_throttling)
    # experiments.extend(darknet_tiny_pq_cacheline_combined_experiments_remoteinit_true_rmode5_thresholds)

    # experiments.extend(stream_modes_pq_cacheline_combined_experiments_remoteinit_true_rmode1)
    # experiments.extend(stream_modes_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_page_throttling)

    # experiments.extend(ligra_sym_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal)
    # experiments.extend(ligra_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal)
    # experiments.extend(ligra_pq_cacheline_combined_experiments_remoteinit_true_rmode1_ideal_pagerank)

    # experiments.extend(spmv_new_pq_cacheline_combined_experiments_remoteinit_true_rmode1_test)
    # experiments.extend(sssp_new_pq_cacheline_combined_experiments_remoteinit_true_rmode1_test)

    ### Run Sniper experiments using ExperimentManager ###
    # Find log filename, to not overwrite previous logs
    timezone = pytz.timezone("Canada/Eastern")
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
            output_root_directory=".", max_concurrent_processes=36, log_file=log_file
        )
        experiment_manager.add_experiments(experiments)
        compiled_application_checker(experiments)
        input_file_checker(experiments)
        experiment_manager.start(
            manager_sleep_interval_seconds=60,
            timezone=timezone,
        )  # main thread sleep for 60 second intervals while waiting

        log_str = "Script end time: {}".format(datetime.datetime.now().astimezone(timezone))
        print(log_str)
        print(log_str, file=log_file)
