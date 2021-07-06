# Copy and rename output files (for when stop-by-icount is used and test scripts don't copy the files)
# Optionally call plot graph functions

import os
import numpy as np
import natsort
import shutil
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import interpolate

from typing import Any, Callable, Dict, List, Optional, TextIO, TypeVar

PathLike = TypeVar("PathLike", str, bytes, os.PathLike)  # Type for file/directory paths

import plot_graph
import plot_graph_pq

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


class BandwidthInfo:
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


def extract_effective_bandwidth(log_file: TextIO):
    experiment_run_info: Dict[int, BandwidthInfo]

    line = log_file.readline()
    experiment_run_info = {}
    printed_log_file_title = False
    while line:
        if line.startswith("Experiment run"):
            experiment_run_no = int(
                (line.strip().split()[-1])[:-1]
            )  # assuming the end of the line has format of "[number]:"
            experiment_run_info[experiment_run_no] = BandwidthInfo()
            line = log_file.readline()

        elif "Queue dram-datamovement-queue:" in line:
            line2 = log_file.readline()
            if "m_max_effective_bandwidth gave" not in line2:
                print(
                    "This script ran into unexpected log file structure in {}".format(
                        log_file.name
                    )
                )
                return
            experiment_run_info[experiment_run_no].page_queue_max_effective_bw = float(
                line2.strip().split()[-2]
            )
            line = log_file.readline()
            while line.startswith("percentage:"):
                line_tokens = line.strip().split()
                percentage = line_tokens[1][:-1]  # [:-1] to remove the comma
                if percentage in BandwidthInfo.percentiles:
                    experiment_run_info[
                        experiment_run_no
                    ].page_queue_effective_bw_percentiles[percentage] = float(
                        line_tokens[-2]
                    )
                line = log_file.readline()
            # Don't read next line, so this last line can be processed the next while loop iteration

        elif "Queue dram-datamovement-queue-2:" in line:
            line2 = log_file.readline()
            if "m_max_effective_bandwidth gave" not in line2:
                print(
                    "This script ran into unexpected log file structure in {}".format(
                        log_file.name
                    )
                )
                return
            experiment_run_info[
                experiment_run_no
            ].cacheline_queue_max_effective_bw = float(line2.strip().split()[-2])
            line = log_file.readline()
            while line.startswith("percentage:"):
                line_tokens = line.strip().split()
                percentage = line_tokens[1][:-1]  # [:-1] to remove the comma
                if percentage in BandwidthInfo.percentiles:
                    experiment_run_info[
                        experiment_run_no
                    ].cacheline_queue_effective_bw_percentiles[percentage] = float(
                        line_tokens[-2]
                    )
                line = log_file.readline()
            # Don't read next line, so this last line can be processed the next while loop iteration

        elif "effective bandwidth that exceeded the allowable max bandwidth" in line:
            if not printed_log_file_title:
                print(log_file.name)
                printed_log_file_title = True
            print("Run {}: {}".format(experiment_run_no, line.strip()))
            line = log_file.readline()

        else:
            line = log_file.readline()

    if printed_log_file_title:
        print()
        
    return experiment_run_info


def plot_effective_bandwidth_grouped_bar_chart(output_directory_path: PathLike, bw_info: Dict[int, BandwidthInfo]):
    plt.clf()
    plt.close("all")

    # labels = ["pq=0\ntest_b=0", "pq=0\ntest_b=2", "pq=1\ntest_b=0", "pq=1\ntest_b=2"]
    labels = ["pq=0\n10^4\n10^4", "pq=1\n10^4\n10^4",
              "pq=0\n10^5\n10^5", "pq=1\n10^5\n10^5",
              "pq=0\n10^6\n10^6", "pq=1\n10^6\n10^6",
              "pq=0\n10^7\n10^7", "pq=1\n10^7\n10^7",
              "pq=0\n10^8\n10^8", "pq=1\n10^8\n10^8",
              "pq=0\n10^4\n10^5", "pq=1\n10^4\n10^5",
              "pq=0\n10^4\n10^6", "pq=1\n10^4\n10^6",
              "pq=0\n10^4\n10^7", "pq=1\n10^4\n10^7",
              "pq=0\n10^5\n10^6", "pq=1\n10^5\n10^6",
              "pq=0\n10^5\n10^7", "pq=1\n10^5\n10^7",]
    # percentages = ["0.975", "0.95"]  # for the test-partition-queues branch
    percentages = []  # effective bandwidth percentiles were commented out in other branches

    page_queue_bws = {}
    page_queue_bws["  100"] = []
    for percentage in percentages:
        page_queue_bws[percentage] = []

    cacheline_queue_bws = {}
    cacheline_queue_bws["  100"] = []
    for percentage in percentages:
        cacheline_queue_bws[percentage] = []

    for i in range(1, len(bw_info) + 1):
        value = bw_info[i].page_queue_max_effective_bw
        page_queue_bws["  100"].append(value if value is not None else np.nan)
        for percentage in percentages:
            value = bw_info[i].page_queue_effective_bw_percentiles[percentage]
            page_queue_bws[percentage].append(value if value is not None else np.nan)

        value = bw_info[i].cacheline_queue_max_effective_bw
        cacheline_queue_bws["  100"].append(value if value is not None else np.nan)
        for percentage in percentages:
            value = bw_info[i].cacheline_queue_effective_bw_percentiles[percentage]
            cacheline_queue_bws[percentage].append(
                value if value is not None else np.nan
            )

    # Get bw_scalefactor and compute correct bandwidth
    bw_scalefactor = 4  # This is the default
    if output_directory_path.find("bw_scalefactor_") != -1:
        start_index = output_directory_path.find("bw_scalefactor_") + len("bw_scalefactor_")
        if output_directory_path.find("_", start_index) != -1:
            end_index = output_directory_path.find("_", start_index)
        else:
            end_index = len(output_directory_path)
        bw_scalefactor = int(output_directory_path[start_index : end_index])
    correct_combined_bw = 19.2 / bw_scalefactor
    correct_half_bw = 0.5 * 19.2 / bw_scalefactor

    # bw scalefactor check
    print(output_directory_path)
    for percentage, bw_list in cacheline_queue_bws.items():
        if percentage == "0.95":  # skip this for now
            continue
        for i, bw in enumerate(bw_list):
            if np.isnan(bw):
                # Page queue only
                if not np.isnan(page_queue_bws[percentage][i]) and page_queue_bws[percentage][i] > correct_combined_bw:
                    print("Experiment run {} page queue had p{} bw of {} > {} ({:.3f}x)".format(i + 1, percentage[2:], page_queue_bws[percentage][i], correct_combined_bw, page_queue_bws[percentage][i] / correct_combined_bw))
            else:
                # Page queue & cacheline queue, assume cacheline queue fraction is 0.5
                if bw > correct_half_bw:
                    print("Experiment run {} cacheline queue had p{} bw of {} > {} ({:.3f}x)".format(i + 1, percentage[2:], bw, correct_half_bw, bw / correct_half_bw))
                if not np.isnan(page_queue_bws[percentage][i]) and page_queue_bws[percentage][i] > correct_half_bw:
                    print("Experiment run {} page queue had p{} bw of {} > {} ({:.3f}x)".format(i + 1, percentage[2:], page_queue_bws[percentage][i], correct_half_bw, page_queue_bws[percentage][i] / correct_half_bw))
    print()

    # # Debug output
    # print(bw_info)
    # for percentage in percentages:
    #     print(page_queue_bws[percentage])
    # for percentage in percentages:
    #     print(cacheline_queue_bws[percentage])

    x = np.arange(len(labels))  # the label locations
    width = 0.15  # the width of the bars
    colors = [("cornflowerblue", "darkblue"), ("lawngreen", "darkgreen"), ("plum", "purple")]

    fig, ax = plt.subplots()
    rects = {}
    cacheline_rects = {}
    for i, (percentage, (color1, color2)) in enumerate(
        zip(["  100"] + percentages, colors)
    ):
        # if np.nan in cacheline_queue_bws[percentage]:
        #     # No cacheline results
        #     rects[percentage] = ax.bar(x + i * 2 * width, page_queue_bws[percentage], 2 * width, label="p{}".format(percentage[2:]), align="edge", color=color1)
        # else:
        rects[percentage] = ax.bar(
            x + 2 * i * width,
            page_queue_bws[percentage],
            width,
            label="p{}".format(percentage[2:]),
            align="edge",
            color=color1,
        )
        cacheline_rects[percentage] = ax.bar(
            x + (2 * i + 1) * width,
            cacheline_queue_bws[percentage],
            width,
            label="p{} cacheline".format(percentage[2:]),
            align="edge",
            color=color2,
        )

    # Set title, axes, legend, etc.
    title_str = "Effective Bandwidth"
    ax.set_title("Effective Bandwidth")
    ax.set_xticks(x + width * (len(percentages + ["  100"])))
    ax.set_xticklabels(labels)
    y_axis_top = 6.0
    # data_y_max = max([max(page_queue_bws[p]) for p in percentages])
    data_y_max = max([max(page_queue_bws[p]) for p in percentages + ["  100"]])
    if data_y_max > y_axis_top:
        y_axis_top = data_y_max + max(2.0, data_y_max * 0.05)
    ax.set_ylim(bottom=0, top=y_axis_top)
    if data_y_max < 10:
        ax.set_yticks(
            np.arange(0, y_axis_top + 0.05, step=1.0)
        )  # +0.05 to include y_axis_top
    else:
        ax.set_yticks(
            np.arange(0, y_axis_top + 0.05, step=10.0)
        )  # +0.05 to include y_axis_top
    ax.set_ylabel("Effective Bandwidth (GB/s)")

    # Set lines for correct bandwidth
    # Lines for bandwidth_verification experiments with 4 runs
    # ax.axhline(y=correct_combined_bw, xmin=0, xmax=0.5, color="black")
    # ax.axhline(y=correct_half_bw, xmin=0.5, xmax=1, color="black")
    # Lines for bandwidth_verification experiments with num_runs runs
    num_runs = len(labels)
    line_len = 1 / (num_runs + 2)
    for i in range(num_runs):
        x_start = (i+1) * line_len
        x_end = x_start + line_len
        if i % 2 == 0:
            ax.axhline(y=correct_combined_bw, xmin=x_start, xmax=x_end, color="black")
        else:
            ax.axhline(y=correct_half_bw, xmin=x_start, xmax=x_end, color="black")

    ax.legend()

    # Add labels of y-values for each bar
    for percentage in (["  100"] + percentages):
        ax.bar_label(rects[percentage], padding=3, rotation="vertical")
        ax.bar_label(cacheline_rects[percentage], padding=3, rotation="vertical")

    # fig.tight_layout()
    # fig.set_size_inches(w, h)
    fig.set_figwidth(14)  # in inches


    graph_filename = "{} {}.png".format(os.path.basename(os.path.normpath(output_directory_path)), title_str)
    plt.savefig(os.path.join(output_directory_path, graph_filename))
    plt.close(fig)


def process_bandwidth_verification_series_directory(directory_path):
    for filename in os.listdir(directory_path):
        # Find the log file
        filename_path = os.path.join(directory_path, filename)
        if (
            os.path.isfile(filename_path)
            and filename.endswith(".log")
            and not filename.startswith("run-sniper-repeat")
        ):
            with open(filename_path) as log_file:
                bw_info = extract_effective_bandwidth(log_file)
                # print("{}:".format(filename))
                # print(bw_info, end="\n")
                # with open(
                #     os.path.join(directory_path, "stats.txt"), "w"
                # ) as record_file:
                #     print(bw_info, file=record_file)

                plot_effective_bandwidth_grouped_bar_chart(directory_path, bw_info)
            break  # we got the file

    # Do IPC graph? by going through the .out files


def get_stats_from_files(
    output_directory_path: PathLike,
    log_file: Optional[TextIO] = None,
    stat_settings: Optional[List[StatSetting]] = None,
):
    ipc_line_no = 3  # Indexing start from 0, not 1
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

        first_file = False
        file_num += 1
        out_file_path = os.path.join(
            output_directory_path, "{}_sim.out".format(file_num)
        )

    return y_values, stat_settings


def get_list_padded_str(l: List[Any]):
    elements = ['{:>7}'.format(val) for val in l]
    return "[" + ", ".join(elements) + "]"


def print_stats(
    output_directory_path: PathLike,
    y_values: List[List[Any]],
    stat_settings: List[StatSetting],
    log_file: Optional[TextIO] = None,
    print_to_terminal = True
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
    print_to_terminal = True
):
    y_values, returned_stat_settings = get_stats_from_files(
        output_directory_path,
        log_file,
        stat_settings,
    )

    print_stats(
        output_directory_path,
        y_values,
        returned_stat_settings,
        log_file,
        print_to_terminal
    )


def process_and_graph_pq_and_cacheline_series(output_directory_path: PathLike, get_output_from_temp_folders = True):
    with open(os.path.join(output_directory_path, "Stats.txt"), "w") as log_file:
        passed_over_directories = []
        for filename in natsort.os_sorted(os.listdir(output_directory_path)):
            filename_path = os.path.join(output_directory_path, filename)
            if os.path.isdir(filename_path) and "output_files" in filename:
                # Record some stats
                # print(filename)
                print(filename, file=log_file)
                get_and_print_stats(
                    filename_path,
                    print_to_terminal=False,
                    log_file=log_file,
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
                        # StatSetting(
                        #     "remote datamovement % queue capped by custom cap",
                        #     float,
                        #     name_for_legend="datamovement capped by custom cap (%)",
                        # ),
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
                        # StatSetting(
                        #     "remote datamovement2 % queue capped by custom cap",
                        #     float,
                        #     name_for_legend="datamovement2 capped by custom cap (%)",
                        # ),
                        StatSetting(
                            "remote page move cancelled due to full queue",
                            int,
                            name_for_legend="remote page moves cancelled due to full queue",
                        ),
                    ],
                )
                # print()
                print(file=log_file)

                if get_output_from_temp_folders:
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

                # Generate graph
                if "partition_queue" in filename_path:
                    # Partition queue series
                    plot_graph_pq.run_from_cmdline(filename_path)
                elif "pq_cacheline_combined" in filename_path:
                    # PQ + cacheline combined series
                    plot_graph_pq.run_from_cmdline(filename_path)
                # elif "cacheline_ratio_series" in filename_path:
                #     # Cacheline ratio series
                #     plot_graph.run_from_cmdline(filename_path, "perf_model/dram", "remote_cacheline_queue_fraction")
                else:
                    # Unknown series type
                    print("\n\nUnknown series type for {}, cannot graph\n".format(filename))

            elif os.path.isdir(filename_path):
                passed_over_directories.append(filename)
        if len(passed_over_directories) > 0:
            print("\nPassed over {} directories:".format(len(passed_over_directories)))
            for dirname in passed_over_directories:
                print("  {}".format(dirname))


def delete_experiment_run_temp_folders(output_directory_path: PathLike):
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


if __name__ == "__main__":
    # with open("/home/jonathan/Desktop/percentages.txt", "r") as file:
    #     line = file.readline()
    #     num_strs = []
    #     while line.strip():
    #         num_str = (line.strip().split()[1])[:-1]
    #         num_strs.append(num_str)
    #         line = file.readline()
    #     print(num_strs)

    output_directory_path = "."

    # process_and_graph_pq_and_cacheline_series(output_directory_path, get_output_from_temp_folders=True)
    
    # delete_experiment_run_temp_folders(output_directory_path)

    process_and_graph_pq_and_cacheline_series(output_directory_path, get_output_from_temp_folders=False)

    
