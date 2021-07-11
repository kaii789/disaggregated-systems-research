# Python 3
from run_sniper_repeat_base import *

if __name__ == "__main__":
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


    # Assumes input matrices are in the {sniper_root}/benchmarks/crono/inputs directory
    sssp_int_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/crono/apps/sssp/sssp_int {sniper_root}/benchmarks/crono/inputs/{{0}} 1".format(
        sniper_root=subfolder_sniper_root_relpath
    )

    stream_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/stream/stream_sniper {{0}}".format(
        sniper_root=subfolder_sniper_root_relpath
    )

    spmv_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/spmv/bench_spdmv {sniper_root}/benchmarks/crono/inputs/{{0}} 1 1".format(
        sniper_root=subfolder_sniper_root_relpath
    )

    ###  Darknet command strings  ###
    # Note: using os.system(), the 'cd' of working directory doesn't persist to the next call to os.system()
    darknet_base_options = "cd {1} && ../../run-sniper -d {{{{sniper_output_dir}}}} -c ../../disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/darknet classifier predict {0}/cfg/imagenet1k.data {0}/cfg/{{0}}.cfg {0}/{{0}}.weights {0}/data/dog.jpg".format(
        ".", darknet_home
    )

    ###  Ligra command strings  ###
    # Do only 1 timed round to save time during initial experiments
    ligra_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/apps/{{0}} -s -rounds 1 {0}/inputs/{{1}}".format(
        ligra_home, sniper_root=subfolder_sniper_root_relpath
    )
    ligra_input_to_file = {
        "regular_input": "rMat_1000000",
        "small_input": "rMat_100000",
        "reg_10x": "rMat_10000000",
        "reg_8x": "rMat_8000000",
    }

    compression_series_experiment_run_configs = [
        # 1) Remote off
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "false"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
            ]
        ),

        # 2) Remote on, simulate page movement time with both bandwidth and network latency, PQ = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
            ]
        ),

        # 3) Remote on, PQ = 1, cache_line_fraction = 0.15
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
                ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.15"),
            ]
        ),

        # 4) Remote on, PQ = 1, cache_line_fraction = 0.5
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
                ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.5"),
            ]
        ),

        # 5) Remote on, PQ = 0, compression = 'ideal', compression_latency = 0, compressed_page_size = 2048
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "ideal"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "compressed_page_size", "2048"),
            ]
        ),

        # 6) Remote on, PQ = 1, cache_line_fraction = 0.15, compression = 'ideal', compression_latency = 0, compressed_page_size = 2048
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
                ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.15"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "ideal"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "compressed_page_size", "2048"),
            ]
        ),

        # 7) Remote on, PQ = 1, cache_line_fraction = 0.15, cache_line_compression = 'bdi', compression = 'ideal', compression_latency = 0, compressed_page_size = 2048
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
                ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.15"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "compression_scheme", "bdi"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "ideal"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "compressed_page_size", "2048"),
            ]
        ),

 
        # 8) Remote on, PQ = 0, compression = 'ideal', compression_latency = 30, compressed_page_size = 2048
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "ideal"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "compression_latency", "30"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "decompression_latency", "30"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "compressed_page_size", "2048"),
            ]
        ),

        # 9) Remote on, PQ = 1, cache_line_fraction = 0.15, compression = 'ideal', compression_latency = 30, compressed_page_size = 2048
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
                ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.15"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "ideal"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "compression_latency", "30"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "decompression_latency", "30"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "compressed_page_size", "2048"),
            ]
        ),

        # 10) Remote on, PQ = 1, cache_line_fraction = 0.15, cache_line_compression = 'bdi', compression = 'ideal', compression_latency = 30, compressed_page_size = 2048
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
                ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.15"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "compression_scheme", "bdi"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "ideal"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "compression_latency", "30"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "decompression_latency", "30"),
                ConfigEntry("perf_model/dram/compression_model/ideal", "compressed_page_size", "2048"),
            ]
        ),

         # 11) Remote on, PQ = 0, compression = 'bdi' 
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "bdi"),
                ConfigEntry("perf_model/dram/compression_model/bdi", "compression_granularity", "-1"),
            ]
        ),

        # 12) Remote on, PQ = 1, cache_line_fraction = 0.15, compression = 'bdi'
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
                ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.15"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "bdi"),
                ConfigEntry("perf_model/dram/compression_model/bdi", "compression_granularity", "-1"),
            ]
        ),

        # 13) Remote on, PQ = 1, cache_line_fraction = 0.15, cache_line_compression = 'bdi', compression = 'bdi'
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
                ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.15"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "compression_scheme", "bdi"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "bdi"),
                ConfigEntry("perf_model/dram/compression_model/bdi", "compression_granularity", "-1"),
            ]
        ),

         # 14) Remote on, PQ = 0, compression = 'lz4', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz4"),
                ConfigEntry("perf_model/dram/compression_model/lz4", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz4", "decompression_latency", "0"),
            ]
        ),

        # 15) Remote on, PQ = 1, cache_line_fraction = 0.15, compression = 'lz4', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
                ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.15"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz4"),
                ConfigEntry("perf_model/dram/compression_model/lz4", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz4", "decompression_latency", "0"),
            ]
        ),

        # 16) Remote on, PQ = 1, cache_line_fraction = 0.15, cache_line_compression = 'bdi', compression = 'lz4'
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
                ConfigEntry("perf_model/dram", "remote_cacheline_queue_fraction", "0.15"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "compression_scheme", "bdi"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz4"),
                ConfigEntry("perf_model/dram/compression_model/lz4", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz4", "decompression_latency", "0"),
            ]
        ),

 


    ]


    #################################

    experiments = []

    # SSSP roadNet, bw_factor [4, 16] 
    sssp_roadNet_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [4, 16]:
            command_str = sssp_int_base_options.format(
                "roadNet-PA.mtx",
                sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            sssp_roadNet_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="sssp_roadNet_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
                        bw_scalefactor,
                        remote_init,
                    ),
                    command_str=command_str,
                    experiment_run_configs=compression_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )

    # stream triad, bw_factor [4, 16] 
    stream_triad_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [4, 16]:
            command_str = stream_base_options.format(
                "3",
                sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            stream_triad_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="stream_triad_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
                        bw_scalefactor,
                        remote_init,
                    ),
                    command_str=command_str,
                    experiment_run_configs=compression_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )

    # darknet bw_factor [4, 16] 
    darknet_compression_experiments_remoteinit_true = []
    for model_type in ["tiny"]:
        for remote_init in ["true"]:  # "false"
            for bw_scalefactor in [4, 16]:
                command_str = darknet_base_options.format(
                    model_type,
                    sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                        int(bw_scalefactor),
                        str(remote_init),
                        int(1 * ONE_BILLION),
                    ),
                )

                darknet_compression_experiments_remoteinit_true.append(
                    Experiment(
                        experiment_name="darknet_{}_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
                            model_type.lower(),
                            bw_scalefactor,
                            remote_init,
                        ),
                        command_str=command_str,
                        experiment_run_configs=compression_series_experiment_run_configs,
                        output_root_directory=".",
                    )
                )

    # spmv pkustk14.mtx, bw_factor [4, 16] 
    spmv_pkustk14_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [4, 16]:
            command_str = spmv_base_options.format(
                "pkustk14.mtx",
                sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            spmv_pkustk14_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="spmv_pkustk14_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
                        bw_scalefactor,
                        remote_init,
                    ),
                    command_str=command_str,
                    experiment_run_configs=compression_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )

    # BFS rMat_1000000, bw_factor [4, 16] 
    bfs_rmat1M_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [4, 16]:
            command_str = ligra_base_options.format(
                "BFS",
                "rMat_1000000",
                sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            bfs_rmat1M_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="bfs_rmat1M_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
                        bw_scalefactor,
                        remote_init,
                    ),
                    command_str=command_str,
                    experiment_run_configs=compression_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )


    # PageRank rMat_1000000, bw_factor [4, 16] 
    pagerank_rmat1M_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [4, 16]:
            command_str = ligra_base_options.format(
                "PageRank",
                "rMat_1000000",
                sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            pagerank_rmat1M_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="pagerank_rmat1M_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
                        bw_scalefactor,
                        remote_init,
                    ),
                    command_str=command_str,
                    experiment_run_configs=compression_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )


    # TriangleCounting rMat_1000000, bw_factor [4, 16] 
    triangle_rmat1M_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [4, 16]:
            command_str = ligra_base_options.format(
                "Triangle",
                "rMat_1000000",
                sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            triangle_rmat1M_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="triangle_rmat1M_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
                        bw_scalefactor,
                        remote_init,
                    ),
                    command_str=command_str,
                    experiment_run_configs=compression_series_experiment_run_configs,


    ## add configs to experiment list
    #experiments.extend(sssp_roadNet_compression_experiments_remoteinit_true)


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
