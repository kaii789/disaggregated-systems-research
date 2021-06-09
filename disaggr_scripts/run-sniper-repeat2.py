# Python 3
import sys
import os
import time
import traceback
import datetime
import getopt
import subprocess

from typing import List, Iterable, Union, TypeVar

import plot_graph

PathLike = TypeVar("PathLike", str, bytes, os.PathLike)  # Type for file/directory paths

this_file_containing_dir_abspath = os.path.dirname(os.path.abspath(__file__))

# If scripts in the Sniper tools folder need to be called
sys.path.append(os.path.join(this_file_containing_dir_abspath, "..", "tools"))

# Add root Sniper directory to path
sys.path.insert(0, os.path.join(this_file_containing_dir_abspath, ".."))
# print(sys.path)


class ConfigEntry:
    def __init__(self, category: str, name: str, value: str) -> None:
        """category should NOT include the square brackets.

        Example: Config("perf_model/dram", "remote_mem_add_lat", 5)"""
        self.category = category
        self.name = name
        self.value = value

        # Make sure category doesn't include the starting/ending square brackets:
        if category[0] == "[" and category[-1] == "]":
            self.category = category[1:-1]  # Strip enclosing square brackets


class ExperimentRunConfig:
    def __init__(self, config_entries: Iterable[ConfigEntry]) -> None:
        self.config_tree = {}
        self.add_config_entries(config_entries)

    def add_config_entry(self, config_entry: ConfigEntry):
        if config_entry.category not in self.config_tree:
            self.config_tree[config_entry.category] = {}
        if config_entry.name in self.config_tree[config_entry.category]:
            raise ValueError(
                "Attempted to add duplicate config entry: attempted to assign config {}/{} with value {} when it already had value {}".format(
                    config_entry.category,
                    config_entry.name,
                    config_entry.value,
                    self.config_tree[config_entry.category][config_entry.name],
                )
            )
        self.config_tree[config_entry.category][config_entry.name] = config_entry.value

    def add_config_entries(self, config_entries: Iterable[ConfigEntry]) -> None:
        for config_entry in config_entries:
            self.add_config_entry(config_entry)

    def generate_config_file_str(self) -> str:
        """Write this string to a file to generate a config file from this
        ConfigEntryCollection's ConfigEntry entries.
        """
        lines = []
        for category, name_value_dict in self.config_tree.items():
            lines.append("[{}]".format(category))
            lines.extend(
                [
                    "{} = {}".format(name, value)
                    for name, value in name_value_dict.items()
                ]
            )
            lines.append("")
        return "\n".join(lines)


class Experiment:
    def __init__(
        self,
        experiment_name: str,
        command_str: str,
        experiment_run_configs: Iterable[ExperimentRunConfig],
        output_directory: PathLike,
        setup_command_str=None,
        clean_up_command_str=None,
    ):
        self.experiment_name = experiment_name
        self.command_str = command_str
        self.experiment_run_configs = experiment_run_configs
        self.output_directory = output_directory
        self.setup_command_str = setup_command_str
        self.clean_up_command_str = clean_up_command_str

    def run_and_graph(self):
        experiment_output_directory = self.run_experiment(
            self.experiment_name,
            self.command_str,
            self.experiment_run_configs,
            self.output_directory,
            self.setup_command_str,
            self.clean_up_command_str,
        )

        # These experiments will use custom graph plotting functions
        # plot_graph.run_from_experiment(
        #     experiment_output_directory,
        #     self.config_param_category,
        #     self.config_param_name,
        #     self.config_param_values,
        # )

    def run_experiment(
        self,
        experiment_name: str,
        command_str: str,
        experiment_run_configs: Iterable[ExperimentRunConfig],
        output_root_directory: PathLike,
        setup_command_str=None,
        clean_up_command_str=None,
    ) -> PathLike:
        # Find a directory name that doesn't already exist
        experiment_output_directory_name = experiment_name + "_output_files"
        experiment_output_directory = os.path.join(
            output_root_directory, experiment_output_directory_name
        )
        num = 2
        while os.path.exists(experiment_output_directory):
            experiment_output_directory_name = (
                experiment_name + "_output_files_" + str(num)
            )
            experiment_output_directory = os.path.join(
                output_root_directory, experiment_output_directory_name
            )
            num += 1
        os.makedirs(experiment_output_directory)

        start_time = time.time()
        for experiment_no, config_collection in enumerate(experiment_run_configs):
            # Update config file
            with open(
                os.path.join(this_file_containing_dir_abspath, "repeat_testing.cfg"),
                "w",
            ) as variating_config_file:
                # variating_config_file.truncate(0)  # start writing from the beginning of the file;
                # not needed since open with "w" automatically does this
                variating_config_file.write(
                    config_collection.generate_config_file_str()
                )

            # Run the program
            error_occurred = False
            command_strs = [command_str]
            if setup_command_str:
                command_strs.insert(0, setup_command_str)
            if clean_up_command_str:
                command_strs.append(clean_up_command_str)
            for command_str in command_strs:
                print("Running linux command:\n{}".format(command_str))
                wait_status = os.system(command_str)  # Behaviour on Linux
                if os.WIFSIGNALED(wait_status) and os.WTERMSIG(wait_status) == 2:
                    # Keyboard Interrupt, stop execution of entire program
                    sys.exit(-1)
                elif os.WIFEXITED(wait_status) and os.WEXITSTATUS(wait_status) != 0:
                    error_occurred = True
                    print(
                        "Run-sniper-repeat command '{}' for experiment run {} got error ret val:\n[[{}]]".format(
                            command_str,
                            experiment_no + 1,
                            os.WEXITSTATUS(wait_status),
                        )
                    )
                    break
            if error_occurred:
                continue  # skip to the next run of the experiment

            # Save a copy of the output for later reference
            files_to_save = ["sim.cfg", "sim.out", "sim.stats.sqlite3"]
            for filename in files_to_save:
                os.system(
                    'cp "{0}" "{1}"/"{2}_{0}"'.format(
                        filename, experiment_output_directory, experiment_no + 1
                    )
                )

            print(
                "Experiment {} run {} done.".format(experiment_name, experiment_no + 1)
            )

        end_time = time.time()
        print(
            "\nRan {} experiment runs in {:.2f} seconds.".format(
                len(experiment_run_configs), end_time - start_time
            )
        )
        print(
            "Average: {:.2f} seconds/experiment run.".format(
                (end_time - start_time) / len(experiment_run_configs)
            )
        )
        return experiment_output_directory


# def execute():
#   global cmd, usage

#   cmd = command_str.split()

#   sys.stdout.flush()
#   sys.stderr.flush()

#   subproc = subprocess.Popen(cmd, env = env)

#   try:
#     try:
#       pid, rc, usage = os.wait4(subproc.pid, 0)
#     except AttributeError:
#       pid, rc = os.waitpid(subproc.pid, 0)
#   except KeyboardInterrupt:
#     try:
#       os.kill(subproc.pid, 9)
#     except OSError:
#       # Already dead, never mind
#       pass
#     return 9

#   rc >>= 8
#   return rc


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
    # Assumes the program is compiled
    command_str1a = "../run-sniper -n 1 -c ../disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg --roi -- ../test/a_disagg_test/mem_test"
    command_str1b = "../run-sniper -n 1 -c ../disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg --roi -- ./test/a_disagg_test/mem_test_varied"
    command_str2a = "../run-sniper -c ../disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg -- ../test/crono/apps/sssp/sssp ../test/crono/inputs/bcsstk05.mtx 1"
    command_str2b = "../run-sniper -c ../disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg -- ../test/crono/apps/sssp/sssp ../test/crono/inputs/bcsstk25.mtx 1"

    darknet_home = "../benchmarks/darknet"  # relative to disaggr_scripts directory
    ligra_home = "../benchmarks/ligra"  # relative to disaggr_scripts directory

    command_strs = {}
    ONE_MILLION = 1000000  # eg to specify how many instructions to run
    ONE_MB_TO_BYTES = 1024 * 1024  # eg to specify localdram_size

    ###  Darknet command strings  ###
    # Note: using os.system(), the 'cd' of working directory doesn't persist to the next call to os.system()
    darknet_base_str_options = "cd {1} && ../../run-sniper -d {2} -c ../../disaggr_config/local_memory_cache.cfg -c {2}/repeat_testing.cfg {{1}} -- {0}/darknet classifier predict {0}/cfg/imagenet1k.data {0}/cfg/{{0}}.cfg {0}/{{0}}.weights {0}/data/dog.jpg".format(
        ".", darknet_home, this_file_containing_dir_abspath
    )
    command_strs["darknet_tiny"] = darknet_base_str_options.format("tiny", "")
    command_strs["darknet_darknet19"] = darknet_base_str_options.format("darknet19", "")
    command_strs["darknet_vgg-16"] = darknet_base_str_options.format("vgg-16", "")
    command_strs["darknet_resnet50"] = darknet_base_str_options.format("resnet50", "")
    # cd ../benchmarks/darknet && ../../run-sniper -c ../../disaggr_config/local_memory_cache.cfg -- ./darknet classifier predict ./cfg/imagenet1k.data ./cfg/tiny.cfg ./tiny.weights ./data/dog.jpg

    ###  Ligra command strings  ###
    # Do only 1 timed round to save time during initial experiments
    ligra_base_str_options = "../run-sniper -d {1} -c ../disaggr_config/local_memory_cache.cfg -c {1}/repeat_testing.cfg {{2}} -- {0}/apps/{{0}} -s -rounds 1 {0}/inputs/{{1}}".format(
        ligra_home, this_file_containing_dir_abspath
    )
    ligra_input_to_file = {
        "regular_input": "rMat_1000000",
        "small_input": "rMat_100000",
    }
    command_strs["ligra_bfs"] = ligra_base_str_options.format(
        "BFS", ligra_input_to_file["regular_input"], ""
    )
    command_strs["ligra_pagerank"] = ligra_base_str_options.format(
        "PageRank", ligra_input_to_file["regular_input"], ""
    )

    # Small input: first run some tests with smaller input size
    command_strs["ligra_bfs_small_input"] = ligra_base_str_options.format(
        "BFS", ligra_input_to_file["small_input"], ""
    )
    command_strs["ligra_pagerank_small_input"] = ligra_base_str_options.format(
        "PageRank", ligra_input_to_file["small_input"], ""
    )
    # ../run-sniper -c ../disaggr_config/local_memory_cache.cfg -- ../benchmarks/ligra/apps/BFS -s ../benchmarks/ligra/inputs/rMat_1000000

    # Stop around 100 Million instructions after entering ROI (magic = true in config so don't need --roi flag)
    command_strs["ligra_bfs_instrs_100mil"] = ligra_base_str_options.format(
        "BFS",
        ligra_input_to_file["regular_input"],
        "-s stop-by-icount:{}".format(100 * ONE_MILLION),
    )

    # 16 MB for ligra_bfs + rMat_1000000
    command_strs["ligra_bfs_localdram_16MB"] = ligra_base_str_options.format(
        "BFS",
        ligra_input_to_file["regular_input"],
        "-g perf_model/dram/localdram_size={}".format(16 * ONE_MB_TO_BYTES),
    )
    # 1 MB for ligra_bfs + rMat_100000
    command_strs["ligra_bfs_small_input_localdram_1MB"] = ligra_base_str_options.format(
        "BFS",
        ligra_input_to_file["small_input"],
        "-g perf_model/dram/localdram_size={}".format(1 * ONE_MB_TO_BYTES),
    )

    experiments = []

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
        # 6) Remote on, simulate page movement time with both bandwidth and network latency, PQ = 1
        ExperimentRunConfig(
            [
                ConfigEntry("perf_model/dram", "enable_remote_mem", "true"),
                ConfigEntry("perf_model/dram", "remote_partitioned_queues", "1"),
            ]
        ),
    ]

    # Remote off, PQ=0 network lat=0, PQ=0, PQ=1
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    for num_MB in [2, 4, 8]:
        localdram_size_str = "{}MB".format(num_MB)
        command_str = ligra_base_str_options.format(
            "BFS",
            ligra_input_file,
            "-g perf_model/dram/localdram_size={}".format(num_MB * ONE_MB_TO_BYTES),
        )

        experiments.append(
            Experiment(
                experiment_name="ligra_bfs_{}localdram_{}_partition_queue_series".format(
                    ""
                    if ligra_input_selection == "regular_input"
                    else ligra_input_selection + "_",
                    localdram_size_str,
                ),
                command_str=command_str,
                experiment_run_configs=partition_queue_series_experiment_run_configs,
                output_directory=".",
            )
        )

        # experiments.append(
        #     Experiment(
        #         experiment_name="testB_localdram_{}_page_size".format(
        #             localdram_size_str
        #         ),
        #         command_str=command_str1a,
        #         experiment_run_configs=generate_one_varying_param_experiment_run_configs(
        #             config_param_category="perf_model/dram",
        #             config_param_name="page_size",
        #             config_param_values=[
        #                 1,
        #                 2,
        #                 1024,
        #                 2048,
        #                 4096,
        #                 8192,
        #                 16384,
        #             ],  # latency is in nanoseconds
        #         ),
        #         output_directory=".",
        #     )
        # )

    command_selection = "darknet_tiny"
    command_selection = "ligra_bfs_small_input"
    # experiments.extend(
    #     [
    #         Experiment(
    #             experiment_name=command_selection + "_remote_additional_latency",
    #             command_str=command_strs[command_selection],
    #             experiment_run_configs=generate_one_varying_param_experiment_run_configs(
    #                 config_param_category="perf_model/dram",
    #                 config_param_name="remote_mem_add_lat",
    #                 config_param_values=[
    #                     0,
    #                     100,
    #                     200,
    #                     500,
    #                     1000,
    #                     2000,
    #                     3000,
    #                     5000,
    #                     10000,
    #                 ],  # latency is in nanoseconds
    #             ),
    #             output_directory=".",
    #         ),
    #         Experiment(
    #             experiment_name=command_selection + "_remote_bw_scalefactor",
    #             command_str=command_strs[command_selection],
    #             experiment_run_configs=generate_one_varying_param_experiment_run_configs(
    #                 config_param_category="perf_model/dram",
    #                 config_param_name="remote_mem_bw_scalefactor",
    #                 config_param_values=[1, 2, 4, 8, 16, 32, 64, 128],
    #             ),
    #             output_directory=".",
    #         ),
    #         Experiment(
    #             experiment_name=command_selection + "_localdram_size",
    #             command_str=command_strs[command_selection],
    #             experiment_run_configs=generate_one_varying_param_experiment_run_configs(
    #                 config_param_category="perf_model/dram",
    #                 config_param_name="localdram_size",
    #                 config_param_values=[4096, 16384, 65536, 262144, 524288, 1048576],
    #             ),
    #             output_directory=".",
    #         ),
    #     ]
    # )

    # # Remote memory testing experiments
    # command_str = command_str1a
    # experiments = [
    #     Experiment(
    #         experiment_name="bcsstk05_remote_additional_latency",
    #         command_str=command_str,
    #         experiment_run_configs=generate_one_varying_param_experiment_run_configs(
    #             config_param_category="perf_model/dram",
    #             config_param_name="remote_mem_add_lat",
    #             config_param_values=list(range(0, 100, 20))
    #             + list(range(100, 1000, 100))
    #             + list(range(1000, 10000, 1000))
    #             + [10000],  # latency is in nanoseconds
    #         ),
    #         output_directory=".",
    #     ),
    #     Experiment(
    #         experiment_name="bcsstk05_remote_bw_scalefactor",
    #         command_str=command_str,
    #         experiment_run_configs=generate_one_varying_param_experiment_run_configs(
    #             config_param_category="perf_model/dram",
    #             config_param_name="remote_mem_bw_scalefactor",
    #             config_param_values=[1, 2, 4, 8, 16, 32, 64, 128],
    #         ),
    #         output_directory=".",
    #     ),
    #     Experiment(
    #         experiment_name="bcsstk05_localdram_size",
    #         command_str=command_str,
    #         experiment_run_configs=generate_one_varying_param_experiment_run_configs(
    #             config_param_category="perf_model/dram",
    #             config_param_name="localdram_size",
    #             # config_param_values=[16384, 163840] + list(range(1000000, 7000000, 1000000)) + list(range(7000000, 77000001, 7000000)))
    #             config_param_values=[4096, 16384, 65536, 262144, 524288, 1048576],
    #             # 950000 is approx the working set size for bcsstk05
    #         ),
    #         output_directory=".",
    #     ),
    # ]

    # Find log filename, to not overwrite previous logs
    log_filename = "run-sniper-repeat2_1.log"
    num = 2
    while os.path.isfile(log_filename):
        log_filename = "run-sniper-repeat2_{}.log".format(num)
        num += 1

    with open(log_filename, "w") as log_file:
        log_str = "Script start time: {}".format(datetime.datetime.now().astimezone())
        print(log_str)
        print(log_str, file=log_file)
        for experiment in experiments:
            try:
                # Run experiment
                log_str = "Starting experiment {} at {}".format(
                    experiment.experiment_name, datetime.datetime.now().astimezone()
                )
                print(log_str)
                print(log_str, file=log_file)
                experiment.run_and_graph()
            except Exception as e:
                # Print exception traceback to both stdout and log file
                err_str = "Error occurred while running experiment '{}':".format(
                    experiment.experiment_name
                )
                print(err_str)
                traceback.print_exc()
                print(file=log_file)
                traceback.print_exc(file=log_file)
        log_str = "Script end time: {}".format(datetime.datetime.now().astimezone())
        print(log_str)
        print(log_str, file=log_file)
