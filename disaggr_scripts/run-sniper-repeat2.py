# Python 3
from __future__ import annotations
import sys
import os
import stat
import time
import traceback
import datetime
import copy
import getopt
import shutil
import subprocess
from collections import deque

import typing
from typing import Dict, List, Iterable, Optional, TextIO, Union, TypeVar

# import plot_graph
# import plot_graph_pq

PathLike = TypeVar("PathLike", str, bytes, os.PathLike)  # Type for file/directory paths

this_file_containing_dir_abspath = os.path.dirname(os.path.abspath(__file__))

# If scripts in the Sniper tools folder need to be called
sys.path.append(os.path.join(this_file_containing_dir_abspath, "..", "tools"))

# Add root Sniper directory to path
sys.path.insert(0, os.path.join(this_file_containing_dir_abspath, ".."))
# print(sys.path)


class ConfigEntry:
    """Represent one config entry used to configure Sniper."""

    def __init__(self, category: str, name: str, value: str) -> None:
        """Note: value should be a string for the config file (even if it seems
        like a numeric type), and category should NOT include the square
        brackets.

        Example: Config("perf_model/dram", "remote_mem_add_lat", 5)
        """
        self.category = category
        self.name = name
        self.value = value

        # Make sure category doesn't include the starting/ending square brackets:
        if category[0] == "[" and category[-1] == "]":
            self.category = category[1:-1]  # Strip enclosing square brackets

    def __copy__(self) -> ConfigEntry:
        return self.__deepcopy__(memo={})  # Deep copy is the same in this case

    def __deepcopy__(self, memo) -> ConfigEntry:
        # No recursive data structures, so we can ignore  the memo argument
        return ConfigEntry(self.category, self.name, self.value)


class ExperimentRunConfig:
    """A collection of additional configs to specify for a particular
    Sniper ExperimentRun.
    """

    def __init__(self, config_entries: Iterable[ConfigEntry]) -> None:
        self.config_tree = {}
        self.add_config_entries(config_entries)

    def add_config_entry(self, config_entry: ConfigEntry):
        """Add a ConfigEntry to this collection. config_entry should not
        conflict with existing entries in the ExperimentRunConfig, ie it
        should not have the same category and name yet have a different value
        than a ConfigEntry that is already in this collection.
        """
        if config_entry.category not in self.config_tree:
            self.config_tree[config_entry.category] = {}
        if (
            config_entry.name in self.config_tree[config_entry.category]
            and config_entry.value
            == self.config_tree[config_entry.category][config_entry.name]
        ):
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
        """Add the specified ConfigEntry's to this collection. None of the entries
        should conflict with each other or existing entries in the
        ExperimentRunConfig, ie none should have the same category and name yet
        have a different value than a ConfigEntry in config_entries or one already
        in this collection.
        """
        for config_entry in config_entries:
            self.add_config_entry(config_entry)

    def generate_config_file_str(self) -> str:
        """Return a string that when written to a file, will constitute a config
        file containing this ExperimentRunConfig's ConfigEntry entries.
        """
        lines = []  # list of lines in the config file
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

    def __copy__(self) -> ExperimentRunConfig:
        return self.__deepcopy__(memo={})  # Want deep copy behaviour in this case

    def __deepcopy__(self, memo) -> ExperimentRunConfig:
        # Referenced from https://stackoverflow.com/a/15774013
        result = self.__class__.__new__(self.__class__)
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            setattr(result, key, copy.deepcopy(value, memo))
        return result


class ExperimentRun:
    """Contain information that specifies the configuration for a particular
    'run' of an Experiment.
    """

    def __init__(
        self,
        experiment_name: str,
        experiment_run_no: int,
        command_str: str,
        experiment_output_directory_abspath: PathLike,
        config_file_str: str,
        setup_command_str=None,
        clean_up_command_str=None,
    ) -> None:
        self.experiment_name = experiment_name
        self.experiment_run_no = experiment_run_no
        self.command_str = command_str
        self.experiment_output_directory_abspath = experiment_output_directory_abspath
        self.config_file_str = config_file_str
        self.setup_command_str = setup_command_str
        self.clean_up_command_str = clean_up_command_str
        self.log_str = "Experiment {} run {} missing log str\n".format(
            experiment_name, experiment_run_no
        )

    def get_config_file_str(self) -> str:
        """Write this string to a file to generate a config file that specifies
        the additional configs for this ExperimentRun.
        """
        return self.config_file_str

    def get_execution_script_str(self) -> str:
        """Write this string to a file to generate a script that executes this
        ExperimentRun.

        The returned string needs to be formatted with named argument
        sniper_output_dir: where the experiment run output directory is
        """
        lines = []

        # lines.append("cd {0}")

        if self.setup_command_str:
            lines.append(self.setup_command_str)

        lines.append('echo "Running linux command:\n{}"'.format(self.command_str))
        if "{sniper_output_dir}" not in self.command_str:
            # command_str should have a {0} field to specify the Sniper output directory
            raise ValueError(
                "Experiment {} run {} missing '{{sniper_output_dir}}' in command_str to specify Sniper output directory. command_str given:\n{}".format(
                    self.experiment_name, self.experiment_run_no, self.command_str
                )
            )
        lines.append(self.command_str)
        lines.append(
            'if [ $? !=  0 ] ; then echo "{}" $?; fi'.format(
                "Run-sniper-repeat command '{}' for experiment {} run {} got error ret val: ".format(
                    self.command_str, self.experiment_name, self.experiment_run_no
                )
            )
        )  # using single bracket [ ] testing for now, since might not be sure which shell is used

        if self.clean_up_command_str:
            lines.append(self.clean_up_command_str)

        # Wait a little bit of time in case something needs to wrap up
        lines.append("sleep 30")  # sleep for 30 seconds

        # Save a copy of the output for later reference
        files_to_save = ["sim.cfg", "sim.out", "sim.stats.sqlite3"]
        for filename in files_to_save:
            lines.append(
                'cp "{0}" "{1}"/"{2}_{0}"'.format(
                    filename,
                    self.experiment_output_directory_abspath,
                    self.experiment_run_no,
                )
            )

        return "\n".join(lines)

    def set_log_str(self, log_str) -> None:
        """Set the log string of this ExperimentRun."""
        self.log_str = log_str

    def get_log_str(self) -> str:
        """Return the log string of this ExperimentRun."""
        return self.log_str


class Experiment:
    """Represents an experiment to run, specified with:
    1) Parameters including a command string to run and configs for experiment runs
    2) Commands to run after the experiment (eg graphing)
    """

    _experiment_runs: List[ExperimentRun]
    _experiment_output_dir_abspath: Optional[PathLike]
    _completed_experiment_runs: int

    def __init__(
        self,
        experiment_name: str,
        command_str: str,
        experiment_run_configs: Iterable[ExperimentRunConfig],
        output_root_directory: PathLike,
        setup_command_str=None,
        clean_up_command_str=None,
    ):
        self.experiment_name = experiment_name
        self.command_str = command_str
        self.experiment_run_configs = experiment_run_configs
        self.output_root_directory = output_root_directory
        self.setup_command_str = setup_command_str
        self.clean_up_command_str = clean_up_command_str
        self.start_time = None
        self._experiment_runs = []
        self._experiment_output_dir_abspath = None
        self._completed_experiment_runs = 0

    def prepare_experiment(self) -> List[ExperimentRun]:
        """Create directory that will eventually contain all finalized experiment
        output, and generate a list of ExperimentRuns.
        """
        # Find a directory name that doesn't already exist
        experiment_output_directory_name = self.experiment_name + "_output_files"
        experiment_output_directory = os.path.join(
            self.output_root_directory, experiment_output_directory_name
        )
        num = 2
        while os.path.exists(experiment_output_directory):
            experiment_output_directory_name = (
                self.experiment_name + "_output_files_" + str(num)
            )
            experiment_output_directory = os.path.join(
                self.output_root_directory, experiment_output_directory_name
            )
            num += 1
        os.makedirs(experiment_output_directory)
        # Use absolute path from now on so no future results get messed up
        self._experiment_output_dir_abspath = os.path.abspath(
            experiment_output_directory
        )

        self.start_time = time.time()
        for experiment_no, config_collection in enumerate(self.experiment_run_configs):
            # Generate ExperimentRun objects
            obj = ExperimentRun(
                self.experiment_name,
                experiment_no + 1,
                self.command_str,
                self._experiment_output_dir_abspath,
                config_collection.generate_config_file_str(),
            )
            self._experiment_runs.append(obj)
        return self._experiment_runs.copy()  # Shallow copy

    def experiment_run_completed(self) -> None:
        """Run this method when a run of this experiment (not necessarily in
        order) is completed.
        """
        self._completed_experiment_runs += 1

    def experiment_done(self) -> bool:
        """Return True iff all runs of this experiment are completed."""
        return self._completed_experiment_runs == len(self._experiment_runs)

    def compile_experiment_log(self) -> PathLike:
        """Create and return a log file from the log strings in this Experiment's
        ExperimentRun objects.
        """
        # Create log file in the experiment output directory
        log_file_path = os.path.join(
            self._experiment_output_dir_abspath,
            "Experiment_{}.log".format(self.experiment_name),
        )
        with open(log_file_path, "w") as log_file:
            for experiment_run in self._experiment_runs:
                log_file.write(experiment_run.get_log_str())
                log_file.write("\n\n")
        return log_file_path

    def post_experiment_processing(self) -> None:
        """Run this method after all runs of the experiment have finished."""
        # Compile logs
        log_file_path = self.compile_experiment_log()

        with open(log_file_path, "a") as log_file:
            log_file.write(
                "Finished {} runs (potentially some in parallel) in {:.2f} seconds\n\n".format(
                    self._completed_experiment_runs, time.time() - self.start_time
                )
            )

            # # Provide extra context to console output
            # print("Experiment {}:".format(self.experiment_name))
            # # Custom graph plotting function
            # plot_graph_pq.run_from_experiment(
            #     self._experiment_output_dir_abspath, log_file
            # )

    ### The following are older versions of methods used to run experiments
    def run_and_graph(self):
        """Older version, running experiment directly and graphing results
        without parallelization."""
        experiment_output_directory = self.run_experiment()

        # These experiments will use custom graph plotting functions
        # plot_graph.run_from_experiment(
        #     experiment_output_directory,
        #     self.config_param_category,
        #     self.config_param_name,
        #     self.config_param_values,
        # )

    def run_experiment(self) -> PathLike:
        """Older version, running experiment directly without parallelization."""
        # Find a directory name that doesn't already exist
        experiment_output_directory_name = self.experiment_name + "_output_files"
        experiment_output_directory = os.path.join(
            self.output_root_directory, experiment_output_directory_name
        )
        num = 2
        while os.path.exists(experiment_output_directory):
            experiment_output_directory_name = (
                self.experiment_name + "_output_files_" + str(num)
            )
            experiment_output_directory = os.path.join(
                self.output_root_directory, experiment_output_directory_name
            )
            num += 1
        os.makedirs(experiment_output_directory)

        start_time = time.time()
        for experiment_no, config_collection in enumerate(self.experiment_run_configs):
            # Update config file
            with open(
                os.path.join(experiment_output_directory, "repeat_testing.cfg"),
                "w",
            ) as variating_config_file:
                # variating_config_file.truncate(0)  # start writing from the beginning of the file;
                # not needed since open with "w" automatically does this
                variating_config_file.write(
                    config_collection.generate_config_file_str()
                )

            # Run the program
            error_occurred = False
            command_strs = [self.command_str]
            if self.setup_command_str:
                command_strs.insert(0, self.setup_command_str)
            if self.clean_up_command_str:
                command_strs.append(self.clean_up_command_str)
            for cmd_str in command_strs:
                print("Running linux command:\n{}".format(cmd_str))
                wait_status = os.system(cmd_str)  # Behaviour on Linux
                if os.WIFSIGNALED(wait_status) and os.WTERMSIG(wait_status) == 2:
                    # Keyboard Interrupt, stop execution of entire program
                    sys.exit(-1)
                elif os.WIFEXITED(wait_status) and os.WEXITSTATUS(wait_status) != 0:
                    error_occurred = True
                    print(
                        "Run-sniper-repeat command '{}' for experiment run {} got error ret val:\n[[{}]]".format(
                            cmd_str,
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
                "Experiment {} run {} done.".format(
                    self.experiment_name, experiment_no + 1
                )
            )

        end_time = time.time()
        print(
            "\nRan {} experiment runs in {:.2f} seconds.".format(
                len(self.experiment_run_configs), end_time - start_time
            )
        )
        print(
            "Average: {:.2f} seconds/experiment run.".format(
                (end_time - start_time) / len(self.experiment_run_configs)
            )
        )
        return experiment_output_directory


class ExperimentManager:
    class ProcessInfo:
        """Class only used by ExperimentManager, collecting information needed
        by a process to run an ExperimentRun."""

        process: Optional[subprocess.Popen]
        start_time: Optional[float]
        log_file: Optional[TextIO]
        experiment_run: Optional[ExperimentRun]
        containing_experiment: Optional[Experiment]
        temp_dir: Optional[PathLike]

        def __init__(self) -> None:
            self.process = None
            self.start_time = None
            self.log_file = None
            self.experiment_run = None
            self.containing_experiment = None
            self.temp_dir = None

    class ProcessQueueInfo:
        """Class only used by ExperimentManager, to keep track of the
        containing Experiment of an ExperimentRun."""

        def __init__(
            self, containing_experiment: Experiment, experiment_run: ExperimentRun
        ) -> None:
            self.containing_experiment = containing_experiment
            self.experiment_run = experiment_run

    _pending_experiments: typing.Deque[Experiment]
    _running_experiments: List[Experiment]
    _process_queue: typing.Deque[ProcessQueueInfo]
    _current_concurrent_processes: int

    def __init__(
        self,
        output_root_directory: PathLike,
        max_concurrent_processes: int,
        log_file: TextIO,
    ) -> None:
        self.output_directory_abspath = os.path.abspath(output_root_directory)
        self.max_concurrent_processes = max_concurrent_processes
        self.log_file = log_file
        self._pending_experiments = deque([])
        self._running_experiments = []  # use list for easier extracting from the middle
        self._process_queue = deque([])  # append, popleft
        self._current_concurrent_processes = 0

    # def set_max_concurrent_processes(self, max_concurrent_processes: int) -> None:
    #     self.max_concurrent_processes = max_concurrent_processes

    def add_experiment(self, experiment: Experiment) -> None:
        self._pending_experiments.append(experiment)

    def add_experiments(self, experiments: Iterable[Experiment]) -> None:
        self._pending_experiments.extend(experiments)

    def start(self) -> None:
        """Start running Experiment's added to this ExperimentManager."""
        os.chdir(self.output_directory_abspath)
        process_info = [
            ExperimentManager.ProcessInfo()
            for _ in range(self.max_concurrent_processes)
        ]

        # Set up temp directories for the processes
        # for process_num in range(self.max_concurrent_processes):
        #     process_temp_dir_name = "process_{}_temp".format(process_num)
        #     process_temp_dir = os.path.join(
        #         self.output_directory_abspath, process_temp_dir_name
        #     )
        #     if not os.path.isdir(process_temp_dir):
        #         os.makedirs(process_temp_dir)
        #     process_info[process_num].temp_dir = process_temp_dir

        try:
            while (
                len(self._pending_experiments) > 0
                or len(self._process_queue) > 0
                or sum(pi.process is None for pi in process_info) != len(process_info)
            ):
                if (
                    len(self._process_queue) < self.max_concurrent_processes
                    and len(self._pending_experiments) > 0
                    and sum(pi.process is None for pi in process_info) > 0
                ):
                    # Replenish self._process_queue if there are more experiments yet to be started,
                    # and there is a free process slot
                    experiment = self._pending_experiments.popleft()
                    self._running_experiments.append(experiment)
                    experiment_runs = experiment.prepare_experiment()
                    for experiment_run in experiment_runs:
                        self._process_queue.append(
                            ExperimentManager.ProcessQueueInfo(
                                experiment, experiment_run
                            )
                        )

                for index in range(len(process_info)):
                    if (
                        process_info[index].process is None
                        and len(self._process_queue) > 0
                    ):
                        process_request = self._process_queue.popleft()
                        process_info[
                            index
                        ].experiment_run = process_request.experiment_run
                        process_info[
                            index
                        ].containing_experiment = process_request.containing_experiment

                        # Create temp dir
                        process_temp_dir_name = "run_{}_process_{}_temp".format(
                            process_info[index].experiment_run.experiment_run_no, index
                        )
                        process_temp_dir = os.path.join(
                            process_info[
                                index
                            ].containing_experiment._experiment_output_dir_abspath,
                            process_temp_dir_name,
                        )
                        if not os.path.isdir(process_temp_dir):
                            os.makedirs(process_temp_dir)
                        process_info[index].temp_dir = process_temp_dir

                        # Change current working directory to that of the process to spawn
                        os.chdir(process_info[index].temp_dir)
                        # Create/Update config file
                        with open(
                            "repeat_testing.cfg",
                            "w",
                        ) as variating_config_file:
                            variating_config_file.write(
                                process_info[index].experiment_run.get_config_file_str()
                            )

                        # Create ExperimentRun execution script
                        execution_script_path = "experiment_run_{}.sh".format(
                            process_info[index].experiment_run.experiment_run_no
                        )
                        with open(
                            execution_script_path,
                            "w",
                        ) as execution_script:
                            # use current directory for Sniper output since we're already in the process' temp dir
                            execution_script.write(
                                process_info[index]
                                .experiment_run.get_execution_script_str()
                                .format(sniper_output_dir=os.path.abspath("."))
                            )
                        # os.system('chmod a+x "{}"'.format(execution_script_path))
                        os.chmod(
                            execution_script_path,
                            os.stat(execution_script_path).st_mode
                            | stat.S_IXUSR
                            | stat.S_IXGRP
                            | stat.S_IXOTH,
                        )

                        # Log file for this ExperimentRun for this process
                        log_file = open("process_{}.log".format(index), "w+")
                        process_info[index].log_file = log_file
                        # Spawn process and execute execution script
                        process_info[index].process = subprocess.Popen(
                            '"./{}"'.format(execution_script_path),
                            shell=True,
                            stdout=log_file,
                            stderr=subprocess.STDOUT,
                            text=True,
                        )
                        process_info[index].start_time = time.time()
                        log_str = "Process {} for experiment {} run {} started at time {}".format(
                            index,
                            process_info[index].experiment_run.experiment_name,
                            process_info[index].experiment_run.experiment_run_no,
                            datetime.datetime.now().astimezone(),
                        )
                        print(log_str)
                        print(log_str, file=self.log_file)

                        # Restore current working directory after setting up the process
                        os.chdir(self.output_directory_abspath)
                    elif process_info[index].process is not None:
                        ret = process_info[index].process.poll()
                        if ret is not None:
                            # Process is done
                            if process_info[index].process.returncode != 0:
                                log_str = "Experiment {} run {} execution script returned non-zero exit status of {}".format(
                                    process_info[index].experiment_run.experiment_name,
                                    process_info[
                                        index
                                    ].experiment_run.experiment_run_no,
                                    process_info[index].process.returncode,
                                )
                                print(log_str)
                                print(log_str, file=self.log_file)
                            end_time = time.time()
                            log_str = "Experiment {} run {} complete; took {:.2f} seconds (current time: {})".format(
                                process_info[index].experiment_run.experiment_name,
                                process_info[index].experiment_run.experiment_run_no,
                                end_time - process_info[index].start_time,
                                datetime.datetime.now().astimezone(),
                            )
                            print(log_str)
                            print(log_str, file=self.log_file)

                            process_info[
                                index
                            ].containing_experiment.experiment_run_completed()
                            process_info[index].process = None
                            # Write log file string to ExperimentRun object for later records
                            process_info[index].log_file.seek(0)
                            process_info[index].experiment_run.set_log_str(
                                "Experiment run {}:\n".format(
                                    process_info[index].experiment_run.experiment_run_no
                                )
                                + process_info[index].log_file.read()
                            )
                            process_info[index].log_file.close()
                            process_info[index].log_file = None

                            # Create backup of temp folder; we should have cwd of self.output_directory_abspath
                            # Note: this doesn't work now, since some experiment runs could be run in the same process
                            # and have the same temp folder name, which causes shutil.copytree() to fail
                            time.sleep(5)  # give a bit of time for things to settle in
                            # try:
                            #     shutil.copytree(
                            #         process_info[index].temp_dir,
                            #         os.path.join(
                            #             process_info[
                            #                 index
                            #             ].experiment_run.experiment_output_directory_abspath,
                            #             "process_{}_temp_copy".format(index),
                            #         ),
                            #     )
                            # except Exception as e:
                            #     # Print exception details but don't let this copying crash the entire ExperimentManager
                            #     traceback.print_exc()
                            #     traceback.print_exc(file=self.log_file)

                # Process experiments that have all runs completed
                i = 0
                while i < len(self._running_experiments):
                    if self._running_experiments[i].experiment_done():
                        try:
                            self._running_experiments[i].post_experiment_processing()
                        except Exception as e:
                            # Print exception details but don't let this post-processing crash the entire ExperimentManager
                            traceback.print_exc()
                            traceback.print_exc(file=self.log_file)
                        log_str = "Experiment {} complete".format(
                            self._running_experiments[i].experiment_name
                        )
                        print(log_str)
                        print(log_str, file=self.log_file)
                        self._running_experiments.pop(i)
                    else:
                        i += 1

                if len(self._process_queue) > 0 or len(self._pending_experiments) == 0:
                    # Can sleep for a while since don't need to check processes that often; reduce CPU usage
                    time.sleep(60)  # sleep for 1 min

        except KeyboardInterrupt:
            pass  # Cleanup is done in the finally block
        except Exception as e:
            # Print exception traceback to both stdout and log file
            traceback.print_exc()
            traceback.print_exc(file=self.log_file)
        finally:
            # Cleanup
            for pi in process_info:
                if pi.process is not None:
                    pi.process.terminate()
            time.sleep(0.5)  # Give processes some time to terminate
            for pi in process_info:
                if pi.log_file is not None:
                    pi.log_file.close()
            # Write experiment progress to files, even though experiments might not be done yet
            for experiment in self._running_experiments:
                experiment.compile_experiment_log()


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
    ONE_MILLION = 1000000  # eg to specify how many instructions to run
    ONE_MB_TO_BYTES = 1024 * 1024  # eg to specify localdram_size

    # Previous test strings; assumes the program is compiled
    command_str1a = "{sniper_root}/run-sniper -d {{sniper_output_dir}} -n 1 -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg --roi -- {sniper_root}/test/a_disagg_test/mem_test".format(
        sniper_root=subfolder_sniper_root_relpath
    )
    command_str1b = "{sniper_root}/run-sniper -d {{sniper_output_dir}} -n 1 -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c repeat_testing.cfg --roi -- {sniper_root}/test/a_disagg_test/mem_test_varied".format(
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
    ligra_base_str_options = "{sniper_root}/run-sniper -d {{{{sniper_output_dir}}}} -c {sniper_root}/disaggr_config/local_memory_cache.cfg -c {{{{sniper_output_dir}}}}/repeat_testing.cfg {{sniper_options}} -- {0}/apps/{{0}} -s -rounds 1 {0}/inputs/{{1}}".format(
        ligra_home, sniper_root=subfolder_sniper_root_relpath
    )
    ligra_input_to_file = {
        "regular_input": "rMat_1000000",
        "small_input": "rMat_100000",
    }
    command_strs["ligra_bfs"] = ligra_base_str_options.format(
        "BFS", ligra_input_to_file["regular_input"], sniper_options=""
    )
    command_strs["ligra_pagerank"] = ligra_base_str_options.format(
        "PageRank", ligra_input_to_file["regular_input"], sniper_options=""
    )

    # Small input: first run some tests with smaller input size
    command_strs["ligra_bfs_small_input"] = ligra_base_str_options.format(
        "BFS", ligra_input_to_file["small_input"], sniper_options=""
    )
    command_strs["ligra_pagerank_small_input"] = ligra_base_str_options.format(
        "PageRank", ligra_input_to_file["small_input"], sniper_options=""
    )
    # ../run-sniper -c ../disaggr_config/local_memory_cache.cfg -- ../benchmarks/ligra/apps/BFS -s ../benchmarks/ligra/inputs/rMat_1000000

    # Stop around 100 Million instructions after entering ROI (magic = true in config so don't need --roi flag)
    command_strs["ligra_bfs_instrs_100mil"] = ligra_base_str_options.format(
        "BFS",
        ligra_input_to_file["regular_input"],
        sniper_options="-s stop-by-icount:{}".format(100 * ONE_MILLION),
    )

    # 8 MB for ligra_bfs + rMat_1000000
    command_strs["ligra_bfs_localdram_8MB"] = ligra_base_str_options.format(
        "BFS",
        ligra_input_to_file["regular_input"],
        sniper_options="-g perf_model/dram/localdram_size={}".format(
            int(8 * ONE_MB_TO_BYTES)
        ),
    )
    # 1 MB for ligra_bfs + rMat_100000
    command_strs["ligra_bfs_small_input_localdram_1MB"] = ligra_base_str_options.format(
        "BFS",
        ligra_input_to_file["small_input"],
        sniper_options="-g perf_model/dram/localdram_size={}".format(
            int(1 * ONE_MB_TO_BYTES)
        ),
    )

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
            ConfigEntry(
                "perf_model/dram/compression_model", "use_compression", "false"
            ),
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

    pq_cacheline_combined_configs = []
    for config in (
        partition_queue_series_experiment_run_configs + cacheline_queue_ratio_configs
    ):
        config_copy = copy.deepcopy(config)
        config_copy.add_config_entry(
            ConfigEntry("perf_model/dram/compression_model", "use_compression", "false")
        )
        pq_cacheline_combined_configs.append(config_copy)


    experiments = []

    darknet_darknet19_pq_cacheline_combined_experiments = []
    model_type = "darknet19"
    for num_MB in [4]:
        for bw_scalefactor in [4]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = darknet_base_str_options.format(
                model_type,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                    int(num_MB * ONE_MB_TO_BYTES),
                    int(120),
                    int(bw_scalefactor),
                    int(1000 * ONE_MILLION),
                ),
            )
            # 1 billion instructions cap

            darknet_darknet19_pq_cacheline_combined_experiments.append(
                Experiment(
                    experiment_name="darknet_{}_localdram_{}_netlat_120_bw_scalefactor_{}_pq_cacheline_combined_series".format(
                        model_type.lower(), localdram_size_str, bw_scalefactor
                    ),
                    command_str=command_str,
                    experiment_run_configs=pq_cacheline_combined_configs,
                    output_root_directory=".",
                )
            )

    darknet_resnet50_pq_cacheline_combined_experiments = []
    model_type = "resnet50"
    for num_MB in [4]:
        for bw_scalefactor in [4]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = darknet_base_str_options.format(
                model_type,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                    int(num_MB * ONE_MB_TO_BYTES),
                    int(120),
                    int(bw_scalefactor),
                    int(1000 * ONE_MILLION),
                ),
            )
            # 1 billion instructions cap

            darknet_resnet50_pq_cacheline_combined_experiments.append(
                Experiment(
                    experiment_name="darknet_{}_localdram_{}_netlat_120_bw_scalefactor_{}_pq_cacheline_combined_series".format(
                        model_type.lower(), localdram_size_str, bw_scalefactor
                    ),
                    command_str=command_str,
                    experiment_run_configs=pq_cacheline_combined_configs,
                    output_root_directory=".",
                )
            )

    darknet_tiny_pq_cacheline_combined_experiments = []
    model_type = "tiny"
    for num_MB in [4]:
        for bw_scalefactor in [4]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = darknet_base_str_options.format(
                model_type,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                    int(num_MB * ONE_MB_TO_BYTES),
                    int(120),
                    int(bw_scalefactor),
                    int(1000 * ONE_MILLION),
                ),
            )
            # 1 billion instructions cap

            darknet_tiny_pq_cacheline_combined_experiments.append(
                Experiment(
                    experiment_name="darknet_{}_localdram_{}_netlat_120_bw_scalefactor_{}_pq_cacheline_combined_series".format(
                        model_type.lower(), localdram_size_str, bw_scalefactor
                    ),
                    command_str=command_str,
                    experiment_run_configs=pq_cacheline_combined_configs,
                    output_root_directory=".",
                )
            )


    darknet_tiny_cacheline_ratio_experiments = []
    model_type = "tiny"
    for num_MB in [4]:
        for bw_scalefactor in [4]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = darknet_base_str_options.format(
                model_type,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={} -s stop-by-icount:{}".format(
                    int(num_MB * ONE_MB_TO_BYTES),
                    int(120),
                    int(bw_scalefactor),
                    int(1000 * ONE_MILLION),
                ),
            )
            # 1 billion instructions cap

            darknet_tiny_cacheline_ratio_experiments.append(
                Experiment(
                    experiment_name="darknet_{}_localdram_{}_netlat_120_bw_scalefactor_{}_cacheline_ratio_series".format(
                        model_type.lower(), localdram_size_str, bw_scalefactor
                    ),
                    command_str=command_str,
                    experiment_run_configs=partition_queue_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )

    darknet_tiny_pq_experiments_noicountstop = []
    model_type = "tiny"
    for num_MB in [4]:
        for bw_scalefactor in [4]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = darknet_base_str_options.format(
                model_type,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={}".format(
                    int(num_MB * ONE_MB_TO_BYTES), int(120), int(bw_scalefactor)
                ),
            )
            # 1 billion instructions cap

            darknet_tiny_pq_experiments_noicountstop.append(
                Experiment(
                    experiment_name="darknet_{}_localdram_{}_netlat_120_bw_scalefactor_{}_partition_queue_series".format(
                        model_type.lower(), localdram_size_str, bw_scalefactor
                    ),
                    command_str=command_str,
                    experiment_run_configs=partition_queue_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )

    darknet_tiny_cacheline_ratio_experiments_noicountstop = []
    model_type = "tiny"
    for num_MB in [4]:
        for bw_scalefactor in [4]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = darknet_base_str_options.format(
                model_type,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={}".format(
                    int(num_MB * ONE_MB_TO_BYTES), int(120), int(bw_scalefactor)
                ),
            )
            # 1 billion instructions cap

            darknet_tiny_cacheline_ratio_experiments_noicountstop.append(
                Experiment(
                    experiment_name="darknet_{}_localdram_{}_netlat_120_bw_scalefactor_{}_cacheline_ratio_series".format(
                        model_type.lower(), localdram_size_str, bw_scalefactor
                    ),
                    command_str=command_str,
                    experiment_run_configs=partition_queue_series_experiment_run_configs,
                    output_root_directory=".",
                )
            )

    experiments.extend(darknet_tiny_pq_experiments)
    experiments.extend(darknet_tiny_cacheline_ratio_experiments)
    experiments.extend(darknet_tiny_pq_experiments_noicountstop)
    experiments.extend(darknet_tiny_cacheline_ratio_experiments_noicountstop)

    bcsstk32_bw_verification_experiments = []
    for num_B in [131072, 262144]:
        for bw_scalefactor in [4, 8, 32]:
            localdram_size_str = "{}B".format(num_B)
            command_str = command_str2c_base_options.format(
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={}".format(
                    num_B, 120, bw_scalefactor
                ),
            )

            bcsstk32_bw_verification_experiments.append(
                Experiment(
                    experiment_name="bcsstk32_localdram_{}_bw_scalefactor_{}_verification_series".format(
                        localdram_size_str, bw_scalefactor
                    ),
                    command_str=command_str,
                    experiment_run_configs=queue_delay_cap_configs,
                    output_root_directory=".",
                )
            )

    # BFS, 8, 16 MB
    bfs_bw_verification_experiments = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    for num_MB in [8]:  # 16
        for bw_scalefactor in [4, 8, 32]:
            localdram_size_str = "{}MB".format(num_MB)
            command_str = ligra_base_str_options.format(
                application_name,
                ligra_input_file,
                sniper_options="-g perf_model/dram/localdram_size={} -g perf_model/dram/remote_mem_add_lat={} -g perf_model/dram/remote_mem_bw_scalefactor={}".format(
                    int(num_MB * ONE_MB_TO_BYTES), 120, bw_scalefactor
                ),
            )

            bfs_bw_verification_experiments.append(
                Experiment(
                    experiment_name="ligra_{}_{}localdram_{}_netlat_120_bw_scalefactor_{}_verification_series".format(
                        application_name.lower(),
                        ""
                        if ligra_input_selection == "regular_input"
                        else ligra_input_selection + "_",
                        localdram_size_str,
                        bw_scalefactor,
                    ),
                    command_str=command_str,
                    experiment_run_configs=queue_delay_cap_configs,
                    output_root_directory=".",
                )
            )

    # experiments.extend(bcsstk32_bw_verification_experiments)
    # experiments.extend(bfs_bw_verification_experiments)
    # experiments.extend(bfs_small_bw_experiments)

    # Partition queue series, 6 runs per series
    # Darknet tiny, partition queue series, net_lat = 120 (default)
    # TODO: find out a good localdram_size to use
    darknet_tiny_pq_experiments = []
    model_type = "tiny"
    for num_MB in [16]:  # approx 50% of total memory usage in ROI
        localdram_size_str = "{}MB".format(num_MB)
        command_str = darknet_base_str_options.format(
            model_type,
            sniper_options="-g perf_model/dram/localdram_size={} -s stop-by-icount:{}".format(
                int(num_MB * ONE_MB_TO_BYTES), int(1000 * ONE_MILLION)
            ),
        )
        # 1 billion instructions cap

        darknet_tiny_pq_experiments.append(
            Experiment(
                experiment_name="darknet_{}_localdram_{}_netlat_120_partition_queue_series".format(
                    model_type.lower(),
                    localdram_size_str,
                ),
                command_str=command_str,
                experiment_run_configs=partition_queue_series_experiment_run_configs,
                output_root_directory=".",
            )
        )

    # BFS_small 1, 2, 4 MB, Partition queue series, now with net_lat = 120
    bfs_small_pq_experiments = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    for num_MB in [1, 2, 4]:
        localdram_size_str = "{}MB".format(num_MB)
        command_str = ligra_base_str_options.format(
            application_name,
            ligra_input_file,
            sniper_options="-g perf_model/dram/localdram_size={}".format(
                int(num_MB * ONE_MB_TO_BYTES)
            ),
        )

        bfs_small_pq_experiments.append(
            Experiment(
                experiment_name="ligra_{}_{}localdram_{}_netlat_120_partition_queue_series".format(
                    application_name.lower(),
                    ""
                    if ligra_input_selection == "regular_input"
                    else ligra_input_selection + "_",
                    localdram_size_str,
                ),
                command_str=command_str,
                experiment_run_configs=partition_queue_series_experiment_run_configs,
                output_root_directory=".",
            )
        )

    # BFS_small, cacheline queue ratio series, net_lat = 120
    bfs_small_cacheline_ratio_experiments = []
    ligra_input_selection = "small_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    for num_MB in [1, 2, 4]:
        localdram_size_str = "{}MB".format(num_MB)
        command_str = ligra_base_str_options.format(
            application_name,
            ligra_input_file,
            sniper_options="-g perf_model/dram/localdram_size={}".format(
                int(num_MB * ONE_MB_TO_BYTES)
            ),
        )

        bfs_small_cacheline_ratio_experiments.append(
            Experiment(
                experiment_name="ligra_bfs_{}localdram_{}_netlat_120_cacheline_ratio_series".format(
                    ""
                    if ligra_input_selection == "regular_input"
                    else ligra_input_selection + "_",
                    localdram_size_str,
                ),
                command_str=command_str,
                experiment_run_configs=generate_one_varying_param_experiment_run_configs(
                    "perf_model/dram",
                    "remote_cacheline_queue_fraction",
                    ["0.4", "0.3", "0.2", "0.1"],
                ),
                output_root_directory=".",
            )
        )

    # BFS 43, 22 MB, Partition queue series
    bfs_pq_experiments = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "BFS"
    for num_MB in [43, 22]:  # approx 50% and 25% of total memory usage in ROI
        localdram_size_str = "{}MB".format(num_MB)
        command_str = ligra_base_str_options.format(
            application_name,
            ligra_input_file,
            sniper_options="-g perf_model/dram/localdram_size={} -s stop-by-icount:{}".format(
                int(num_MB * ONE_MB_TO_BYTES), int(1000 * ONE_MILLION)
            ),
        )
        # BFS only has 220M instructions, so won't be limited by the 1 billion instructions cap

        bfs_pq_experiments.append(
            Experiment(
                experiment_name="ligra_{}_{}localdram_{}_partition_queue_series".format(
                    application_name.lower(),
                    ""
                    if ligra_input_selection == "regular_input"
                    else ligra_input_selection + "_",
                    localdram_size_str,
                ),
                command_str=command_str,
                experiment_run_configs=partition_queue_series_experiment_run_configs,
                output_root_directory=".",
            )
        )

    # PageRank 36, 18 MB, Partition queue series
    page_rank_pq_experiments = []
    ligra_input_selection = "regular_input"  # "regular_input" OR "small_input"
    ligra_input_file = ligra_input_to_file[ligra_input_selection]
    application_name = "PageRank"
    for num_MB in [36, 18]:  # approx 50% and 25% of total memory usage in ROI
        localdram_size_str = "{}MB".format(num_MB)
        command_str = ligra_base_str_options.format(
            application_name,
            ligra_input_file,
            sniper_options="-g perf_model/dram/localdram_size={} -s stop-by-icount:{}".format(
                int(num_MB * ONE_MB_TO_BYTES), int(1000 * ONE_MILLION)
            ),
        )
        # Cap Pagerank at 1 Billion instructions

        page_rank_pq_experiments.append(
            Experiment(
                experiment_name="ligra_{}_{}localdram_{}_partition_queue_series".format(
                    application_name.lower(),
                    ""
                    if ligra_input_selection == "regular_input"
                    else ligra_input_selection + "_",
                    localdram_size_str,
                ),
                command_str=command_str,
                experiment_run_configs=partition_queue_series_experiment_run_configs,
                output_root_directory=".",
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
        #         output_root_directory=".",
        #     )
        # )

    # experiments.extend(bfs_small_pq_experiments)
    # experiments.extend(bfs_small_cacheline_ratio_experiments)
    # experiments.extend(bfs_pq_experiments)
    # experiments.extend(page_rank_pq_experiments)

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
    #             output_root_directory=".",
    #         ),
    #         Experiment(
    #             experiment_name=command_selection + "_remote_bw_scalefactor",
    #             command_str=command_strs[command_selection],
    #             experiment_run_configs=generate_one_varying_param_experiment_run_configs(
    #                 config_param_category="perf_model/dram",
    #                 config_param_name="remote_mem_bw_scalefactor",
    #                 config_param_values=[1, 2, 4, 8, 16, 32, 64, 128],
    #             ),
    #             output_root_directory=".",
    #         ),
    #         Experiment(
    #             experiment_name=command_selection + "_localdram_size",
    #             command_str=command_strs[command_selection],
    #             experiment_run_configs=generate_one_varying_param_experiment_run_configs(
    #                 config_param_category="perf_model/dram",
    #                 config_param_name="localdram_size",
    #                 config_param_values=[4096, 16384, 65536, 262144, 524288, 1048576],
    #             ),
    #             output_root_directory=".",
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
    #         output_root_directory=".",
    #     ),
    #     Experiment(
    #         experiment_name="bcsstk05_remote_bw_scalefactor",
    #         command_str=command_str,
    #         experiment_run_configs=generate_one_varying_param_experiment_run_configs(
    #             config_param_category="perf_model/dram",
    #             config_param_name="remote_mem_bw_scalefactor",
    #             config_param_values=[1, 2, 4, 8, 16, 32, 64, 128],
    #         ),
    #         output_root_directory=".",
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
    #         output_root_directory=".",
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

        # for experiment in experiments:
        #     try:
        #         # Run experiment
        #         log_str = "Starting experiment {} at {}".format(
        #             experiment.experiment_name, datetime.datetime.now().astimezone()
        #         )
        #         print(log_str)
        #         print(log_str, file=log_file)
        #         experiment.run_and_graph()
        #     except Exception as e:
        #         # Print exception traceback to both stdout and log file
        #         err_str = "Error occurred while running experiment '{}':".format(
        #             experiment.experiment_name
        #         )
        #         print(err_str)
        #         traceback.print_exc()
        #         print(err_str, file=log_file)
        #         traceback.print_exc(file=log_file)

        experiment_manager = ExperimentManager(
            output_root_directory=".", max_concurrent_processes=17, log_file=log_file
        )
        experiment_manager.add_experiments(experiments)
        experiment_manager.start()

        experiment_manager2 = ExperimentManager(
            output_root_directory=".", max_concurrent_processes=4, log_file=log_file
        )
        experiment_manager2.add_experiments(
            darknet_darknet19_pq_experiments + darknet_resnet50_pq_experiments
        )
        experiment_manager2.start()

        log_str = "Script end time: {}".format(datetime.datetime.now().astimezone())
        print(log_str)
        print(log_str, file=log_file)
