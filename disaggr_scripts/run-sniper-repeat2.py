# Python 3
import sys
import os
import time
import traceback
import datetime
import getopt
import subprocess

import plot_graph

this_file_containing_dir_abspath = os.path.dirname(os.path.abspath(__file__))

# If scripts in the Sniper tools folder need to be called
sys.path.append(os.path.join(this_file_containing_dir_abspath, "..", "tools"))

# Add root Sniper directory to path
sys.path.insert(0, os.path.join(this_file_containing_dir_abspath, ".."))
# print(sys.path)


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


def run_experiment(
    experiment_name,
    config_param_category,
    config_param_name,
    config_param_values,
    command_str,
    output_root_directory,
    setup_command_str,
    clean_up_command_str,
):
    """config_param_category shouldn't include the square brackets; config_param_values should be an iterable of values"""

    # Find a directory name that doesn't already exist
    experiment_output_directory_name = experiment_name + "_output_files"
    experiment_output_directory = os.path.join(
        output_root_directory, experiment_output_directory_name
    )
    num = 2
    while os.path.exists(experiment_output_directory):
        experiment_output_directory_name = experiment_name + "_output_files_" + str(num)
        experiment_output_directory = os.path.join(
            output_root_directory, experiment_output_directory_name
        )
        num += 1
    os.makedirs(experiment_output_directory)

    start_time = time.time()
    for experiment_no, config_param_value in enumerate(config_param_values):
        # Update config file
        with open(
            os.path.join(this_file_containing_dir_abspath, "repeat_testing.cfg"), "w"
        ) as variating_config_file:
            # variating_config_file.truncate(0)  # start writing from the beginning of the file
            variating_config_file.write(
                "[{}]\n{} = {}\n".format(
                    config_param_category, config_param_name, config_param_value
                )
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
                    "Run-sniper-repeat command '{}' for config {} got error ret val:\n[[{}]]".format(
                        command_str,
                        "{}/{}={}".format(
                            config_param_category, config_param_name, config_param_value
                        ),
                        os.WEXITSTATUS(wait_status),
                    )
                )
                break
        if error_occurred:
            continue

        # Save a copy of the output for later reference
        files_to_save = ["sim.cfg", "sim.out"]
        for filename in files_to_save:
            os.system(
                "cp {0} {1}/{2}_{0}".format(
                    filename, experiment_output_directory, experiment_no + 1
                )
            )

        print("Experiment {} run {} done.".format(experiment_name, experiment_no + 1))

    end_time = time.time()
    print(
        "\nRan {} experiments in {:.2f} seconds.".format(
            len(config_param_values), end_time - start_time
        )
    )
    print(
        "Average: {:.2f} seconds/experiment.".format(
            (end_time - start_time) / len(config_param_values)
        )
    )
    return experiment_output_directory


class Experiment:
    def __init__(
        self,
        experiment_name,
        command_str,
        config_param_category,
        config_param_name,
        config_param_values,
        output_directory,
        setup_command_str=None,
        clean_up_command_str=None,
    ):
        """config_param_category should NOT include the square brackets"""

        self.experiment_name = experiment_name
        self.command_str = command_str
        self.config_param_category = config_param_category
        self.config_param_name = config_param_name
        self.config_param_values = config_param_values
        self.output_directory = output_directory
        self.setup_command_str = setup_command_str
        self.clean_up_command_str = clean_up_command_str

    def run_and_graph(self):
        experiment_output_directory = run_experiment(
            self.experiment_name,
            self.config_param_category,
            self.config_param_name,
            self.config_param_values,
            self.command_str,
            self.output_directory,
            self.setup_command_str,
            self.clean_up_command_str,
        )

        plot_graph.run_from_experiment(
            experiment_output_directory,
            self.config_param_category,
            self.config_param_name,
            self.config_param_values,
        )


if __name__ == "__main__":
    # Assumes the program is compiled
    command_str1a = "../run-sniper -n 1 -c ../disaggr_config/local_memory_cache.cfg -c ../disaggr_config/l3cache.cfg -c repeat_testing.cfg --roi -- ../test/a_disagg_test/mem_test"
    command_str1b = "../run-sniper -n 1 -c ../disaggr_config/local_memory_cache.cfg -c ../disaggr_config/l3cache.cfg -c repeat_testing.cfg --roi -- ./test/a_disagg_test/mem_test_varied"
    command_str2a = "../run-sniper -c ../disaggr_config/local_memory_cache.cfg -c ../disaggr_config/l3cache.cfg -c repeat_testing.cfg -- ../test/crono/apps/sssp/sssp ../test/crono/inputs/bcsstk05.mtx 1"
    command_str2b = "../run-sniper -c ../disaggr_config/local_memory_cache.cfg -c ../disaggr_config/l3cache.cfg -c repeat_testing.cfg -- ../test/crono/apps/sssp/sssp ../test/crono/inputs/bcsstk25.mtx 1"

    darknet_home = "../benchmarks/darknet"  # relative to disaggr_scripts directory
    ligra_home = "../benchmarks/ligra"  # relative to disaggr_scripts directory

    command_strs = {}
    # Note: using os.system(), the 'cd' of working directory doesn't persist to the next call to os.system()
    darknet_base_str = "cd {1} && ../../run-sniper -d {2} -c ../../disaggr_config/local_memory_cache.cfg -c {2}/repeat_testing.cfg -- {0}/darknet classifier predict {0}/cfg/imagenet1k.data {0}/cfg/{{0}}.cfg {0}/{{0}}.weights {0}/data/dog.jpg".format(
        ".", darknet_home, this_file_containing_dir_abspath
    )
    command_strs["darknet_tiny"] = darknet_base_str.format("tiny")
    command_strs["darknet_darknet19"] = darknet_base_str.format("darknet19")
    command_strs["darknet_vgg-16"] = darknet_base_str.format("vgg-16")
    command_strs["darknet_resnet50"] = darknet_base_str.format("resnet50")
    # cd ../benchmarks/darknet && ../../run-sniper -c ../../disaggr_config/local_memory_cache.cfg -g perf_model/dram/remote_mem_add_lat=200 -- ./darknet classifier predict ./cfg/imagenet1k.data ./cfg/tiny.cfg ./tiny.weights ./data/dog.jpg

    ligra_base_str = "../run-sniper -d {1} -c ../disaggr_config/local_memory_cache.cfg -c {1}/repeat_testing.cfg -- {0}/apps/{{0}} -s {0}/inputs/{{1}}".format(
        ligra_home, this_file_containing_dir_abspath
    )
    command_strs["ligra_bfs"] = ligra_base_str.format("BFS", "rMat_1000000")
    command_strs["ligra_pagerank"] = ligra_base_str.format("PageRank", "rMat_1000000")

    # Small input: first run some tests with smaller input size
    command_strs["ligra_bfs_small_input"] = ligra_base_str.format("BFS", "rMat_100000")
    command_strs["ligra_pagerank_small_input"] = ligra_base_str.format(
        "PageRank", "rMat_100000"
    )
    # ../run-sniper -c ../disaggr_config/local_memory_cache.cfg -g perf_model/dram/remote_mem_add_lat=200 -- ../benchmarks/ligra/apps/BFS -s ../benchmarks/ligra/inputs/rMat_1000000

    experiments = []
    # experiments.append(
    #     Experiment(
    #         experiment_name="darknet_tiny_remote_additional_latency_test",
    #         command_str=command_strs["darknet_tiny"],
    #         config_param_category="perf_model/dram",
    #         config_param_name="remote_mem_add_lat",
    #         config_param_values=[100],  # latency is in nanoseconds
    #         output_directory=".",
    #     )
    # )
    # experiments.append(
    #     Experiment(
    #         experiment_name="ligra_bfs_remote_additional_latency_test",
    #         command_str=command_strs["ligra_bfs"],
    #         config_param_category="perf_model/dram",
    #         config_param_name="remote_mem_add_lat",
    #         config_param_values=[100],  # latency is in nanoseconds
    #         output_directory=".",
    #     )
    # )
    darknet_experiments = []
    command_selection = "darknet_tiny"
    darknet_experiments.extend(
        [
            Experiment(
                experiment_name=command_selection + "_remote_additional_latency",
                command_str=command_strs[command_selection],
                config_param_category="perf_model/dram",
                config_param_name="remote_mem_add_lat",
                config_param_values=[
                    0,
                    100,
                    200,
                    500,
                    1000,
                    2000,
                    3000,
                    5000,
                    10000,
                ],  # latency is in nanoseconds
                output_directory=".",
            ),
            Experiment(
                experiment_name=command_selection + "_remote_bw_scalefactor",
                command_str=command_strs[command_selection],
                config_param_category="perf_model/dram",
                config_param_name="remote_mem_bw_scalefactor",
                config_param_values=[1, 2, 4, 8, 16, 32, 64, 128],
                output_directory=".",
            ),
            Experiment(
                experiment_name=command_selection + "_localdram_size",
                command_str=command_strs[command_selection],
                config_param_category="perf_model/dram",
                config_param_name="localdram_size",
                config_param_values=[4096, 16384, 65536, 262144, 524288, 1048576],
                output_directory=".",
            ),
        ]
    )
    ligra_experiments = []
    command_selection = "ligra_bfs_small_input"
    ligra_experiments.extend(
        [
            Experiment(
                experiment_name=command_selection + "_remote_additional_latency",
                command_str=command_strs[command_selection],
                config_param_category="perf_model/dram",
                config_param_name="remote_mem_add_lat",
                config_param_values=[
                    0,
                    100,
                    200,
                    500,
                    1000,
                    2000,
                    3000,
                    5000,
                    10000,
                ],  # latency is in nanoseconds
                output_directory=".",
            ),
            Experiment(
                experiment_name=command_selection + "_remote_bw_scalefactor",
                command_str=command_strs[command_selection],
                config_param_category="perf_model/dram",
                config_param_name="remote_mem_bw_scalefactor",
                config_param_values=[1, 2, 4, 8, 16, 32, 64, 128],
                output_directory=".",
            ),
            Experiment(
                experiment_name=command_selection + "_localdram_size",
                command_str=command_strs[command_selection],
                config_param_category="perf_model/dram",
                config_param_name="localdram_size",
                config_param_values=[4096, 16384, 65536, 262144, 524288, 1048576],
                output_directory=".",
            ),
        ]
    )

    experiments.extend(ligra_experiments)
    # experiments.extend(darknet_experiments)

    # # Remote memory testing experiments
    # command_str = command_str1a
    # experiments = [
    #     Experiment(
    #         experiment_name="bcsstk25_remote_additional_latency",
    #         command_str=command_str,
    #         config_param_category="perf_model/dram",
    #         config_param_name="remote_mem_add_lat",
    #         config_param_values=list(range(0, 100, 20))
    #         + list(range(100, 1000, 100))
    #         + list(range(1000, 10000, 1000))
    #         + [10000],  # latency is in nanoseconds
    #         output_directory="."
    #     ),
    #     Experiment(
    #         experiment_name="bcsstk25_remote_bw_scalefactor",
    #         command_str=command_str,
    #         config_param_category="perf_model/dram",
    #         config_param_name="remote_mem_bw_scalefactor",
    #         config_param_values=[1, 2, 4, 8, 16, 32, 64, 128],
    #         output_directory="."
    #     ),
    #     Experiment(
    #         experiment_name="bcsstk25_localdram_size",
    #         command_str=command_str,
    #         config_param_category="perf_model/dram",
    #         config_param_name="localdram_size",
    #         # config_param_values=[16384, 163840] + list(range(1000000, 7000000, 1000000)) + list(range(7000000, 77000001, 7000000)))
    #         config_param_values=[4096, 16384, 65536, 262144, 524288, 1048576],
    #         # 950000 is approx the working set size for bcsstk05
    #         output_directory="."
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
