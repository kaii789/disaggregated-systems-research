# Python 3
import sys
import os
import time
import getopt
import subprocess

import plot_graph

sys.path.append(os.path.join(os.path.dirname(__file__), "tools"))

# Add root Sniper directory to path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
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
):
    """config_param_category shouldn't include the square brackets; config_param_values should be an iterable of values"""
    output_files_directory = experiment_name + "_output_files"

    if os.path.exists(output_files_directory):
        # print("Warning: the output directory {} already exists (maybe a previous experiment with the same name?), files in it may be overwritten")
        # Find another directory name that doesn't already exist
        num = 2
        while os.path.exists(output_files_directory):
            output_files_directory = (
                experiment_name + "_output_files_" + str(num)
            )
            num += 1
    os.makedirs(output_files_directory)

    start_time = time.time()
    for experiment_no, config_param_value in enumerate(config_param_values):
        # Update config file
        with open("repeat_testing.cfg", "w") as variating_config_file:
            # variating_config_file.truncate(0)  # start writing from the beginning of the file
            variating_config_file.write(
                "[{}]\n{} = {}\n".format(
                    config_param_category, config_param_name, config_param_value
                )
            )

        # Run the program
        ret_val = os.system(command_str)
        if ret_val != 0:
            print(
                "Run-sniper-repeat with config {} got error ret val:\n[[{}]]".format(
                    config_param_value, ret_val
                )
            )
            sys.exit(-1)

        # Save a copy of the output for later reference
        files_to_save = ["sim.cfg", "sim.out"]
        for filename in files_to_save:
            os.system(
                "cp {0} {1}/{2}_{0}".format(
                    filename, output_files_directory, experiment_no + 1
                )
            )

        if experiment_no % 4 == 0:
            print("Experiment {} done.".format(experiment_no + 1))
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
    return output_files_directory


class Experiment:
    def __init__(
        self,
        experiment_name,
        command_str,
        config_param_category,
        config_param_name,
        config_param_values,
    ):
        """config_param_category should NOT include the square brackets"""

        self.experiment_name = experiment_name
        self.command_str = command_str
        self.config_param_category = config_param_category
        self.config_param_name = config_param_name
        self.config_param_values = config_param_values

    def run_and_graph(self):
        output_directory = run_experiment(
            self.experiment_name,
            self.config_param_category,
            self.config_param_name,
            self.config_param_values,
            self.command_str,
        )

        plot_graph.run_from_experiment(
            output_directory,
            self.config_param_category,
            self.config_param_name,
            self.config_param_values,
        )


if __name__ == "__main__":
    # Assumes the program is compiled
    command_str1a = "../run-sniper -n 1 -c ../disaggr_config/nandita_cache.cfg -c ../disaggr_config/l3cache.cfg -c repeat_testing.cfg --roi -- ../test/a_disagg_test/mem_test"
    command_str1b = "../run-sniper -n 1 -c ../disaggr_config/nandita_cache.cfg -c ../disaggr_config/l3cache.cfg -c repeat_testing.cfg --roi -- ./test/a_disagg_test/mem_test_varied"
    command_str2a = "../run-sniper -c ../disaggr_config/nandita_cache.cfg -c ../disaggr_config/l3cache.cfg -c repeat_testing.cfg -- ../test/crono/apps/sssp/sssp ../test/crono/inputs/bcsstk05.mtx 1"
    command_str2b = "../run-sniper -c ../disaggr_config/nandita_cache.cfg -c ../disaggr_config/l3cache.cfg -c repeat_testing.cfg -- ../test/crono/apps/sssp/sssp ../test/crono/inputs/bcsstk25.mtx 1"

    command_str = command_str2b

    experiments = [
        Experiment(
            experiment_name="bcsstk25_remote_additional_latency",
            command_str=command_str,
            config_param_category="perf_model/dram",
            config_param_name="remote_mem_add_lat",
            config_param_values=list(range(0, 100, 20))
            + list(range(100, 1000, 100))
            + list(range(1000, 10000, 1000))
            + [10000],  # latency is in nanoseconds
        ),
        Experiment(
            experiment_name="bcsstk25_remote_bw_scalefactor",
            command_str=command_str,
            config_param_category="perf_model/dram",
            config_param_name="remote_mem_bw_scalefactor",
            config_param_values=[1, 2, 4, 8, 16, 32, 64, 128],
        ),
        Experiment(
            experiment_name="bcsstk25_localdram_size",
            command_str=command_str,
            config_param_category="perf_model/dram",
            config_param_name="localdram_size",
            # config_param_values=[16384, 163840] + list(range(1000000, 7000000, 1000000)) + list(range(7000000, 77000001, 7000000)))
            config_param_values=[4096, 16384, 65536, 262144, 524288, 1048576],
        ),  # 950000 is approx the working set size for bcsstk05
    ]

    for experiment in experiments:
        experiment.run_and_graph()
