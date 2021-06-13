# Python 3 file
import sys
import os
import time
import subprocess
import getopt
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from typing import Any, Callable, List, Optional, TextIO, TypeVar

PathLike = TypeVar("PathLike", str, bytes, os.PathLike)  # Type for file/directory paths


class StatSetting:
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


def get_stats_from_files(
    output_directory_path: PathLike,
    config_param_category: str,
    config_param_name: str,
    log_file: Optional[TextIO] = None,
    stat_settings: Optional[List[StatSetting]] = None,
):
    ipc_line_no = 3  # Indexing start from 0, not 1
    # Can add check for config_param_category, for param names that exist in multiple categories
    config_line_beginning = config_param_name + " = "
    if stat_settings is None:  # Use stat_settings defined here
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

    x_value_line_no = None
    config_param_values = []

    if not os.path.isdir(output_directory_path):
        raise NotADirectoryError(
            "Directory could not be found".format(output_directory_path)
        )

    first_file = True
    file_num = 1
    out_file_path = os.path.join(output_directory_path, "{}_sim.out".format(file_num))
    # Read all the output files, starting from 1 and going up
    while os.path.isfile(out_file_path):
        with open(out_file_path, "r") as out_file:
            out_file_lines = out_file.readlines()
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
                    raise ValueError("\n".join(error_strs))
            else:
                # Read the lines of pertinant information
                for index in range(len(y_values)):
                    line = out_file_lines[y_value_line_nos[index]]
                    y_values[index].append(
                        stat_settings[index].format_func(line.split()[-1])
                        if line.split()[-1] != "|"
                        else np.nan
                    )  # The last entry of the line

        # Associated sim.cfg file
        with open(
            os.path.join(output_directory_path, "{}_sim.cfg".format(file_num)), "r"
        ) as config_file:
            if first_file:
                for line_no, line in enumerate(config_file.readlines()):
                    if line.startswith(config_line_beginning):
                        x_value_line_no = line_no
                        # The entry after the equals sign
                        config_param_values.append(float(line.split()[2]))
                if x_value_line_no is None:
                    raise ValueError(
                        "Error: didn't find desired line starting with '{}' in .cfg file".format(
                            config_line_beginning
                        )
                    )
            else:
                line = config_file.readlines()[x_value_line_no]
                # The entry after the equals sign
                config_param_values.append(float(line.split()[2]))
        first_file = False
        file_num += 1
        out_file_path = os.path.join(
            output_directory_path, "{}_sim.out".format(file_num)
        )

    return config_param_values, y_values, stat_settings


def print_stats(
    output_directory_path: PathLike,
    config_param_name: str,
    config_param_values: str,
    y_values: List[List[Any]],
    stat_settings: List[StatSetting],
    log_file: Optional[TextIO] = None,
):
    print("X values ({}):\n".format(config_param_name), config_param_values)
    print("Y values:")
    for i, y_value_list in enumerate(y_values):
        print("{}: {}".format(stat_settings[i].name_for_legend, y_value_list))

    if log_file:  # Also print to log file
        print("X values ({}):\n".format(config_param_name), config_param_values)
        print("Y values:", file=log_file)
        for i, y_value_list in enumerate(y_values):
            print(
                "{}: {}".format(stat_settings[i].name_for_legend, y_value_list),
                file=log_file,
            )


def save_graph(
    output_directory_path: PathLike,
    config_param_name: str,
    config_param_values: str,
    y_values: List[List[Any]],
    stat_settings: List[StatSetting],
    log_file: Optional[TextIO] = None,
):
    plt.clf()
    # Plot as graph
    line_style_list = [".--r", ".--g", ".--b", ".--c", ".--m", ".--y"]
    if len(line_style_list) < len(y_values):
        line_style_list.extend(
            [".--r" for _ in range(len(y_values) - len(line_style_list))]
        )  # Extend list
    elif len(line_style_list) > len(y_values):
        line_style_list = line_style_list[: len(y_values)]  # Truncate list

    # for i, (y_value_list, line_style) in enumerate(zip(y_values, line_style_list)):
    #     plt.plot(
    #         x_axis, y_value_list, line_style, label=stat_settings[i].name_for_legend
    #     )
    # Temporarily: only plot IPC in the graph
    plt.plot(
        config_param_values, y_values[0], ".--r", label=stat_settings[0].name_for_legend
    )
    y_axis_top = 0.55
    if max(y_values[0]) > y_axis_top:
        y_axis_top = max(y_values[0])
    plt.ylim(bottom=0, top=y_axis_top)
    plt.yticks(
        np.arange(0, y_axis_top + 0.01, step=0.05)
    )  # +0.01 to include y_axis_top

    title_str = "IPC vs Stats"
    plt.title(title_str)
    plt.xlabel("{}".format(config_param_name))
    plt.ylabel("Stats")
    # plt.axvline(x=70000000)  # For local DRAM size graph
    plt.legend()
    # Note: .png files are deleted by 'make clean' in the test/shared Makefile in the original repo
    graph_filename = "{}.png".format(title_str)
    plt.savefig(os.path.join(output_directory_path, graph_filename))
    # plt.show()


def run_from_experiment(
    output_directory_path: PathLike, log_file: Optional[TextIO] = None
):
    # in this case, the two functions are the same
    run_from_cmdline(output_directory_path, log_file)


def run_from_cmdline(
    output_directory_path: PathLike,
    config_param_category: str,
    config_param_name: str,
    log_file: Optional[TextIO] = None,
    stat_settings: Optional[List[StatSetting]] = None,
    graph_stats: bool = False,
):
    x_axis, y_values, returned_stat_settings = get_stats_from_files(
        output_directory_path,
        config_param_category,
        config_param_name,
        log_file,
        stat_settings,
    )

    print_stats(
        output_directory_path,
        config_param_name,
        x_axis,
        y_values,
        returned_stat_settings,
        log_file,
    )
    if graph_stats:
        save_graph(
            output_directory_path,
            config_param_name,
            x_axis,
            y_values,
            returned_stat_settings,
            log_file,
        )


def run_from_cmdline_cacheline_queue_ratio(output_directory_path: PathLike):
    stat_settings = [
        StatSetting("IPC", float),
        #  StatSetting("Idle time (%)", lambda s: float(s.strip("%"))),
        StatSetting(
            "remote dram avg access latency",
            float,
            name_for_legend="remote dram avg access latency (ns)",
        ),
        StatSetting(
            "remote datamovement queue model avg access latency",
            float,
            name_for_legend="page queue avg access latency (ns)",
        ),
        StatSetting(
            "remote datamovement2 queue model avg access latency",
            float,
            name_for_legend="cacheline queue avg access latency (ns)",
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
        StatSetting("num data moves", int, name_for_legend="num page moves"),
        StatSetting("num inflight hits", int, name_for_legend="num inflight hits"),
        # StatSetting("num redundant moves", int, name_for_legend="num redundant moves total"),
        StatSetting(
            "num redundant moves total",
            int,
            name_for_legend="num redundant moves total",
        ),
        StatSetting(
            "num redundant moves temp1",
            int,
            name_for_legend="num redundant moves temp1",
        ),
        StatSetting(
            "num temp1 cache slower than page",
            int,
            name_for_legend="num temp1 cache slower than page",
        ),
        StatSetting(
            "num redundant moves temp2",
            int,
            name_for_legend="num redundant moves temp2",
        ),
        StatSetting(
            "PQ=1 temp1 time savings (ns)",
            float,
            name_for_legend="PQ=1 temp1 approx latency savings (ns)",
        ),
        StatSetting(
            "PQ=1 temp2 time savings (ns)",
            float,
            name_for_legend="PQ=1 temp2 approx latency savings (ns)",
        ),
        StatSetting(
            "num local evictions",
            lambda s: int(s) / 1000,
            name_for_legend="local evictions (1000s)",
        ),
    ]
    run_from_cmdline(
        output_directory_path,
        "perf_model/dram",
        "remote_cacheline_queue_fraction",
        stat_settings=stat_settings,
        graph_stats=True,
    )


def check_config(
    output_directory_path: PathLike,
    # config_param_category: str,
    config_param_name: str,
):
    ipc_line_no = 3  # Indexing start from 0, not 1
    # Can add check for config_param_category, for param names that exist in multiple categories
    config_line_beginning = config_param_name + " = "

    x_value_line_no = None
    config_param_values = []

    if not os.path.isdir(output_directory_path):
        raise NotADirectoryError(
            "Directory could not be found".format(output_directory_path)
        )

    first_file = True
    file_num = 1
    out_file_path = os.path.join(output_directory_path, "{}_sim.cfg".format(file_num))
    # Read all the output files, starting from 1 and going up
    while os.path.isfile(out_file_path):
        # sim.cfg file
        with open(
            os.path.join(output_directory_path, "{}_sim.cfg".format(file_num)), "r"
        ) as config_file:
            if first_file:
                for line_no, line in enumerate(config_file.readlines()):
                    if line.startswith(config_line_beginning):
                        x_value_line_no = line_no
                        # The entry after the equals sign
                        config_param_values.append(float(line.split()[2]))
                if x_value_line_no is None:
                    raise ValueError(
                        "Error: didn't find desired line starting with '{}' in .cfg file".format(
                            config_line_beginning
                        )
                    )
            else:
                line = config_file.readlines()[x_value_line_no]
                if not line.startswith(config_line_beginning):
                    raise ValueError(
                        "Error: didn't find desired line starting with '{}' in .cfg file {}".format(
                            config_line_beginning, out_file_path
                        )
                    )
                # The entry after the equals sign
                config_param_values.append(float(line.split()[2]))
        first_file = False
        file_num += 1
        out_file_path = os.path.join(
            output_directory_path, "{}_sim.cfg".format(file_num)
        )
    print("Config {} values:\n".format(config_param_name), config_param_values)


if __name__ == "__main__":
    type = None
    usage_str = "Usage: python3 print_stats.py -t <type of experiment>"
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ht:", ["type="])
    except getopt.GetoptError:
        print(usage_str)
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print(usage_str)
            sys.exit()
        elif opt in ("-t", "--type"):
            type = arg

    if type is None:
        print(usage_str)
        sys.exit(2)
    elif type == "cacheline_ratio":
        run_from_cmdline_cacheline_queue_ratio(".")
    elif type == "print_only":
        directory_path = "."  # current directory of the calling terminal
        check_config(directory_path, "localdram_size")
        check_config(directory_path, "remote_mem_add_lat")
        check_config(directory_path, "remote_mem_bw_scalefactor")
        check_config(directory_path, "remote_partitioned_queues")
        check_config(directory_path, "remote_cacheline_queue_fraction")
