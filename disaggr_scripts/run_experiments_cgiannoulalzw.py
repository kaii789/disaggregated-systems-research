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

    nw_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/rodinia/bin/needle {{0}} 1 1".format(
        sniper_root=subfolder_sniper_root_relpath
    )

    ###  Darknet command strings  ###
    # Note: using os.system(), the 'cd' of working directory doesn't persist to the next call to os.system()
    darknet_base_options = "cd {1} && ../../run-sniper -d {{{{sniper_output_dir}}}} -c ../../disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/darknet classifier predict {0}/cfg/imagenet1k.data {0}/cfg/{{0}}.cfg {0}/{{0}}.weights {0}/data/dog.jpg && cd - ".format(
        ".", darknet_home
    )

    timeseries_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/timeseries/src/scrimp {sniper_root}/benchmarks/timeseries/inputs/{{0}} 50 0.25 1 4".format(
        sniper_root=subfolder_sniper_root_relpath
    )

    hpcg_base_options = "cp {sniper_root}/benchmarks/hpcg/linux_serial/bin/hpcg.dat .;{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/hpcg/linux_serial/bin/xhpcg".format(
    sniper_root=subfolder_sniper_root_relpath
    )
    
    sls_base_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg {{sniper_options}} -- {sniper_root}/benchmarks/sls/bin/sls -f /home/shared/sls.in".format(
    sniper_root=subfolder_sniper_root_relpath
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
        # 11) Remote on, PQ = 0, compression = 'bdi' 
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "bdi"),
                ConfigEntry("perf_model/dram/compression_model/bdi", "compression_granularity", "-1"),
                ConfigEntry("perf_model/dram/compression_model/bdi", "use_additional_options", "false"),
            ]
        ),

         # 11) Remote on, PQ = 0, compression = 'fpc' 
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "fpc"),
                ConfigEntry("perf_model/dram/compression_model/bdi", "compression_granularity", "-1"),
                ConfigEntry("perf_model/dram/compression_model/bdi", "use_additional_options", "false"),
            ]
        ),


        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "false"),
            ]
        ),

        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "256"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "4"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "256"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "16"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "256"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "32"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),


 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "256"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "64"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "256"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "96"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),


        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "512"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "4"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "512"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "16"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "512"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "32"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),


 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "512"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "64"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "512"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "96"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),




        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "768"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "4"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "768"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "16"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "768"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "32"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),


 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "768"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "64"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "768"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "96"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),




        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "1024"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "4"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "1024"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "16"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "1024"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "32"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),


 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "1024"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "64"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "1024"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "96"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),



        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "1280"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "4"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "1280"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "16"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "1280"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "32"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),


 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "1280"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "64"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),

 
        # 17) Remote on, PQ = 0, compression = 'lz78', compression_latency = 0
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "0"),
                ConfigEntry("perf_model/dram/compression_model/cacheline", "use_cacheline_compression", "false"),
                ConfigEntry("perf_model/dram/compression_model", "use_compression", "true"),
                ConfigEntry("perf_model/dram/compression_model", "compression_scheme", "lz78"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "compression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "decompression_latency", "0"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "word_size" , "1"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "dictionary_size" , "1280"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "entry_size" , "96"),
                ConfigEntry("perf_model/dram/compression_model/lz78", "size_limit" , "true"),
            ]
        ),










    ]


    #################################

    experiments = []

    # SSSP roadNet, bw_factor [4, 16] 
    sssp_roadNet_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [8]:
            command_str = sssp_int_base_options.format(
                "roadNet-CA.mtx",
                sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            sssp_roadNet_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="sssp_roadNetCA_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
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
        for bw_scalefactor in [8]:
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

    # rodinia-nw needle 6144, bw_factor [4, 16] 
    nw_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [8]:
            command_str = nw_base_options.format(
                "2048",
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(16777216),
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            nw_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="nw_6144_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
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
    for model_type in ["darknet19", "resnet50", "vgg-16", "yolov3"]:
        for remote_init in ["true"]:  # "false"
            for bw_scalefactor in [8]:
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
        for bw_scalefactor in [8]:
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
        for bw_scalefactor in [8]:
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
        for bw_scalefactor in [8]:
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
        for bw_scalefactor in [8]:
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
                    output_root_directory=".",
                )
            )


    # Components rMat_1000000, bw_factor [4, 16] 
    components_rmat1M_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [8]:
            command_str = ligra_base_options.format(
                "Components",
                "rMat_1000000",
                sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            components_rmat1M_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="components_rmat1M_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
                        bw_scalefactor,
                        remote_init,
                    ),
                    command_str=command_str,
                    experiment_run_configs=compression_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )


    # Radii rMat_1000000, bw_factor [4, 16] 
    radii_rmat1M_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [8]:
            command_str = ligra_base_options.format(
                "Radii",
                "rMat_1000000",
                sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            radii_rmat1M_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="radii_rmat1M_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
                        bw_scalefactor,
                        remote_init,
                    ),
                    command_str=command_str,
                    experiment_run_configs=compression_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )


    # timeseries bw_factor [4, 16] 
    timeseries_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [8]:
            command_str = timeseries_base_options.format(
                "e0103.txt",
                sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            timeseries_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="timeseries_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
                        bw_scalefactor,
                        remote_init,
                    ),
                    command_str=command_str,
                    experiment_run_configs=compression_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )

    # sls bw_factor [4, 16] 
    sls_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [8]:
            command_str = sls_base_options.format(
                sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            sls_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="sls_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
                        bw_scalefactor,
                        remote_init,
                    ),
                    command_str=command_str,
                    experiment_run_configs=compression_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )


    # hpcg bw_factor [4, 16] 
    hpcg_compression_experiments_remoteinit_true = []
    for remote_init in ["true"]:  # "false"
        for bw_scalefactor in [8]:
            command_str = hpcg_base_options.format(
                sniper_options="-g perf_model/dram/remote_mem_bw_scalefactor={} -g perf_model/dram/remote_init={} -s stop-by-icount:{}".format(
                    int(bw_scalefactor),
                    str(remote_init),
                    int(1 * ONE_BILLION),
                ),
            )

            hpcg_compression_experiments_remoteinit_true.append(
                Experiment(
                    experiment_name="hpcg_bw_scalefactor_{}_remoteinit_{}_compression_series".format(
                        bw_scalefactor,
                        remote_init,
                    ),
                    command_str=command_str,
                    experiment_run_configs=compression_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )







    ## add configs to experiment list
    experiments.extend(spmv_pkustk14_compression_experiments_remoteinit_true)
    experiments.extend(sssp_roadNet_compression_experiments_remoteinit_true)
    experiments.extend(darknet_compression_experiments_remoteinit_true)
    experiments.extend(stream_triad_compression_experiments_remoteinit_true)
    experiments.extend(bfs_rmat1M_compression_experiments_remoteinit_true)
    experiments.extend(triangle_rmat1M_compression_experiments_remoteinit_true)
    experiments.extend(components_rmat1M_compression_experiments_remoteinit_true)
    experiments.extend(radii_rmat1M_compression_experiments_remoteinit_true)
    experiments.extend(pagerank_rmat1M_compression_experiments_remoteinit_true)
    experiments.extend(timeseries_compression_experiments_remoteinit_true)
    experiments.extend(hpcg_compression_experiments_remoteinit_true)
    experiments.extend(nw_compression_experiments_remoteinit_true)
    experiments.extend(sls_compression_experiments_remoteinit_true)


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
