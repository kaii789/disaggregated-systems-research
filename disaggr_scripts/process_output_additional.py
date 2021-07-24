import os
import numpy as np
import natsort
import shutil
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import interpolate

from typing import Any, Callable, Dict, Iterable, List, Tuple, Optional, TextIO, TypeVar

PathLike = TypeVar("PathLike", str, bytes, os.PathLike)  # Type for file/directory paths

from process_output_dir import BandwidthInfo, StatSetting
from process_output_dir import get_stats_from_files, get_list_padded_str, print_stats, get_and_print_stats, process_and_graph_experiment_series, delete_experiment_run_temp_folders

# import plot_graph
import plot_graph_pq

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


def save_graph_pq(
    output_directory_path: PathLike,
    y_values: List[List[Any]],
    stat_settings: List[StatSetting],
    x_axis: Optional[List[str]] = None,
    pq0_index: Optional[int] = None,
    pq0_guideline_indices: Iterable[int] = (),
    labels: Optional[List[str]] = None,
    log_file: Optional[TextIO] = None,
    title_str: Optional[str] = None,
    figsize_tuple: Optional[Tuple[float, float]] = None,
):
    plt.clf()
    plt.close("all")

    if len(y_values) == 0:
        # No data passed in
        print("No y_value lists in parameter y_values, skipping")
        return

    if not x_axis:
        if len(y_values[0]) == 16:  # PQ and cacheline combined series
            x_axis = [
                "no\nremote\nmem\n",
                "page\nmove\ninstant",
                "page\nmove\nnet lat\nonly",
                "page\nmove\nbw\nonly",
                "pq0",
                "pq1\ncl=\n0.1",
                "pq1\ncl=\n0.15",
                "pq1\ncl=\n0.2",
                "pq1\ncl=\n0.25",
                "pq1\ncl=\n0.3",
                "pq1\ncl=\n0.35",
                "pq1\ncl=\n0.4",
                "pq1\ncl=\n0.45",
                "pq1\ncl=\n0.5",
                "pq1\ncl=\n0.55",
                "pq1\ncl=\n0.6",
            ]
            if figsize_tuple is None:
                figsize_tuple = (10, 4.8)  # (width, height) in inches
        elif len(y_values[0]) == 13:  # PQ and cacheline combined series, edited (pq_new_series)
            x_axis = [
                "no\nremote\nmem\n",
                "page\nmove\ninstant",
                "pq0",
                "pq1\ncl=\n0.005",
                "pq1\ncl=\n0.01",
                "pq1\ncl=\n0.025",
                "pq1\ncl=\n0.05",
                "pq1\ncl=\n0.075",
                "pq1\ncl=\n0.1",
                "pq1\ncl=\n0.15",
                "pq1\ncl=\n0.2",
                "pq1\ncl=\n0.3",
                "pq1\ncl=\n0.5",
            ]
            if figsize_tuple is None:
                figsize_tuple = (9, 4.8)  # (width, height) in inches
            pq0_index = 2
        elif len(y_values[0]) == 12:  # PQ and cacheline combined series, edited (pq_newer_series)
            x_axis = [
                "no\nremote\nmem\n",
                "page\nmove\ninstant",
                "pq0",
                "pq1\ncl=\n0.01",
                "pq1\ncl=\n0.025",
                "pq1\ncl=\n0.05",
                "pq1\ncl=\n0.075",
                "pq1\ncl=\n0.1",
                "pq1\ncl=\n0.15",
                "pq1\ncl=\n0.2",
                "pq1\ncl=\n0.3",
                "pq1\ncl=\n0.5",
            ]
            if figsize_tuple is None:
                figsize_tuple = (9, 4.8)  # (width, height) in inches
                # figsize_tuple = (9, 6)  # (width, height) in inches
            pq0_index = 2
        elif len(y_values[0]) == 11:  # PQ and cacheline combined series, edited (pq_newer_series), TEMP
            x_axis = [
                "no\nremote\nmem\n",
                "page\nmove\ninstant",
                "pq0",
                "pq1\ncl=\n0.01",
                "pq1\ncl=\n0.025",
                "pq1\ncl=\n0.05",
                "pq1\ncl=\n0.075",
                "pq1\ncl=\n0.1",
                "pq1\ncl=\n0.15",
                "pq1\ncl=\n0.2",
                "pq1\ncl=\n0.3",
            ]
            if figsize_tuple is None:
                figsize_tuple = (9, 4.8)  # (width, height) in inches
            pq0_index = 2
        else:
            raise ValueError("number of experiment runs={}, inaccurate?".format(len(y_values[0])))
    if not figsize_tuple:
        figsize_tuple = (6.4, 4.8)  # default figure size
    if not labels:
        labels = [stat_settings[i].name_for_legend.strip() for i in range(len(y_values))]

    # Print stats to console, and if specified save to file
    if title_str:
        print("{}:".format(title_str))
    else:
        print("{}:".format(os.path.basename(os.path.normpath(output_directory_path))))
    print("X values:\n", [s.replace("\n", " ") for s in x_axis])
    print("Y values:")
    for i, y_value_list in enumerate(y_values):
        print("{:45}: {}".format(labels[i], get_list_padded_str(y_value_list)))
    print()

    if log_file:  # Also print to log file
        print("X values:\n", [s.replace("\n", " ") for s in x_axis], file=log_file)
        print("Y values:", file=log_file)
        for i, y_value_list in enumerate(y_values):
            print(
                "{:45}: {}".format(labels[i], get_list_padded_str(y_value_list)),
                file=log_file,
            )
        print(file=log_file)

    # Plot as graph
    plt.figure(figsize=figsize_tuple)
    if pq0_index is not None:
        for i in pq0_guideline_indices:
            plt.axhline(y=y_values[i][pq0_index])  # horizontal line at pq0 IPC for easier comparison

    line_style_list = [".--", ".--", ".--", ".--", ".--", ".--"]
    colors_list = ["r", "g", "b", "y", "c", "m", "darkorange", "navy", "dimgray", "violet"]
    if len(line_style_list) < len(y_values):
        line_style_list.extend(
            [line_style_list[0] for _ in range(len(y_values) - len(line_style_list))]
        )  # Extend list
    elif len(line_style_list) > len(y_values):
        line_style_list = line_style_list[: len(y_values)]  # Truncate list
    if len(colors_list) < len(y_values):
        colors_list.extend(
            [colors_list[0] for _ in range(len(y_values) - len(colors_list))]
        )  # Extend list
    elif len(colors_list) > len(y_values):
        colors_list = colors_list[: len(y_values)]  # Truncate list

    for i, (y_value_list, label, line_style, color) in enumerate(zip(y_values, labels, line_style_list, colors_list)):
        plt.plot(
            x_axis, y_value_list, line_style, label=label, color=color
        )
    # Uniform scale among experiments for the same application and input
    y_axis_top = 0.55
    # if "bcsstk" in output_directory_path:
    #     y_axis_top = 1.4
    data_y_max = max([max(y_values[i]) for i in range(len(y_values))])
    if data_y_max > y_axis_top:
        y_axis_top = data_y_max + max(0.2, data_y_max * 0.05)
    plt.ylim(bottom=0, top=y_axis_top + 0.04)
    plt.yticks(
        np.arange(0, y_axis_top + 0.01, step=(0.05 if y_axis_top < 0.8 else 0.1))
    )  # +0.01 to include y_axis_top

    if title_str is None:
        title_str = "Effect of Partition Queues"
    plt.title(title_str)
    plt.ylabel("Stats")
    plt.legend()
    plt.tight_layout()
    # Note: .png files are deleted by 'make clean' in the test/shared Makefile in the original repo
    graph_filename = "{}.png".format(title_str)
    plt.savefig(os.path.join(output_directory_path, graph_filename))


def pq_graphing(dir_path, log_file: Optional[TextIO] = None):
    """Graph the experiment folder."""
    dirname = os.path.basename(os.path.normpath(dir_path))
    if "partition_queue" in dirname:
        # Partition queue series
        plot_graph_pq.run_from_experiment(dir_path, log_file=log_file)
        return True
    elif "pq_cacheline_combined" in dirname:
        # PQ + cacheline combined series
        plot_graph_pq.run_from_experiment(dir_path, log_file=log_file)
        return True
    elif "pq_new_series" in dirname:
        # PQ + cacheline combined series, edited (13 runs)
        plot_graph_pq.run_from_experiment(dir_path, log_file=log_file)
        return True
    elif "pq_newer_series" in dirname:
        # PQ + cacheline combined series, edited (12 runs)
        plot_graph_pq.run_from_experiment(dir_path, log_file=log_file)
        return True
    # elif "cacheline_ratio_series" in dirname:
    #     # Cacheline ratio series
    #     plot_graph.run_from_experiment(dir_path, "perf_model/dram", "remote_cacheline_queue_fraction")
    #     return True
    else:
        # Unknown series type
        print("\n\nUnknown series type for {}, cannot graph\n".format(dirname))
        return False  # did not successfully graph


def rename_double_underscore(output_directory_path: PathLike):
    processed_folders = []
    renamed_files = []
    for filename in natsort.os_sorted(os.listdir(output_directory_path)):
        filename_path = os.path.join(output_directory_path, filename)
        if os.path.isdir(filename_path) and "output_files" in filename and "__" in filename:
            for sub_filename in natsort.os_sorted(os.listdir(filename_path)):
                sub_filename_path = os.path.join(filename_path, sub_filename)
                if (
                    os.path.isfile(sub_filename_path)
                    and "__" in sub_filename
                ):
                    os.rename(sub_filename_path, os.path.join(filename_path, sub_filename.replace("__", "_")))
                    print("Renamed file:", sub_filename)
                    renamed_files.append(sub_filename)
            # Rename directory
            os.rename(filename_path, os.path.join(output_directory_path, filename.replace("__", "_")))
            print("Renamed old folder:", filename_path)
            processed_folders.append(filename)
    print("Renamed {} folders, {} files".format(len(processed_folders), len(renamed_files)))

def rename_dot_zero(output_directory_path: PathLike):
    processed_folders = []
    renamed_files = []
    for filename in natsort.os_sorted(os.listdir(output_directory_path)):
        filename_path = os.path.join(output_directory_path, filename)
        if os.path.isdir(filename_path) and "output_files" in filename and ".0" in filename:
            for sub_filename in natsort.os_sorted(os.listdir(filename_path)):
                sub_filename_path = os.path.join(filename_path, sub_filename)
                if (
                    os.path.isfile(sub_filename_path)
                    and ".0" in sub_filename
                ):
                    # print("Will rename {} to {}".format(sub_filename, sub_filename.replace(".0", "")))
                    os.rename(sub_filename_path, os.path.join(filename_path, sub_filename.replace(".0", "")))
                    print("Renamed old file:", sub_filename)
                    renamed_files.append(sub_filename)
            # Rename directory
            os.rename(filename_path, os.path.join(output_directory_path, filename.replace(".0", "")))
            print("Renamed old folder:", filename_path)
            processed_folders.append(filename)
    print("Renamed {} folders, {} files".format(len(processed_folders), len(renamed_files)))

def rename_add_net_lat(output_directory_path: PathLike):
    processed_folders = []
    renamed_files = []
    for filename in natsort.os_sorted(os.listdir(output_directory_path)):
        filename_path = os.path.join(output_directory_path, filename)
        if os.path.isdir(filename_path) and "output_files" in filename and "netlat" not in filename:
            for sub_filename in natsort.os_sorted(os.listdir(filename_path)):
                sub_filename_path = os.path.join(filename_path, sub_filename)
                if (
                    os.path.isfile(sub_filename_path)
                    and "netlat" not in sub_filename
                    and "bw_scalefactor" in sub_filename
                ):
                    # print("Will rename {} to {}".format(sub_filename, sub_filename.replace(".0", "")))
                    os.rename(sub_filename_path, os.path.join(filename_path, sub_filename.replace("bw_scalefactor", "netlat_120_bw_scalefactor")))
                    print("Renamed old file:", sub_filename)
                    renamed_files.append(sub_filename)
            # Rename directory
            os.rename(filename_path, os.path.join(output_directory_path, filename.replace("bw_scalefactor", "netlat_120_bw_scalefactor")))
            print("Renamed old folder:", filename_path)
            processed_folders.append(filename)
    print("Renamed {} folders, {} files".format(len(processed_folders), len(renamed_files)))


def rename_run_temp_folder_nums(output_directory_path):
    renamed_run_temp_folders = []
    for filename in natsort.os_sorted(os.listdir(output_directory_path)):
        filename_path = os.path.join(output_directory_path, filename)
        if os.path.isdir(filename_path) and "output_files" in filename:
            # Subfolder iteration
            for sub_filename in natsort.os_sorted(os.listdir(filename_path)):
                sub_filename_path = os.path.join(filename_path, sub_filename)
                if (
                    os.path.isdir(sub_filename_path)
                    and sub_filename.startswith("run_")
                    and "temp" in sub_filename
                ):
                    run_no = int(sub_filename[4:sub_filename.find("_", 4)])  # 4 is len("run_")
                    if run_no > 4:
                        # Rename
                        new_name = "run_{}_".format(run_no - 1) + sub_filename[sub_filename.find("process"):]
                        os.rename(sub_filename_path, os.path.join(filename_path, new_name))
                        print("Renamed old folder:", sub_filename_path)
                        renamed_run_temp_folders.append(sub_filename)


def ideal_window_size_combining(output_directory_path: PathLike):
    ideal_window_size_throttling_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D5_add (rmode1, idealwinsize, remote_init=true)"
    fcfs_baseline_throttling_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D3 (rmode1, FCFS throttling baseline)"
    ideal_baseline_throttling_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D5-mel-15"

    passed_over_directories = []

    last_experiment_name_root = None
    # baseline_y_values = None
    # baseline_stat_settings = None
    graph_y_values = []
    graph_stat_settings = []

    labels = ["IPC, FIFO throttling baseline", "IPC, ideal baseline winsize=100000"]
    for win_size in [10000, 20000, 500000, 1000000]:
        labels.append("IPC, ideal winsize={}".format(win_size))

    for filename in natsort.os_sorted(os.listdir(ideal_window_size_throttling_dir)):
        filename_path = os.path.join(ideal_window_size_throttling_dir, filename)
        if not os.path.isdir(filename_path):
            continue
        if not "output_files" in filename:
            passed_over_directories.append(filename)
            continue
        if "remoteinit" not in filename:
            print("Directory {} doesn't contain the string 'remoteinit', passing over".format(filename))
            continue
        # The second index of the slice is the underscore right after "remoteinit_true" or "remoteinit_false"
        current_experiment_name_root = filename[:filename.find("_", filename.find("remoteinit") + len("remoteinit") + 1)]
        if current_experiment_name_root != last_experiment_name_root:
            if last_experiment_name_root is not None:
                # Wrap up previous series
                save_graph_pq(output_directory_path, graph_y_values, graph_stat_settings, labels=labels, title_str=last_experiment_name_root)
                graph_y_values.clear()
                graph_stat_settings.clear()
            # Starting new series
            last_experiment_name_root = current_experiment_name_root
            # Get FIFO throttling baseline results
            baseline_experiment_output_dir_list = []
            for candidate_file in os.listdir(fcfs_baseline_throttling_dir):
                candidate_file_path = os.path.join(fcfs_baseline_throttling_dir, candidate_file)
                if os.path.isdir(candidate_file_path) and candidate_file.startswith(current_experiment_name_root):
                    baseline_experiment_output_dir_list.append(candidate_file_path)
            if len(baseline_experiment_output_dir_list) != 1:
                print("Error: did not find one FIFO baseline experiment with the same name root:", baseline_experiment_output_dir_list)

            fifo_baseline_y_values, fifo_baseline_stat_settings = get_stats_from_files(baseline_experiment_output_dir_list[0])
            # Get the IPC ones, at index 0
            graph_y_values.append(fifo_baseline_y_values[0])
            graph_stat_settings.append(fifo_baseline_stat_settings[0])

            # Get ideal throttling default 10^5 winsize results
            ideal_baseline_experiment_output_dir_list = []
            for candidate_file in os.listdir(ideal_baseline_throttling_dir):
                candidate_file_path = os.path.join(ideal_baseline_throttling_dir, candidate_file)
                if os.path.isdir(candidate_file_path) and candidate_file.startswith(current_experiment_name_root):
                    ideal_baseline_experiment_output_dir_list.append(candidate_file_path)
            if len(ideal_baseline_experiment_output_dir_list) != 1:
                print("Error: did not find one ideal baseline experiment with the same name root:", ideal_baseline_experiment_output_dir_list)

            ideal_baseline_y_values, ideal_baseline_stat_settings = get_stats_from_files(ideal_baseline_experiment_output_dir_list[0])
            # Get the IPC ones, at index 0
            graph_y_values.append(ideal_baseline_y_values[0])
            graph_stat_settings.append(ideal_baseline_stat_settings[0])

        y_values, stat_settings = get_stats_from_files(filename_path)
        # Get the IPC ones, at index 0
        graph_y_values.append(y_values[0])
        graph_stat_settings.append(stat_settings[0])

    # last series
    if len(graph_y_values) > 0:
        save_graph_pq(output_directory_path, graph_y_values, graph_stat_settings, labels=labels, title_str=last_experiment_name_root)
    if len(passed_over_directories) > 0:
        print("\nPassed over {} directories:".format(len(passed_over_directories)))
        for dirname in passed_over_directories:
            print("  {}".format(dirname))


def ideal_thresholds_combining(output_directory_path: PathLike):
    ideal_thresholds_throttling_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D5_add (rmode2, idealthresholds, remote_init=true)"
    fcfs_baseline_throttling_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D3 (rmode2, FCFS throttling baseline)"

    passed_over_directories = []

    last_experiment_name_root = None
    graph_y_values = []
    graph_stat_settings = []

    labels = ["IPC, FIFO rmode2 threshold 5", "IPC, FIFO rmode2 threshold 10"]
    for threshold in [5, 10, 15]:
        labels.append("IPC, ideal rmode2 threshold={}".format(threshold))

    for filename in natsort.os_sorted(os.listdir(ideal_thresholds_throttling_dir)):
        filename_path = os.path.join(ideal_thresholds_throttling_dir, filename)
        if not os.path.isdir(filename_path):
            continue
        if not ("output_files" in filename and "idealwinsize" not in filename):
            passed_over_directories.append(filename)
            continue
        if "remoteinit" not in filename:
            print("Directory {} doesn't contain the string 'remoteinit', passing over".format(filename))
            continue
        current_experiment_name_root = filename[:filename.find("threshold") - 1]
        if current_experiment_name_root != last_experiment_name_root:
            if last_experiment_name_root is not None:
                # Wrap up previous series
                save_graph_pq(output_directory_path, graph_y_values, graph_stat_settings, labels=labels, title_str=last_experiment_name_root)
                graph_y_values.clear()
                graph_stat_settings.clear()
            # Starting new series
            last_experiment_name_root = current_experiment_name_root
            # Get FIFO throttling baseline results
            baseline_experiment_output_dir_list = []
            for candidate_file in os.listdir(fcfs_baseline_throttling_dir):
                candidate_file_path = os.path.join(fcfs_baseline_throttling_dir, candidate_file)
                if os.path.isdir(candidate_file_path) and candidate_file.startswith(current_experiment_name_root):
                    baseline_experiment_output_dir_list.append(candidate_file_path)

            for fifo_baseline in baseline_experiment_output_dir_list:
                fifo_baseline_y_values, fifo_baseline_stat_settings = get_stats_from_files(fifo_baseline)
                # Get the IPC ones, at index 0
                graph_y_values.append(fifo_baseline_y_values[0])
                graph_stat_settings.append(fifo_baseline_stat_settings[0])

        y_values, stat_settings = get_stats_from_files(filename_path)
        # Get the IPC ones, at index 0
        graph_y_values.append(y_values[0])
        graph_stat_settings.append(stat_settings[0])

    # last series
    if len(graph_y_values) > 0:
        save_graph_pq(output_directory_path, graph_y_values, graph_stat_settings, labels=labels, title_str=last_experiment_name_root)
    if len(passed_over_directories) > 0:
        print("\nPassed over {} directories:".format(len(passed_over_directories)))
        for dirname in passed_over_directories:
            print("  {}".format(dirname))

def convert_old_pq_cacheline_combined_y_values(ipcs_list: List[Any]):
    new_series_format = []
    for index in [0, 1, 4]:
        new_series_format.append(ipcs_list[index])
    for i in range(5):
        new_series_format.append(np.nan)  # 5 np.nan for the runs that are not in the old baselines
    for index in [5, 6, 7, 9, 13]:
        new_series_format.append(ipcs_list[index])
    return new_series_format

def limit_redundant_moves_combining(output_directory_path: PathLike):
    limit_redundant_moves_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D5_cont (rmode1, limitredundantmoves)"
    fcfs_baseline_throttling_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D3 (rmode1, FCFS throttling baseline)"
    ideal_baseline_throttling_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D5-mel-15"

    passed_over_directories = []

    last_experiment_name_root = None
    graph_y_values = []
    graph_stat_settings = []

    labels = ["IPC, FIFO baseline"]
    for limit_redundant_moves in [2, 5, 10, 40]:
        labels.append("IPC, ideal limitmoves={}".format(limit_redundant_moves))
        labels.append("IPC, nonideal limitmoves={}".format(limit_redundant_moves))

    for filename in natsort.os_sorted(os.listdir(limit_redundant_moves_dir)):
        filename_path = os.path.join(limit_redundant_moves_dir, filename)
        if not os.path.isdir(filename_path):
            continue
        if not ("output_files" in filename):
            passed_over_directories.append(filename)
            continue
        if "remoteinit" not in filename:
            print("Directory {} doesn't contain the string 'remoteinit', passing over".format(filename))
            continue
        # The second index of the slice is the underscore right after "remoteinit_true" or "remoteinit_false"
        current_experiment_name_root = filename[:filename.find("_", filename.find("remoteinit") + len("remoteinit") + 1)]
        if current_experiment_name_root != last_experiment_name_root:
            if last_experiment_name_root is not None:
                # Wrap up previous series
                save_graph_pq(output_directory_path, graph_y_values, graph_stat_settings, labels=labels, title_str=last_experiment_name_root)
                graph_y_values.clear()
                graph_stat_settings.clear()
            # Starting new series
            last_experiment_name_root = current_experiment_name_root
            # Get FIFO throttling baseline results
            baseline_experiment_output_dir_list = []
            for candidate_file in os.listdir(fcfs_baseline_throttling_dir):
                candidate_file_path = os.path.join(fcfs_baseline_throttling_dir, candidate_file)
                if os.path.isdir(candidate_file_path) and candidate_file.startswith(current_experiment_name_root):
                    baseline_experiment_output_dir_list.append(candidate_file_path)

            for fifo_baseline in baseline_experiment_output_dir_list:
                fifo_baseline_y_values, fifo_baseline_stat_settings = get_stats_from_files(fifo_baseline)
                # Get the IPC ones, at index 0
                graph_y_values.append(convert_old_pq_cacheline_combined_y_values(fifo_baseline_y_values[0]))
                graph_stat_settings.append(fifo_baseline_stat_settings[0])

            # # Get ideal throttling default 10^5 winsize results
            # ideal_baseline_experiment_output_dir_list = []
            # for candidate_file in os.listdir(ideal_baseline_throttling_dir):
            #     candidate_file_path = os.path.join(ideal_baseline_throttling_dir, candidate_file)
            #     if os.path.isdir(candidate_file_path) and candidate_file.startswith(current_experiment_name_root):
            #         ideal_baseline_experiment_output_dir_list.append(candidate_file_path)
            # if len(ideal_baseline_experiment_output_dir_list) != 1:
            #     print("Error: did not find one ideal baseline experiment with the same name root:", ideal_baseline_experiment_output_dir_list)

            # ideal_baseline_y_values, ideal_baseline_stat_settings = get_stats_from_files(ideal_baseline_experiment_output_dir_list[0])
            # # Get the IPC ones, at index 0
            # graph_y_values.append(ideal_baseline_y_values[0])
            # graph_stat_settings.append(ideal_baseline_stat_settings[0])

        y_values, stat_settings = get_stats_from_files(filename_path)
        # Get the IPC ones, at index 0
        graph_y_values.append(y_values[0])
        graph_stat_settings.append(stat_settings[0])

    # last series
    if len(graph_y_values) > 0:
        save_graph_pq(output_directory_path, graph_y_values, graph_stat_settings, labels=labels, title_str=last_experiment_name_root)
    if len(passed_over_directories) > 0:
        print("\nPassed over {} directories:".format(len(passed_over_directories)))
        for dirname in passed_over_directories:
            print("  {}".format(dirname))


def D5B_ideal_pagemove_throttling_combining(output_directory_path: PathLike, results_dir_path: PathLike):
    passed_over_directories = []

    last_experiment_name_root = None
    graph_y_values = []
    graph_stat_settings = []

    labels = ["IPC, FCFS baseline", "IPC, Ideal baseline"]
    figsize_tuple = (9, 4.8)
    pq0_guideline_indices = (0, 1)  # draw pq0 guideline only for the first two series, the FCFS baseline and the ideal page throttling baseline

    for filename in natsort.os_sorted(os.listdir(results_dir_path)):
        filename_path = os.path.join(results_dir_path, filename)
        if not os.path.isdir(filename_path):
            continue
        if not ("output_files" in filename and "pq_newer_series" in filename):
            passed_over_directories.append(filename)
            continue
        if "remoteinit" not in filename:
            print("Directory {} doesn't contain the string 'remoteinit', passing over".format(filename))
            continue
        # The second index of the slice is the underscore right after "remoteinit_true" or "remoteinit_false"
        current_experiment_name_root = filename[:filename.find("_", filename.find("remoteinit") + len("remoteinit") + 1)]
        if current_experiment_name_root != last_experiment_name_root:
            if last_experiment_name_root is not None:
                # Wrap up previous series
                save_graph_pq(output_directory_path, graph_y_values, graph_stat_settings, figsize_tuple=figsize_tuple, labels=labels, title_str=last_experiment_name_root, pq0_guideline_indices=pq0_guideline_indices)
                graph_y_values.clear()
                graph_stat_settings.clear()
            # Starting new series
            last_experiment_name_root = current_experiment_name_root

            # Get FIFO throttling baseline results
            baseline_dir_name = current_experiment_name_root + "_pq_newer_series_output_files"
            baseline_experiment_output_dir = os.path.join(results_dir_path, baseline_dir_name)
            ideal_dir_name = current_experiment_name_root + "_idealwinsize_100000_pq_newer_series_output_files"
            ideal_experiment_output_dir = os.path.join(results_dir_path, ideal_dir_name)

            fifo_baseline_y_values, fifo_baseline_stat_settings = get_stats_from_files(baseline_experiment_output_dir)
            # Get the IPC ones, at index 0
            graph_y_values.append(fifo_baseline_y_values[0])
            graph_stat_settings.append(fifo_baseline_stat_settings[0])

            ideal_baseline_y_values, ideal_baseline_stat_settings = get_stats_from_files(ideal_experiment_output_dir)
            # Get the IPC ones, at index 0
            graph_y_values.append(ideal_baseline_y_values[0])
            graph_stat_settings.append(ideal_baseline_stat_settings[0])

        # y_values, stat_settings = get_stats_from_files(filename_path)
        # # Get the IPC ones, at index 0
        # graph_y_values.append(y_values[0])
        # graph_stat_settings.append(stat_settings[0])

    # last series
    if len(graph_y_values) > 0:
        save_graph_pq(output_directory_path, graph_y_values, graph_stat_settings, figsize_tuple=figsize_tuple, labels=labels, title_str=last_experiment_name_root, pq0_guideline_indices=pq0_guideline_indices)
    if len(passed_over_directories) > 0:
        print("\nPassed over {} directories:".format(len(passed_over_directories)))
        for dirname in passed_over_directories:
            print("  {}".format(dirname))


def process_D5B_dir():
    results_dir_path = "/home/jonathan/Desktop/experiment_results/experimentrun_D5_next_l3cache"
    graph_output_dir_path = "/home/jonathan/Desktop/experiment_results/Ideal vs FCFS (D5B)"
    passed_over_directories = []
    for filename in natsort.os_sorted(os.listdir(results_dir_path)):
        filename_path = os.path.join(results_dir_path, filename)
        if not os.path.isdir(filename_path):
            continue
        if filename.startswith("experimentrun_D5B") and "test" not in filename.lower():
            D5B_ideal_pagemove_throttling_combining(graph_output_dir_path, filename_path)
        else:
            passed_over_directories.append(filename)
    if len(passed_over_directories) > 0:
        print("\nPassed over {} directories:".format(len(passed_over_directories)))
        for dirname in passed_over_directories:
            print("  {}".format(dirname))


def pq0_bw_sensitivity_copying(output_directory_path: PathLike, results_dir_path: PathLike, target_beginnings: str, ending_format_str: str):
    # Get pq=0 results from various experiment folders, and copy to the output_directory_path
    passed_over_directories = []
    matched_folders = []

    for filename in natsort.os_sorted(os.listdir(results_dir_path)):
        filename_path = os.path.join(results_dir_path, filename)
        if not os.path.isdir(filename_path):
            continue
        if not ("output_files" in filename and "pq_newer_series" in filename and "remoteinit_true" in filename) \
                or "idealwinsize" in filename or "threshold" in filename:
            passed_over_directories.append(filename)
            continue
        # Determine if the experiment folder matches ones of the configurations we're looking for
        matched = False
        for beginning in target_beginnings:
            if filename.startswith(beginning):
                matched = True
                break
        if not matched:
            # print("beginning didn't match: {}".format(filename))
            continue
        matched = False
        for bw in [4, 8, 16, 32]:
            if filename.endswith(ending_format_str.format(bw)):
                matched = True
                break
        if not matched:
            # print("ending didn't match: {}".format(filename))
            continue

        matched_folders.append(filename)
        current_experiment_name_root = filename[:filename.find("_", filename.find("netlat") + len("netlat") + 1)]
        current_experiment_name_root = current_experiment_name_root + "_remoteinit_true_pq0"

        target_dir = os.path.join(output_directory_path, current_experiment_name_root)
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        file_num = 3
        cfg_file_path = os.path.join(filename_path, "{}_sim.cfg".format(file_num))
        out_file_path = os.path.join(filename_path, "{}_sim.out".format(file_num))
        # Read all the output files, starting from 1 and going up
        if not os.path.isfile(cfg_file_path) or not os.path.isfile(out_file_path):
            print("Error...")
            continue

        start_index = filename.find("bw_scalefactor_") + len("bw_scalefactor_")
        if filename.find("_", start_index) != -1:
            end_index = filename.find("_", start_index)
        else:
            end_index = len(filename)
        bw_scalefactor = int(filename[start_index : end_index])
        bw_to_num = {4: 1, 8: 2, 16: 3, 32: 4}

        cfg_file_destination = os.path.join(target_dir, "{}_sim.cfg".format(bw_to_num[bw_scalefactor]))
        out_file_destination = os.path.join(target_dir, "{}_sim.out".format(bw_to_num[bw_scalefactor]))
        shutil.copy2(cfg_file_path, cfg_file_destination)
        shutil.copy2(out_file_path, out_file_destination)

    # if len(passed_over_directories) > 0:
    #     print("\nPassed over {} directories:".format(len(passed_over_directories)))
    #     for dirname in passed_over_directories:
    #         print("  {}".format(dirname))
    
    # Print matched folders
    for dir in matched_folders:
        print(dir)


def pq0_bw_sensitivity():
    target_beginnings = ["ligra_bfs_localdram_4MB_netlat_120",
                         "darknet_tiny_localdram_2MB_netlat_120",
                         "darknet_darknet19_localdram_4MB_netlat_120",
                         "darknet_resnet50_localdram_4MB_netlat_120",
                         "darknet_vgg16_localdram_4MB_netlat_120",
                         "ligra_bc_nonsym_localdram_2MB_netlat_120",
                         "ligra_components_nonsym_localdram_2MB_netlat_120",
                         "ligra_pagerank_nonsym_localdram_8MB_netlat_120",
                         "ligra_triangle_sym_regular_input_sym_localdram_8MB_netlat_120",
                        #  "roadNetCA_localdram_2MB_netlat_120",
                         "roadNetPA_localdram_1MB_netlat_120",
                         "spmv_roadNetPA_localdram_524288B_netlat_120",
                         "stream_mode1_localdram_4MB_netlat_120",
                         "stream_mode3_localdram_4MB_netlat_120",
                         "darknet_tiny_localdram_1MB_netlat_120",
                         "darknet_darknet19_localdram_1MB_netlat_120",
                         "darknet_resnet50_localdram_1MB_netlat_120",
                         "darknet_vgg16_localdram_1MB_netlat_120",
                         "ligra_triangle_sym_regular_input_sym_localdram_16MB_netlat_120",
                        ]
    ending_format_str = "_bw_scalefactor_{}_remoteinit_true_pq_newer_series_output_files"

    output_directory_path = "/home/jonathan/Desktop/experiment_results/experimentrun_D5_next_l3cache"
    passed_over_directories = []
    for filename in natsort.os_sorted(os.listdir(output_directory_path)):
        filename_path = os.path.join(output_directory_path, filename)
        if not os.path.isdir(filename_path):
            continue
        if filename.startswith("experimentrun") and "test" not in filename.lower() and "prefetcher" not in filename.lower():
            pq0_bw_sensitivity_copying("/home/jonathan/Desktop/experiment_results/pq0 bw sensitivity", filename_path, target_beginnings, ending_format_str)
        else:
            passed_over_directories.append(filename)
    # if len(passed_over_directories) > 0:
    #     print("\nPassed over {} directories:".format(len(passed_over_directories)))
    #     for dirname in passed_over_directories:
    #         print("  {}".format(dirname))


def get_stats_from_files_custom(
    output_directory_path: PathLike,
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
    for file_num in [1, 2, 3, 4]:
        out_file_path = os.path.join(output_directory_path, "{}_sim.out".format(file_num))
        if not os.path.isfile(out_file_path):
            for index in range(len(y_values)):
                y_values[index].append(np.nan)
            continue
        with open(out_file_path, "r") as out_file:
            out_file_lines = out_file.readlines()
            if len(out_file_lines) == 0:
                # The file is empty...
                print("{} is an empty file!".format(out_file_path))
                for index in range(len(y_values)):
                    y_values[index].append(np.nan)
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

    return y_values, stat_settings

def pq0_bw_sensitivity_graphing():
    # Graph pq=0 IPC changes
    output_directory_path = "/home/jonathan/Desktop/experiment_results/pq0 bw sensitivity"
    passed_over_directories = []

    ipcs = []
    labels = []
    for filename in natsort.os_sorted(os.listdir(output_directory_path)):
        filename_path = os.path.join(output_directory_path, filename)
        if not os.path.isdir(filename_path):
            continue
        if "pq0" in filename.lower():
            # Get IPCs
            y_values, _ = get_stats_from_files_custom(filename_path)
            ipcs.append(y_values[0])
            label = filename[:filename.find("netlat") - 1].replace("_localdram_", "_")
            labels.append(label)
        else:
            passed_over_directories.append(filename)
    if len(passed_over_directories) > 0:
        print("\nPassed over {} directories:".format(len(passed_over_directories)))
        for dirname in passed_over_directories:
            print("  {}".format(dirname))

    # Graph
    save_graph_pq(output_directory_path,
                  ipcs,
                  [StatSetting("IPC", float) for _ in range(len(ipcs))],
                  x_axis=["bw_sf=4", "bw_sf=8", "bw_sf=16", "bw_sf=32"],
                  labels=labels,
                  title_str="Benchmark Bandwidth Sensitivity",
                  figsize_tuple=(8, 10))


def prefetcher_combining(output_directory_path: PathLike):
    def find_experiment_dirs(containing_dir: PathLike, experiment_name_root: str):
        # Find directories containing baseline results
        fcfs_throttling_baseline_path = None
        ideal_throttling_baseline_path = None
        for subdir in natsort.os_sorted(os.listdir(containing_dir)):
            subdir_path = os.path.join(containing_dir, subdir)
            if not (os.path.isdir(subdir_path) and subdir.startswith("experimentrun_D5B")):
                continue
            for experiment_folder_name in natsort.os_sorted(os.listdir(subdir_path)):
                if experiment_folder_name == experiment_name_root + "_pq_newer_series_output_files":
                    fcfs_throttling_baseline_path = os.path.join(subdir_path, experiment_folder_name)
                elif experiment_folder_name == experiment_name_root + "_idealwinsize_100000_pq_newer_series_output_files":
                    ideal_throttling_baseline_path = os.path.join(subdir_path, experiment_folder_name)
                if fcfs_throttling_baseline_path is not None and ideal_throttling_baseline_path is not None:
                    break  # Got both ones we wanted
        return fcfs_throttling_baseline_path, ideal_throttling_baseline_path

    prefetcher_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D5_next_l3cache/experimentrun_D5E (prefetcher)"
    fcfs_ideal_throttling_containing_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D5_next_l3cache"

    passed_over_directories = []

    last_experiment_name_root = None
    graph_y_values = []
    graph_stat_settings = []

    labels = ["IPC, FCFS baseline", "IPC, Ideal page throttling baseline", "IPC, Prefetcher (next page)"]

    for filename in natsort.os_sorted(os.listdir(prefetcher_dir)):
        filename_path = os.path.join(prefetcher_dir, filename)
        if not os.path.isdir(filename_path):
            continue
        if not ("output_files" in filename):
            passed_over_directories.append(filename)
            continue
        if "remoteinit" not in filename:
            print("Directory {} doesn't contain the string 'remoteinit', passing over".format(filename))
            continue
        # The second index of the slice is the underscore right after "remoteinit_true" or "remoteinit_false"
        current_experiment_name_root = filename[:filename.find("_", filename.find("remoteinit") + len("remoteinit") + 1)]
        if current_experiment_name_root != last_experiment_name_root:
            if last_experiment_name_root is not None:
                # Wrap up previous series
                save_graph_pq(output_directory_path, graph_y_values, graph_stat_settings, labels, title_str=last_experiment_name_root)
                graph_y_values.clear()
                graph_stat_settings.clear()
            # Starting new series
            last_experiment_name_root = current_experiment_name_root
            # Get FCFS and Ideal throttling baseline results
            fcfs_baseline, ideal_baseline = find_experiment_dirs(fcfs_ideal_throttling_containing_dir, current_experiment_name_root)
            if fcfs_baseline is None:
                print("Couldn't find fcfs_baseline for {}".format(current_experiment_name_root))
            if ideal_baseline is None:
                print("Couldn't find ideal_baseline for {}".format(current_experiment_name_root))

            fcfs_baseline_y_values, fcfs_baseline_stat_settings = get_stats_from_files(fcfs_baseline)
            # Get the IPC ones, at index 0
            graph_y_values.append(fcfs_baseline_y_values[0])
            graph_stat_settings.append(fcfs_baseline_stat_settings[0])

            ideal_baseline_y_values, ideal_baseline_stat_settings = get_stats_from_files(ideal_baseline)
            # Get the IPC ones, at index 0
            graph_y_values.append(ideal_baseline_y_values[0])
            graph_stat_settings.append(ideal_baseline_stat_settings[0])

        y_values, stat_settings = get_stats_from_files(filename_path)
        # Get the IPC ones, at index 0
        graph_y_values.append(y_values[0])
        graph_stat_settings.append(stat_settings[0])

    # last series
    if len(graph_y_values) > 0:
        save_graph_pq(output_directory_path, graph_y_values, graph_stat_settings, labels, title_str=last_experiment_name_root)
    if len(passed_over_directories) > 0:
        print("\nPassed over {} directories:".format(len(passed_over_directories)))
        for dirname in passed_over_directories:
            print("  {}".format(dirname))


def general_experiment_combining(output_directory_path: PathLike):
    darknet_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D7/experimentrun_D7 (darknet)"
    darknet_compression_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D7/experimentrun_D7 (darknet compression)"
    ligra_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D7/experimentrun_D7 (ligra)"
    spmv_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D7/experimentrun_D7 (spmv)"
    sssp_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D7/experimentrun_D7 (sssp)"
    stream_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D7/experimentrun_D7 (stream)"
    new_experiments_dir = darknet_compression_dir
    fcfs_baseline_throttling_dir = darknet_dir
    ideal_baseline_throttling_dir = darknet_dir
    experiment_series_name = "pq_newer_series"

    passed_over_directories = []

    last_experiment_name_root = None
    graph_y_values = []
    graph_stat_settings = []

    labels = []
    figsize_tuple = (9, 4.8)
    pq0_guideline_indices = (0, )  # draw pq0 guideline only for the first series, typically the FCFS baseline

    for filename in natsort.os_sorted(os.listdir(new_experiments_dir)):
        filename_path = os.path.join(new_experiments_dir, filename)
        if not os.path.isdir(filename_path):
            continue
        if not ("output_files" in filename):
            passed_over_directories.append(filename)
            continue
        if "remoteinit" not in filename:
            print("Directory {} doesn't contain the string 'remoteinit', passing over".format(filename))
            continue
        # The second index of the slice is the underscore right after "remoteinit_true" or "remoteinit_false"
        current_experiment_name_root = filename[:filename.find("_", filename.find("remoteinit") + len("remoteinit") + 1)]
        # The variation name is the part after current_experiment_name_root and before experiment_series_name, without leading and trailing "_"
        current_experiment_variation_name = filename[filename.find("_", filename.find("remoteinit") + len("remoteinit") + 1) + 1 : filename.find(experiment_series_name) - 1]
        if current_experiment_name_root != last_experiment_name_root:
            if last_experiment_name_root is not None:
                # Wrap up previous series
                save_graph_pq(output_directory_path, graph_y_values, graph_stat_settings, figsize_tuple=figsize_tuple, labels=labels, title_str=last_experiment_name_root, pq0_guideline_indices=pq0_guideline_indices)
                graph_y_values.clear()
                graph_stat_settings.clear()
            # Starting new series
            last_experiment_name_root = current_experiment_name_root
            labels = []
            # Get FCFS throttling baseline results
            baseline_experiment_output_dir_list = []
            baseline_experiment_variation_names = []
            for candidate_file in os.listdir(fcfs_baseline_throttling_dir):
                candidate_file_path = os.path.join(fcfs_baseline_throttling_dir, candidate_file)
                experiment_variation_name = candidate_file[candidate_file.find("_", candidate_file.find("remoteinit") + len("remoteinit") + 1) + 1 : candidate_file.find(experiment_series_name) - 1]
                if os.path.isdir(candidate_file_path) and candidate_file.startswith(current_experiment_name_root) and experiment_variation_name == "":
                    baseline_experiment_output_dir_list.append(candidate_file_path)
                    baseline_experiment_variation_names.append(experiment_variation_name)
    

            # Graph all FCFS baselines
            for fcfs_baseline, baseline_variation_name in zip(baseline_experiment_output_dir_list, baseline_experiment_variation_names):
                fcfs_baseline_y_values, fcfs_baseline_stat_settings = get_stats_from_files(fcfs_baseline)
                # Get the IPC ones, at index 0
                graph_y_values.append(fcfs_baseline_y_values[0])
                graph_stat_settings.append(fcfs_baseline_stat_settings[0])
                labels.append("FCFS baseline " + baseline_variation_name)

            # # Get ideal throttling default 10^5 winsize results
            ideal_baseline_experiment_output_dir_list = []
            ideal_baseline_experiment_variation_names = []
            for candidate_file in os.listdir(ideal_baseline_throttling_dir):
                candidate_file_path = os.path.join(ideal_baseline_throttling_dir, candidate_file)
                experiment_variation_name = candidate_file[candidate_file.find("_", candidate_file.find("remoteinit") + len("remoteinit") + 1) + 1 : candidate_file.find(experiment_series_name) - 1]
                if os.path.isdir(candidate_file_path) and candidate_file.startswith(current_experiment_name_root) and "idealwinsize" in candidate_file:
                    ideal_baseline_experiment_output_dir_list.append(candidate_file_path)
                    ideal_baseline_experiment_variation_names.append(experiment_variation_name)
            if len(ideal_baseline_experiment_output_dir_list) != 1:
                print("Error: did not find just one ideal baseline experiment with the same name root as '{}':".format(current_experiment_name_root), ideal_baseline_experiment_output_dir_list)
            else:
                ideal_baseline_y_values, ideal_baseline_stat_settings = get_stats_from_files(ideal_baseline_experiment_output_dir_list[0])
                # Get the IPC ones, at index 0
                graph_y_values.append(ideal_baseline_y_values[0])
                graph_stat_settings.append(ideal_baseline_stat_settings[0])
                labels.append(ideal_baseline_experiment_variation_names[0])

        if current_experiment_variation_name == "" or current_experiment_variation_name == "idealwinsize_100000":
            # Already included in FCFS/Ideal page throttling baseline
            continue
        # TEMP
        # if "prefetch" in current_experiment_variation_name:
        #     continue
        # if "limredundantmoves" in current_experiment_variation_name or "rmode5" in current_experiment_variation_name:
        #     continue
        y_values, stat_settings = get_stats_from_files(filename_path)
        # Get the IPC ones, at index 0
        graph_y_values.append(y_values[0])
        graph_stat_settings.append(stat_settings[0])
        labels.append(current_experiment_variation_name)

    # last series
    if len(graph_y_values) > 0:
        save_graph_pq(output_directory_path, graph_y_values, graph_stat_settings, figsize_tuple=figsize_tuple, labels=labels, title_str=last_experiment_name_root, pq0_guideline_indices=pq0_guideline_indices)
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

    # process_and_graph_experiment_series(output_directory_path, get_output_from_temp_folders=True, graph_experiment_folders=True, graphing_function=pq_graphing)

    # delete_experiment_run_temp_folders(output_directory_path)

    process_and_graph_experiment_series(output_directory_path, get_output_from_temp_folders=False, graph_experiment_folders=True, graphing_function=pq_graphing)

    # For pq=0 bw sensitivity testing
    # process_and_graph_experiment_series(output_directory_path, get_output_from_temp_folders=True, graph_experiment_folders=False, first_experiment_no=3)


    # rename_double_underscore(output_directory_path)
    # rename_dot_zero(output_directory_path)
    # rename_add_net_lat(output_directory_path)

    # ideal_window_size_combining(".")
    # ideal_thresholds_combining(".")
    # limit_redundant_moves_combining(".")

    # process_D5B_dir()

    # # additional_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D5_next_l3cache/experimentrun_D5B (ligra other)"
    # additional_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D5_next_l3cache/experimentrun_D5B (stream)"
    # D5B_ideal_pagemove_throttling_combining("/home/jonathan/Desktop/experiment_results/Ideal vs FCFS (D5B)", additional_dir)

    # additional_dir = "/home/jonathan/Desktop/experiment_results/experimentrun_D5_next_l3cache/experimentrun_D5Test"
    # D5B_ideal_pagemove_throttling_combining("/home/jonathan/Desktop/experiment_results/I_D5Test", additional_dir)

    # pq0_bw_sensitivity()
    # pq0_bw_sensitivity_graphing()

    # prefetcher_combining("/home/jonathan/Desktop/experiment_results/prefetcher (next page)")

    # general_experiment_combining("/home/jonathan/Desktop/experiment_results/prefetcher_D7")

    # passed_over_directories = []
    # directories_not_graphed = []
    # for filename in natsort.os_sorted(os.listdir(output_directory_path)):
    #     filename_path = os.path.join(output_directory_path, filename)
    #     if os.path.isdir(filename_path) and "output_files" in filename:
    #         for sub_filename in natsort.os_sorted(os.listdir(filename_path)):
    #             sub_filename_path = os.path.join(filename_path, sub_filename)
    #             if (
    #                 os.path.isfile(sub_filename_path)
    #                 and sub_filename.endswith(".png")
    #             ):
    #                 src_path = sub_filename_path
    #                 dst_path = os.path.join(output_directory_path, sub_filename)
    #                 shutil.copy2(src_path, dst_path)