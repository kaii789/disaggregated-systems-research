import os
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import interpolate


def save_pdf_histogram(cdf_x, cdf_y, output_directory_path, num_bins = 20):
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
    plt.bar(x_axis[:-1], heights, align='edge', width=(cdf_x[-1] - cdf_x[0]) / num_bins)

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


def save_cdf_pdf_histogram_combined(cdf_x, cdf_y, output_directory_path, histogram_num_bins = 20):
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
    plt.bar(x_axis[:-1], heights, align='edge', width=(cdf_x[-1] - cdf_x[0]) / histogram_num_bins, label="PDF Histogram")

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


if __name__ == "__main__":
    sssp_bcsstk05_cdf_x = [0, 0, 0.190398, 0.3769, 0.379358, 0.39047, 0.747779, 0.753386, 0.762866, 0.907126, 1.17138, 1.17394, 1.25185, 1.28893, 1.44597, 1.45645, 1.46923, 1.52127, 1.79178, 1.86711, 1.94308, 1.97058, 2.21415, 2.21811, 2.22284, 2.28596, 2.32256, 2.32505, 2.55513, 2.65812, 2.67498, 2.80952, 3.03, 3.03678, 3.28826, 3.45606, 3.46011, 3.6034, 4.01313, 4.47889, ]
    sssp_bcsstk05_cdf_y = [0, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.175, 0.2, 0.225, 0.25, 0.275, 0.3, 0.325, 0.35, 0.375, 0.4, 0.425, 0.45, 0.475, 0.5, 0.525, 0.55, 0.575, 0.6, 0.625, 0.65, 0.675, 0.7, 0.725, 0.75, 0.775, 0.8, 0.825, 0.85, 0.875, 0.9, 0.925, 0.95, 0.975, ]
    
    sssp_bcsstk25_cdf_x = [0, 0.559854, 0.762761, 0.923754, 1.04451, 1.17067, 1.27998, 1.39552, 1.51947, 1.5933, 1.71564, 1.83418, 1.91549, 2.00796, 2.12478, 2.23327, 2.29523, 2.37516, 2.44576, 2.51614, 2.58918, 2.64361, 2.7023, 2.77545, 2.84459, 2.9319, 3.00388, 3.08891, 3.18234, 3.28635, 3.38859, 3.4972, 3.60925, 3.71783, 3.83909, 3.96273, 4.09339, 4.25208, 4.43857, 4.72352, ]
    sssp_bcsstk25_cdf_y = [0, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.175, 0.2, 0.225, 0.25, 0.275, 0.3, 0.325, 0.35, 0.375, 0.4, 0.425, 0.45, 0.475, 0.5, 0.525, 0.55, 0.575, 0.6, 0.625, 0.65, 0.675, 0.7, 0.725, 0.75, 0.775, 0.8, 0.825, 0.85, 0.875, 0.9, 0.925, 0.95, 0.975, ]

    output_directory_path = "."
    # save_cdf_graph(cdf_x, cdf_y, output_directory_path)
    # save_pdf_histogram(cdf_x, cdf_y, output_directory_path)
    save_cdf_pdf_histogram_combined(sssp_bcsstk25_cdf_x, sssp_bcsstk25_cdf_y, output_directory_path)
