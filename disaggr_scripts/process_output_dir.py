# Copy and rename output files (for when the test scripts don't copy the files)
# Optionally call plot graph functions

import os
import numpy as np
import natsort
import shutil
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import interpolate

from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, TextIO, TypeVar

PathLike = TypeVar("PathLike", str, bytes, os.PathLike)  # Type for file/directory paths

# import plot_graph
# import plot_graph_pq

class StatSetting:
    """Specify information for a Sniper statistic, to find the value from
    output files and graph it.
    """
    def __init__(
        self,
        line_beginning: str,
        format_func: Callable[[str], Any],
        name_for_legend: str = None,
    ):
        self.line_beginning = line_beginning
        self.format_func = format_func  # Function to format value read from text file
        if name_for_legend is None:
            name_for_legend = line_beginning
        self.name_for_legend = name_for_legend


class BandwidthInfo:
    """Collect information about the effective bandwidth for a Sniper run."""
    percentiles: List[str]
    page_queue_effective_bw_percentiles: Dict[str, float]
    cacheline_queue_effective_bw_percentiles: Dict[str, float]
    page_queue_max_effective_bw: float
    cacheline_queue_max_effective_bw: float

    # percentiles to extract from the log file
    percentiles = ["0.975", "0.95"]
    # percentiles = ['0', '0.025', '0.05', '0.075', '0.1', '0.125', '0.15', '0.175', '0.2', '0.225', '0.25', '0.275', '0.3', '0.325', '0.35', '0.375', '0.4', '0.425', '0.45', '0.475', '0.5', '0.525', '0.55', '0.575', '0.6', '0.625', '0.65', '0.675', '0.7', '0.725', '0.75', '0.775', '0.8', '0.825', '0.85', '0.875', '0.9', '0.925', '0.95', '0.975']

    def __init__(self):
        self.page_queue_max_effective_bw = None
        self.cacheline_queue_max_effective_bw = None
        self.page_queue_effective_bw_percentiles = {}
        self.cacheline_queue_effective_bw_percentiles = {}

        for percentage_str in self.percentiles:
            self.page_queue_effective_bw_percentiles[percentage_str] = None
            self.cacheline_queue_effective_bw_percentiles[percentage_str] = None

    def __str__(self):
        lines = []
        lines.append(
            "BandwidthInfo() object: page_queue_max_effective_bw={}".format(
                self.page_queue_max_effective_bw
            )
        )
        lines.append(
            "cacheline_queue_max_effective_bw={}".format(
                self.cacheline_queue_max_effective_bw
            )
        )
        lines.append(
            "page_queue_effective_bw_percentiles={}".format(
                str(self.page_queue_effective_bw_percentiles)
            )
        )
        lines.append(
            "cacheline_queue_effective_bw_percentiles={}".format(
                str(self.cacheline_queue_effective_bw_percentiles)
            )
        )
        lines.append("")  # to add a trailing newline
        return "\n".join(lines)

    def __repr__(self):
        return self.__str__()


def get_stats_from_files(
    output_directory_path: PathLike,
    first_experiment_no: Optional[int] = 1,
    log_file: Optional[TextIO] = None,
    stat_settings: Optional[List[StatSetting]] = None,
):
    """Run this script in an experiment folder, ie the containing folder of
    numbered Sniper config and output files.
    """
    ipc_line_no = 3  # Indexing start from 0, not 1
    if stat_settings is None:
        # Use stat_settings defined here
        # StatSetting line_beginning's: case sensitive, not sensitive to leading whitespace
        stat_settings = [
            StatSetting("IPC", float),
            #  StatSetting("Idle time (%)", lambda s: float(s.strip("%"))),
            #  StatSetting("remote dram avg access latency", float, name_for_legend="remote dram avg access latency (ns)"),
            #  StatSetting("local dram avg access latency", float, name_for_legend="local dram avg access latency (ns)"),
            #  StatSetting("average dram access latency", float, name_for_legend="avg dram access latency (ns)"),
            #  StatSetting("num local evictions", lambda s: int(s) / 1000, name_for_legend="local evictions (1000s)"),
            #  StatSetting("DDR page hits", int),
            #  StatSetting("DDR page misses", int),
        ]

    y_value_line_nos = [None for _ in range(len(stat_settings))]
    y_values = [[] for _ in range(len(stat_settings))]

    if not os.path.isdir(output_directory_path):
        raise NotADirectoryError(
            "Directory could not be found".format(output_directory_path)
        )

    first_file = True
    file_num = first_experiment_no
    out_file_path = os.path.join(output_directory_path, "{}_sim.out".format(file_num))
    # Read all the output files, starting from 1 and going up
    while os.path.isfile(out_file_path):
        with open(out_file_path, "r") as out_file:
            out_file_lines = out_file.readlines()
            if len(out_file_lines) == 0:
                # The file is empty...
                print("{} is an empty file!".format(out_file_path))
                for index in range(len(y_values)):
                    y_values[index].append(np.nan)
                file_num += 1
                out_file_path = os.path.join(
                    output_directory_path, "{}_sim.out".format(file_num)
                )
                continue
            if first_file:
                # Get line numbers of relevant lines
                for line_no, line in enumerate(out_file_lines):
                    for index, stat_setting in enumerate(stat_settings):
                        if line.strip().startswith(stat_setting.line_beginning):
                            y_value_line_nos[index] = line_no
                            y_values[index].append(
                                stat_setting.format_func(line.split()[-1])
                                if line.split()[-1] != "|"
                                else np.nan
                            )  # The last entry of the line
                if not out_file_lines[ipc_line_no].strip().startswith("IPC"):
                    raise ValueError(
                        "Error: didn't find desired line starting with '{}' in .out file".format(
                            "IPC"
                        )
                    )
                elif None in y_value_line_nos:
                    error_strs = []
                    for index, value in enumerate(y_value_line_nos):
                        if value is None:
                            error_strs.append(
                                "Error: didn't find desired line starting with '{}' in .out file".format(
                                    stat_settings[index].line_beginning
                                )
                            )
                        y_values[index].append(np.nan)  # ignore missing stats
                    # raise ValueError("\n".join(error_strs))
                    print("\n".join(error_strs))
            else:
                # Read the lines of pertinant information
                for index in range(len(y_values)):
                    if y_value_line_nos[index] is None \
                            or not out_file_lines[y_value_line_nos[index]].strip().startswith(stat_settings[index].line_beginning):
                        # Couldn't find the line where it was in the previous file, try looking again for the line in this file
                        y_value_line_nos[index] = None
                        for line_no, line in enumerate(out_file_lines):
                            if line.strip().startswith(stat_settings[index].line_beginning):
                                y_value_line_nos[index] = line_no  # found it
                                break
                    if y_value_line_nos[index] is None:  # Still didn't find the line
                        y_values[index].append(np.nan)  # ignore missing stats
                        continue
                    line = out_file_lines[y_value_line_nos[index]]
                    y_values[index].append(
                        stat_settings[index].format_func(line.split()[-1])
                        if line.split()[-1] != "|"
                        else np.nan
                    )  # The last entry of the line

        first_file = False
        file_num += 1
        out_file_path = os.path.join(
            output_directory_path, "{}_sim.out".format(file_num)
        )

    return y_values, stat_settings


def get_list_padded_str(l: List[Any], col_min_width: Optional[int] = 7):
    format_str = "{{:>{col_min_width}}}".format(col_min_width=col_min_width)
    elements = [format_str.format(val) for val in l]
    return "[" + ", ".join(elements) + "]"


def print_stats(
    output_directory_path: PathLike,
    y_values: List[List[Any]],
    stat_settings: List[StatSetting],
    log_file: Optional[TextIO] = None,
    print_to_terminal: Optional[bool] = True
):
    if print_to_terminal:
        print("Y values:")
        for i, y_value_list in enumerate(y_values):
            print("{:45}: {}".format(stat_settings[i].name_for_legend, get_list_padded_str(y_value_list)))

    if log_file:  # Also print to log file
        print("Y values:", file=log_file)
        for i, y_value_list in enumerate(y_values):
            print(
                "{:45}: {}".format(stat_settings[i].name_for_legend, get_list_padded_str(y_value_list)),
                file=log_file,
            )


def get_and_print_stats(
    output_directory_path: PathLike,
    log_file: Optional[TextIO] = None,
    stat_settings: Optional[List[StatSetting]] = None,
    print_to_terminal: bool = True,
    first_experiment_no: int = 1,
):
    """Run this script in an experiment folder, ie the containing folder of
    numbered Sniper config and output files.
    """
    y_values, returned_stat_settings = get_stats_from_files(
        output_directory_path,
        log_file=log_file,
        stat_settings=stat_settings,
        first_experiment_no=first_experiment_no
    )

    print_stats(
        output_directory_path,
        y_values,
        returned_stat_settings,
        log_file=log_file,
        print_to_terminal=print_to_terminal
    )


def custom_graphing_function(
    dir_path: PathLike, log_file: Optional[TextIO] = None
) -> bool:
    """Graph the experiment folder """
    dirname = os.path.basename(os.path.normpath(dir_path))
    if "some_experiment_series_name" in dirname:
        # Do something
        return True  # graphing success
    else:
        # Unknown series type
        print("\n\nUnknown series type for {}, cannot graph\n".format(dirname))
        return False  # did not successfully graph


def process_and_graph_experiment_series(
    output_directory_path: PathLike,
    get_output_from_temp_folders: bool = True,
    graph_experiment_folders: bool = True,
    graphing_function: Optional[Callable[[str, Optional[TextIO]], bool]] = None,
    first_experiment_no: int = 1,
):
    """Run this script in the directory containing experiment folders, ie the
    containing folder of the run.py file.
    """
    with open(os.path.join(output_directory_path, "Stats.txt"), "w") as log_file:
        passed_over_directories = []
        directories_not_graphed = []
        for filename in natsort.os_sorted(os.listdir(output_directory_path)):
            filename_path = os.path.join(output_directory_path, filename)
            if os.path.isdir(filename_path) and "output_files" in filename:
                if get_output_from_temp_folders:
                    # Copy files from temp folders into this directory
                    for sub_filename in natsort.os_sorted(os.listdir(filename_path)):
                        sub_filename_path = os.path.join(filename_path, sub_filename)
                        if (
                            os.path.isdir(sub_filename_path)
                            and sub_filename.startswith("run_")
                            and "temp" in sub_filename
                        ):
                            run_no = int(sub_filename[4:sub_filename.find("_", 4)])  # 4 is len("run_")
                            for file_to_save in ["sim.cfg", "sim.out", "sim.stats.sqlite3"]:
                                src_path = os.path.join(sub_filename_path, file_to_save)
                                dst_path = os.path.join(filename_path, "{}_".format(run_no) + file_to_save)
                                shutil.copy2(src_path, dst_path)

                # Record some stats
                # print(filename)
                print(filename, file=log_file)
                get_and_print_stats(
                    filename_path,
                    print_to_terminal=False,
                    log_file=log_file,
                    first_experiment_no=first_experiment_no,
                    stat_settings=[
                        StatSetting("IPC", float),
                        StatSetting(
                            "remote dram avg access latency",
                            float,
                            name_for_legend="remote dram avg access latency (ns)",
                        ),
                        StatSetting(
                            "remote datamovement queue model avg access latency",
                            float,
                            name_for_legend="  page queue avg access latency (ns)",
                        ),
                        StatSetting(
                            "remote datamovement2 queue model avg access latency",
                            float,
                            name_for_legend="  cacheline queue avg access latency (ns)",
                        ),
                        StatSetting(
                            "local dram avg access latency",
                            float,
                            name_for_legend="local dram avg access latency (ns)",
                        ),
                        StatSetting(
                            "average dram access latency",
                            float,
                            name_for_legend="avg dram access latency (ns)",
                        ),
                        StatSetting(
                            "remote datamovement % capped by window size",
                            float,
                            name_for_legend="datamovement capped by window size (%)",
                        ),
                        StatSetting(
                            "remote datamovement % queue utilization full",
                            float,
                            name_for_legend="datamovement utilization full (%)",
                        ),
                        StatSetting(
                            "remote datamovement2 % capped by window size",
                            float,
                            name_for_legend="datamovement2 capped by window size (%)",
                        ),
                        StatSetting(
                            "remote datamovement2 % queue utilization full",
                            float,
                            name_for_legend="datamovement2 utilization full (%)",
                        ),
                        StatSetting(
                            "remote page move cancelled due to full queue",
                            int,
                            name_for_legend="remote page moves cancelled due to full queue",
                        ),
                    ],
                )
                # print()
                print(file=log_file)

                if graph_experiment_folders:
                    # Generate graph
                    with open(
                        os.path.join(filename_path, filename[:filename.find("_output_files")] + " Stats.txt"),
                        "w"
                    ) as experiment_log_file:
                        # Add calls to custom graphing functions here
                        graphed = graphing_function(filename_path, experiment_log_file)
                        if not graphed:
                            directories_not_graphed.append(filename)

            elif os.path.isdir(filename_path):
                passed_over_directories.append(filename)
        if len(passed_over_directories) > 0:
            print("\nPassed over {} directories:".format(len(passed_over_directories)))
            for dirname in passed_over_directories:
                print("  {}".format(dirname))
        if len(directories_not_graphed) > 0:
            print("\nDid not graph {} directories:".format(len(directories_not_graphed)))
            for dirname in directories_not_graphed:
                print("  {}".format(dirname))


def delete_experiment_run_temp_folders(output_directory_path: PathLike):
    """Run this script in the directory containing experiment folders, ie the
    containing folder of the run.py file.
    """
    passed_over_directories = []
    for filename in natsort.os_sorted(os.listdir(output_directory_path)):
        filename_path = os.path.join(output_directory_path, filename)
        if os.path.isdir(filename_path) and "output_files" in filename:
            # Now in an experiment output folder
            deleted_temp_folders = 0

            for sub_filename in natsort.os_sorted(os.listdir(filename_path)):
                sub_filename_path = os.path.join(filename_path, sub_filename)
                if (
                    os.path.isdir(sub_filename_path)
                    and sub_filename.startswith("run_")
                    and "temp" in sub_filename
                ):
                    # Delete folder and all its contents
                    shutil.rmtree(sub_filename_path)
                    deleted_temp_folders += 1
            print("{}: deleted {} temp folders".format(filename, deleted_temp_folders))

        elif os.path.isdir(filename_path):
            passed_over_directories.append(filename)
    if len(passed_over_directories) > 0:
        print("\nPassed over {} directories:".format(len(passed_over_directories)))
        for dirname in passed_over_directories:
            print("  {}".format(dirname))


def print_remote_access_percentage(output_directory_path: PathLike):
    class StatIndex(IntEnum):
        """Specify indices of the stats_settings list, only for this function."""
        TOTAL_ACCESSES = 0
        TOTAL_READS = 1
        REMOTE_READS = 2
        TOTAL_WRITES = 3
        REMOTE_WRITES = 4
        INFLIGHT_HITS = 5

    stat_settings = [
        StatSetting("num dram accesses", int),
        StatSetting("num dram reads", int),
        StatSetting("num remote reads", int),
        StatSetting("num dram writes", int),
        StatSetting("num remote writes", int),
        StatSetting("num inflight hits", int),
    ]

    passed_over_directories = []
    for filename in natsort.os_sorted(os.listdir(output_directory_path)):
        filename_path = os.path.join(output_directory_path, filename)
        if os.path.isdir(filename_path) and "output_files" in filename:
            # Now in an experiment output folder
            # y_values, _ = get_stats_from_files(output_directory_path, stat_settings=stat_settings)

            # Only need to get the baseline pq=0, compression=off file.
            # SPECIFY THE RUN NUMBER BELOW:
            file_num = 3
            out_file_path = os.path.join(filename_path, "{}_sim.out".format(file_num))
            # Read all the output files, starting from 1 and going up
            if not os.path.isfile(out_file_path):
                passed_over_directories.append(filename)
                continue
            y_value_line_nos = [None for _ in range(len(stat_settings))]
            stat_values = [None for _ in range(len(stat_settings))]
            with open(out_file_path, "r") as out_file:
                out_file_lines = out_file.readlines()
                if len(out_file_lines) == 0:
                    # The file is empty...
                    passed_over_directories.append(filename)
                    continue
                # Get line numbers of relevant lines
                for line_no, line in enumerate(out_file_lines):
                    for index, stat_setting in enumerate(stat_settings):
                        if line.strip().startswith(stat_setting.line_beginning):
                            y_value_line_nos[index] = line_no
                            stat_values[index] = (stat_setting.format_func(line.split()[-1])
                                if line.split()[-1] != "|"
                                else np.nan
                            )  # The last entry of the line
                if None in y_value_line_nos:
                    error_strs = []
                    for index, value in enumerate(y_value_line_nos):
                        if value is None:
                            error_strs.append(
                                "Error: didn't find desired line starting with '{}' in .out file".format(
                                    stat_settings[index].line_beginning
                                )
                            )
                    # raise ValueError("\n".join(error_strs))
                    print("\n".join(error_strs))

            print(stat_values)

            remote_reads_plus_writes = stat_values[StatIndex.REMOTE_READS] + stat_values[StatIndex.REMOTE_WRITES]
            # Count an inflight hit as this amount of remote accesses, since inflight hits
            # have an access latency between remote accesses and pure local dram accesses
            inflight_hit_remote_access_fraction = 0.5
            remote_accesses_including_inflight_hits = remote_reads_plus_writes + inflight_hit_remote_access_fraction * stat_values[StatIndex.INFLIGHT_HITS]
            print("{}:".format(filename))
            print("% reads remote (out of {}), % accesses remote (out of {}), % accesses remote (inflight hits counting as 0.5)".format(
                stat_values[StatIndex.TOTAL_READS],
                stat_values[StatIndex.TOTAL_ACCESSES],
            ))
            print("{:.2f}, {:.2f}, {:.2f}".format(
                100 * stat_values[StatIndex.REMOTE_READS] / stat_values[StatIndex.TOTAL_READS],
                100 * remote_reads_plus_writes / stat_values[StatIndex.TOTAL_ACCESSES],
                100 * remote_accesses_including_inflight_hits / stat_values[StatIndex.TOTAL_ACCESSES],
            ))
            print()

    if len(passed_over_directories) > 0:
        print("\nPassed over {} directories:".format(len(passed_over_directories)))
        for dirname in passed_over_directories:
            print("  {}".format(dirname))


def print_all_remote_access_percentages(output_directory_path: PathLike):
    passed_over_directories = []
    for filename in natsort.os_sorted(os.listdir(output_directory_path)):
        filename_path = os.path.join(output_directory_path, filename)
        if not os.path.isdir(filename_path):
            continue
        if filename.startswith("experimentrun") and "test" not in filename.lower():
            print_remote_access_percentage(filename_path)
        else:
            passed_over_directories.append(filename)
    if len(passed_over_directories) > 0:
        print("\nPassed over {} directories:".format(len(passed_over_directories)))
        for dirname in passed_over_directories:
            print("  {}".format(dirname))


if __name__ == "__main__":
    output_directory_path = "."

    # process_and_graph_experiment_series(output_directory_path, get_output_from_temp_folders=True, graph_experiment_folders=True, graphing_function=custom_graphing_function)
    
    # delete_experiment_run_temp_folders(output_directory_path)

    # process_and_graph_experiment_series(output_directory_path, get_output_from_temp_folders=False, graph_experiment_folders=True, graphing_function=custom_graphing_function)

    # process_and_graph_experiment_series(output_directory_path, get_output_from_temp_folders=False, graph_experiment_folders=False)

    # print_remote_access_percentage(output_directory_path)
    print_all_remote_access_percentages(output_directory_path)
