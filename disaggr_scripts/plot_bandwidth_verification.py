import os
import numpy as np
import natsort
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import interpolate

from typing import Any, Callable, Dict, List, Optional, TextIO, TypeVar

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


def save_pdf_histogram(cdf_x, cdf_y, output_directory_path, num_bins=20):
    """Save a graph of a scaled histogram that approximates the shape of the PDF."""
    plt.clf()

    cdf_approx = interpolate.interp1d(cdf_x, cdf_y)  # 1D interpolation between points
    x_axis = np.linspace(cdf_x[0], cdf_x[-1], num_bins)

    heights = []
    for i in range(len(x_axis) - 1):
        # Calculate probability of bin using difference of approx CDF
        heights.append(cdf_approx(x_axis[i + 1]) - cdf_approx(x_axis[i]))

    # print(sum(heights))  # Should be close to 1
    if abs(sum(heights) - 1) > 0.1:
        print("Scaled PDF histogram might be very inaccurate")

    # For graphing, scale to have the tallest bar have height 1
    heights = np.array(heights)
    heights /= np.max(heights)

    # plt.plot(cdf_x, cdf_y, "r.")
    plt.bar(x_axis[:-1], heights, align="edge", width=(cdf_x[-1] - cdf_x[0]) / num_bins)

    title_str = "Effective Bandwidth PDF Histogram"
    plt.title(title_str)
    plt.xlabel("Effective Bandwidth (GB/s)")
    plt.ylabel("Scaled Density")
    graph_filename = "{}.png".format(title_str)
    plt.savefig(os.path.join(output_directory_path, graph_filename))


def save_cdf_graph(cdf_x, cdf_y, output_directory_path):
    """Save a graph of the CDF, from generated CDF points."""
    plt.clf()

    plt.plot(cdf_x, cdf_y)

    title_str = "Effective Bandwidth CDF"
    plt.title(title_str)
    plt.xlabel("Effective Bandwidth (GB/s)")
    plt.ylabel("Probability")
    # plt.axvline(x=70000000)  # For local DRAM size graph
    # plt.legend()
    # Note: .png files are deleted by 'make clean' in the test/shared Makefile in the original repo
    graph_filename = "{}.png".format(title_str)
    plt.savefig(os.path.join(output_directory_path, graph_filename))


def save_cdf_pdf_histogram_combined(
    cdf_x, cdf_y, output_directory_path, histogram_num_bins=20
):
    """Save a graph of a scaled histogram that approximates the shape of the PDF,
    plus the original CDF points used.
    """
    plt.clf()

    # Scaled histogram, approximating the shape of the PDF
    cdf_approx = interpolate.interp1d(cdf_x, cdf_y)  # 1D interpolation between points
    x_axis = np.linspace(cdf_x[0], cdf_x[-1], histogram_num_bins)
    heights = []
    for i in range(len(x_axis) - 1):
        # Calculate probability of bin using difference of approx CDF
        heights.append(cdf_approx(x_axis[i + 1]) - cdf_approx(x_axis[i]))
    # print(sum(heights))  # Should be close to 1
    if abs(sum(heights) - 1) > 0.1:
        print("Scaled PDF histogram might be very inaccurate")

    # For graphing, scale to have the tallest bar have height 1
    heights = np.array(heights)
    heights /= np.max(heights)
    plt.bar(
        x_axis[:-1],
        heights,
        align="edge",
        width=(cdf_x[-1] - cdf_x[0]) / histogram_num_bins,
        label="PDF Histogram",
    )

    # Plot points of CDF
    plt.plot(cdf_x, cdf_y, "r.", label="CDF Points")

    title_str = "Effective Bandwidth PDF Histogram and CDF"
    plt.title(title_str)
    plt.xlabel("Effective Bandwidth (GB/s)")
    plt.ylabel("Scaled Density (PDF) / Probability (CDF)")

    plt.xticks(np.arange(0, cdf_x[-1] + 0.25, step=0.5))
    plt.ylim(bottom=0, top=1.0)
    plt.yticks(np.arange(0, 1 + 0.01, step=0.1))  # +0.01 to include 1

    plt.legend()
    # Note: .png files are deleted by 'make clean' in the test/shared Makefile in the original repo
    graph_filename = "{}.png".format(title_str)
    plt.savefig(os.path.join(output_directory_path, graph_filename))


def extract_effective_bandwidth(log_file: TextIO):
    experiment_run_info: Dict[int, BandwidthInfo]

    line = log_file.readline()
    experiment_run_info = {}
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

        else:
            line = log_file.readline()
    return experiment_run_info


def plot_grouped_bar_chart(output_directory_path: PathLike, bw_info: Dict[int, BandwidthInfo]):
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
    percentages = ["0.975", "0.95"]

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

    # Debug output
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
    data_y_max = max([max(page_queue_bws[p]) for p in percentages])
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
    # Lines for bandwidth_verification experiments with 4 runs
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

                plot_grouped_bar_chart(directory_path, bw_info)
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
            print("{:45}: {}".format(stat_settings[i].name_for_legend, y_value_list))

    if log_file:  # Also print to log file
        print("Y values:", file=log_file)
        for i, y_value_list in enumerate(y_values):
            print(
                "{:45}: {}".format(stat_settings[i].name_for_legend, y_value_list),
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


if __name__ == "__main__":
    # with open("/home/jonathan/Desktop/percentages.txt", "r") as file:
    #     line = file.readline()
    #     num_strs = []
    #     while line.strip():
    #         num_str = (line.strip().split()[1])[:-1]
    #         num_strs.append(num_str)
    #         line = file.readline()
    #     print(num_strs)

    sssp_bcsstk05_cdf_x = [
        0,
        0,
        0.190398,
        0.3769,
        0.379358,
        0.39047,
        0.747779,
        0.753386,
        0.762866,
        0.907126,
        1.17138,
        1.17394,
        1.25185,
        1.28893,
        1.44597,
        1.45645,
        1.46923,
        1.52127,
        1.79178,
        1.86711,
        1.94308,
        1.97058,
        2.21415,
        2.21811,
        2.22284,
        2.28596,
        2.32256,
        2.32505,
        2.55513,
        2.65812,
        2.67498,
        2.80952,
        3.03,
        3.03678,
        3.28826,
        3.45606,
        3.46011,
        3.6034,
        4.01313,
        4.47889,
    ]
    sssp_bcsstk05_cdf_y = [
        0,
        0.025,
        0.05,
        0.075,
        0.1,
        0.125,
        0.15,
        0.175,
        0.2,
        0.225,
        0.25,
        0.275,
        0.3,
        0.325,
        0.35,
        0.375,
        0.4,
        0.425,
        0.45,
        0.475,
        0.5,
        0.525,
        0.55,
        0.575,
        0.6,
        0.625,
        0.65,
        0.675,
        0.7,
        0.725,
        0.75,
        0.775,
        0.8,
        0.825,
        0.85,
        0.875,
        0.9,
        0.925,
        0.95,
        0.975,
    ]

    sssp_bcsstk25_cdf_x = [
        0,
        0.559854,
        0.762761,
        0.923754,
        1.04451,
        1.17067,
        1.27998,
        1.39552,
        1.51947,
        1.5933,
        1.71564,
        1.83418,
        1.91549,
        2.00796,
        2.12478,
        2.23327,
        2.29523,
        2.37516,
        2.44576,
        2.51614,
        2.58918,
        2.64361,
        2.7023,
        2.77545,
        2.84459,
        2.9319,
        3.00388,
        3.08891,
        3.18234,
        3.28635,
        3.38859,
        3.4972,
        3.60925,
        3.71783,
        3.83909,
        3.96273,
        4.09339,
        4.25208,
        4.43857,
        4.72352,
    ]
    sssp_bcsstk25_cdf_y = [
        0,
        0.025,
        0.05,
        0.075,
        0.1,
        0.125,
        0.15,
        0.175,
        0.2,
        0.225,
        0.25,
        0.275,
        0.3,
        0.325,
        0.35,
        0.375,
        0.4,
        0.425,
        0.45,
        0.475,
        0.5,
        0.525,
        0.55,
        0.575,
        0.6,
        0.625,
        0.65,
        0.675,
        0.7,
        0.725,
        0.75,
        0.775,
        0.8,
        0.825,
        0.85,
        0.875,
        0.9,
        0.925,
        0.95,
        0.975,
    ]

    output_directory_path = "."
    # save_cdf_graph(cdf_x, cdf_y, output_directory_path)
    # save_pdf_histogram(cdf_x, cdf_y, output_directory_path)

    # save_cdf_pdf_histogram_combined(sssp_bcsstk25_cdf_x, sssp_bcsstk25_cdf_y, output_directory_path)

    with open(os.path.join(output_directory_path, "Stats.txt"), "w") as log_file:
        passed_over_directories = []
        for filename in natsort.os_sorted(os.listdir(output_directory_path)):
            filename_path = os.path.join(output_directory_path, filename)
            if (
                os.path.isdir(filename_path)
                and not filename.startswith("process_")
                and "verification_series" in filename
            ):
                # Generate bar plot graph
                process_bandwidth_verification_series_directory(filename_path)
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
                        StatSetting(
                            "remote datamovement % queue capped by custom cap",
                            float,
                            name_for_legend="datamovement capped by custom cap (%)",
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
                            "remote datamovement2 % queue capped by custom cap",
                            float,
                            name_for_legend="datamovement2 capped by custom cap (%)",
                        ),
                    ],
                )
                # print()
                print(file=log_file)

            elif os.path.isdir(filename_path):
                passed_over_directories.append(filename)
        if len(passed_over_directories) > 0:
            print("\nPassed over {} directories:".format(len(passed_over_directories)))
            for dirname in passed_over_directories:
                print("  {}".format(dirname))
