# Python 3
from __future__ import annotations
import sys
import os
import stat
import time
import datetime
import traceback
import copy
import getopt
import shutil
import subprocess
from collections import deque

import typing
from typing import Callable, Dict, List, Iterable, Optional, TextIO, Union, TypeVar

PathLike = TypeVar("PathLike", str, bytes, os.PathLike)  # Type for file/directory paths

this_file_containing_dir_abspath = os.path.dirname(os.path.abspath(__file__))

# # If scripts in the Sniper tools folder need to be called
# sys.path.append(os.path.join(this_file_containing_dir_abspath, "..", "tools"))

# # Add root Sniper directory to path
# sys.path.insert(0, os.path.join(this_file_containing_dir_abspath, ".."))
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
        # No recursive data structures, so we can ignore the memo argument
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
            != self.config_tree[config_entry.category][config_entry.name]
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

    def replace_config_entry(self, config_entry: ConfigEntry):
        """Add a ConfigEntry to this collection. If config_entry conflicts
        with an existing entry in the ExperimentRunConfig, ie it
        has the same category and name yet have a different value
        than a ConfigEntry that is already in this collection, the new one
        replaces the old one.
        """
        if config_entry.category not in self.config_tree:
            self.config_tree[config_entry.category] = {}
        self.config_tree[config_entry.category][config_entry.name] = config_entry.value

    def replace_config_entries(self, config_entries: Iterable[ConfigEntry]) -> None:
        """Add the specified ConfigEntry's to this collection. Any entries that
        conflict with existing entries or other entries in config_entries will
        replace any older entries.
        """
        for config_entry in config_entries:
            self.replace_config_entry(config_entry)

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
        start_experiment_no: int = 1,
        setup_command_str: Optional[str] = None,
        clean_up_command_str: Optional[str] = None,
        post_experiment_processing_function: Optional[Callable[[str], None]] = None,
    ):
        """Optional parameter post_experiment_processing_function should be a
        callable taking three arguments:
          1) the absolute path of the experiment output directory
          2) the starting experiment number
          3) an opened log file
        """
        self.experiment_name = experiment_name
        self.command_str = command_str
        self.experiment_run_configs = experiment_run_configs
        self.output_root_directory = output_root_directory
        self.start_experiment_no = start_experiment_no
        self.setup_command_str = setup_command_str
        self.clean_up_command_str = clean_up_command_str
        self.post_experiment_processing_function = post_experiment_processing_function
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
                experiment_no + self.start_experiment_no,
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
            if self.post_experiment_processing_function is not None:
                # # Provide extra context to console output
                # print("Experiment {}:".format(self.experiment_name))

                # Custom post experiment processing function, eg plotting a graph
                self.post_experiment_processing_function(
                    self._experiment_output_dir_abspath,
                    self.start_experiment_no,
                    log_file,
                )


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

    def start(self, manager_sleep_interval_seconds: int = 60, timezone: Optional[datetime.tzinfo] = None) -> None:
        """Start running Experiment's added to this ExperimentManager."""
        os.chdir(self.output_directory_abspath)
        process_info = [
            ExperimentManager.ProcessInfo()
            for _ in range(self.max_concurrent_processes)
        ]

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
                                .format(sniper_output_dir=os.path.abspath("."))  # sniper_output_dir should be an absolute path
                            )
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
                            datetime.datetime.now().astimezone(timezone),
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
                                datetime.datetime.now().astimezone(timezone),
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

                            time.sleep(5)  # give a bit of time for things to settle in

                # Process experiments that have all runs completed
                i = 0
                while i < len(self._running_experiments):
                    if self._running_experiments[i].experiment_done():
                        try:
                            self._running_experiments[i].post_experiment_processing()
                        except Exception as e:
                            log_str = "Error occurred while running post experiment processing for experiment '{}':".format(
                                self._running_experiments[i].experiment_name
                            )
                            print(log_str)
                            print(log_str, file=self.log_file)
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
                    time.sleep(manager_sleep_interval_seconds)

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
