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

from typing import Any, Callable, List, TypeVar

PathLike = TypeVar("PathLike", str, bytes, os.PathLike)  # Type for file/directory paths


# Plots graph based on files in output_directory
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
# print(sys.path)


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


def run_from_experiment(
    output_directory_path: PathLike,
    config_param_category: str,
    config_param_name: str,
    config_param_values: List[Any],
):
    ipc_line_no = 3  # Indexing start from 0, not 1
    # StatSetting line_beginning's: case sensitive, not sensitive to leading whitespace
    stat_settings = [
        StatSetting("IPC", float),
        #  StatSetting("Idle time (%)", lambda s: float(s.strip("%"))),
        #  StatSetting("average dram access latency", float, name_for_legend="avg dram access latency (ns)"),
        #  StatSetting("num local evictions", lambda s: int(s) / 1000, name_for_legend="local evictions (1000s)"),
        #  StatSetting("DDR page hits", int),
        #  StatSetting("DDR page misses", int),
    ]
    y_value_line_nos = [None for _ in range(len(stat_settings))]
    y_values = [[] for _ in range(len(stat_settings))]

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
                            # The last entry of the line
                            y_values[index].append(
                                stat_setting.format_func(line.split()[-1] if line.split()[-1] != "|" else np.nan)
                            )
                if (
                    not out_file_lines[ipc_line_no].strip().startswith("IPC")
                    or None in y_value_line_nos
                ):
                    print("Error: didn't find desired line in .out file")
                    sys.exit(-1)
                first_file = False
            else:
                # Read the lines of pertinant information
                for index in range(len(y_values)):
                    line = out_file_lines[y_value_line_nos[index]]
                    # The last entry of the line
                    y_values[index].append(
                        stat_settings[index].format_func(line.split()[-1] if line.split()[-1] != "|" else np.nan)
                    )

            # config_filename = "{}_sim.cfg".format(file_num)
            file_num += 1
            out_file_path = os.path.join(
                output_directory_path, "{}_sim.out".format(file_num)
            )

    save_graph(
        output_directory_path,
        config_param_name,
        config_param_values,
        y_values,
        stat_settings,
    )


def run_from_cmdline(
    output_directory_path: PathLike, config_param_category: str, config_param_name: str
):
    ipc_line_no = 3  # Indexing start from 0, not 1
    # Can add check for config_param_category, for param names that exist in multiple categories
    config_line_beginning = config_param_name + " = "
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
                                stat_setting.format_func(line.split()[-1] if line.split()[-1] != "|" else np.nan)
                            )  # The last entry of the line
                if (
                    not out_file_lines[ipc_line_no].strip().startswith("IPC")
                    or None in y_value_line_nos
                ):
                    print("Error: didn't find desired line in .out file")
                    sys.exit(-1)
            else:
                # Read the lines of pertinant information
                for index in range(len(y_values)):
                    line = out_file_lines[y_value_line_nos[index]]
                    y_values[index].append(
                        stat_settings[index].format_func(line.split()[-1] if line.split()[-1] != "|" else np.nan)
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
                    print(
                        "Error: didn't find desired line starting with '{}' in .cfg file".format(
                            config_line_beginning
                        )
                    )
                    sys.exit(-1)
            else:
                line = config_file.readlines()[x_value_line_no]
                # The entry after the equals sign
                config_param_values.append(float(line.split()[2]))
        first_file = False
        file_num += 1
        out_file_path = os.path.join(
            output_directory_path, "{}_sim.out".format(file_num)
        )

    save_graph(
        output_directory_path,
        config_param_name,
        config_param_values,
        y_values,
        stat_settings,
    )


def save_graph(
    output_directory_path: PathLike,
    config_param_name: str,
    config_param_values: str,
    y_values: List[List[Any]],
    stat_settings: List[StatSetting],
):
    plt.clf()
    # Plot graph
    print("X values:\n", config_param_values)
    print("Y values:")
    for i, y_value_list in enumerate(y_values):
        print("{}: {}".format(stat_settings[i].name_for_legend, y_value_list))

    # Plot as graph
    line_style_list = [".--r", ".--g", ".--b", ".--c", ".--m", ".--y"]
    if len(line_style_list) < len(y_values):
        line_style_list.extend(
            [".--r" for _ in range(len(y_values) - len(line_style_list))]
        )  # Extend list
    elif len(line_style_list) > len(y_values):
        line_style_list = line_style_list[: len(y_values)]  # Truncate list

    for i, (y_value_list, line_style) in enumerate(zip(y_values, line_style_list)):
        plt.plot(
            config_param_values,
            y_value_list,
            line_style,
            label=stat_settings[i].name_for_legend,
        )
    # title_str = "IPC vs Remote Memory Additional Latency"
    # title_str = "IPC vs Remote Memory Bandwidth"
    # title_str = "IPC vs Local DRAM Size"
    title_str = "Stats vs {}".format(config_param_name)
    plt.title(title_str)
    # plt.xlabel("Remote Memory Additional Latency (ns)")
    # plt.xlabel("Remote Memory Bandwidth Scale Factor")
    # plt.xlabel("Local DRAM Size (B)")
    plt.xlabel("{}".format(config_param_name))
    plt.ylabel("Stats")
    # plt.axvline(x=70000000)  # For local DRAM size graph
    plt.legend()
    # Note: .png files are deleted by 'make clean' in the test/shared Makefile in the original repo
    # graph_filename = "{}-{}.png".format(output_directory_path, title_str)
    graph_filename = "{}.png".format(title_str)
    plt.savefig(os.path.join(output_directory_path, graph_filename))
    # plt.show()


if __name__ == "__main__":
    output_directory_path = None
    config_param_category = None
    config_param_name = None

    usage_str = "Usage: python3 plot_graph.py -d <directory of experiment results> -c <config parameter category> -n <config parameter name>"
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "hd:c:n:", ["directory=", "category=", "name="]
        )
    except getopt.GetoptError:
        print(usage_str)
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print(usage_str)
            sys.exit()
        elif opt in ("-d", "--directory"):
            output_directory_path = arg
        elif opt in ("-c", "--category"):
            if arg[0] == "[" and arg[-1] == "]":
                arg = arg[1:-1]  # Strip enclosing square brackets
            config_param_category = arg
        elif opt in ("-n", "--name"):
            config_param_name = arg

    if None in (output_directory_path, config_param_category, config_param_name):
        print(usage_str)
        sys.exit(2)

    run_from_cmdline(output_directory_path, config_param_category, config_param_name)
