import pandas as pd
import numpy as np
import matplotlib as plt
plt.use('Agg')
import stats

def graph(res_name, benchmark_list, local_dram_list, bw_scalefactor_list):
    labels = ["Remote Bandwidth Scalefactor", "Compression Off", "Page Compression(ideal)", "Cacheline + Page Compression(ideal)", "Page Compression", "Cacheline + Page Compression"]
    # "stream_{}_localdram_{}_netlat_{}_bw_scalefactor_{}_combo"

    process = 0
    num_bars = len(labels) - 1
    res = [bw_scalefactor_list[:]] + [[] for _ in range(num_bars)]
    compression_res = {}
    for benchmark in benchmark_list:
        for size in local_dram_list:
            for factor in bw_scalefactor_list:
                dir1 = "{}localdram_{}_netlat_120_bw_scalefactor_{}_combo_output_files".format(benchmark, size, factor)
                for run in range(1, 1 + num_bars):
                    dir2 = "run_{}_process_{}_temp".format(run, process)
                    res_dir = "./{}/{}".format(dir1, dir2)
                    ipc = stats.get_ipc(res_dir)
                    res[run].append(ipc)

                    # Compression res
                    if run in range(2, 1 + num_bars):
                        type = "{}-{}".format(run - 1, factor)
                        compression_res[type] = {}
                        cr, cl, dl, ccr, ccl, cdl = stats.get_compression_stats(res_dir)
                        compression_res[type]['Compression Ratio'] = cr
                        compression_res[type]['Compression Latency'] = cl
                        compression_res[type]['Decompression Latency'] = dl
                        if ccr:
                            compression_res[type]['Cacheline Compression Ratio'] = ccr
                            compression_res[type]['Cacheline Compression Latency'] = ccl
                            compression_res[type]['Cacheline Decompression Latency'] = cdl

                    process += 1

    data = {labels[i]: res[i] for i in range(len(labels))}
    # print(data)
    print(compression_res)
    df = pd.DataFrame(data)
    graph = df.plot(x=labels[0], y=labels[1:], kind="bar", title=res_name)
    fig = graph.get_figure()
    fig.savefig(res_name)

def gen_settings_for_graph(benchmark_name):
    if benchmark_name == "sssp":
        res_name = "sssp_262144B_combo"
        benchmark_list = []
        for input in ["bcsstk05.mtx"]:
            benchmark_list.append("sssp_{}_".format(input))
        local_dram_list = ["262144B"]
        bw_scalefactor_list = [4, 32]
    elif benchmark_name == "bfs_reg":
        res_name = "bfs_reg_8MB_combo"
        benchmark_list = []
        benchmark_list.append("ligra_{}_".format("bfs"))
        local_dram_list = ["8MB"]
        bw_scalefactor_list = [4, 32]
    elif benchmark_name == "tinynet":
        res_name = "tinynet_2MB_combo"
        benchmark_list = []
        for model in ["tiny"]:
            benchmark_list.append("darknet_{}_".format(model))
        local_dram_list = ["2MB"]
        bw_scalefactor_list = [4, 32]
    elif benchmark_name == "darknet19":
        res_name = "tinynet_2MB_combo"
        benchmark_list = []
        for model in ["darknet19"]:
            benchmark_list.append("darknet_{}_".format(model))
        local_dram_list = ["2MB"]
        bw_scalefactor_list = [4, 32]
    elif benchmark_name == "stream_1":
        res_name = "stream_1_2MB_combo"
        benchmark_list = []
        benchmark_list.append("stream_1_")
        local_dram_list = ["2MB"]
        bw_scalefactor_list = [4, 32]

    return res_name, benchmark_list, local_dram_list, bw_scalefactor_list

if __name__ == "__main__":
    res_name, benchmark_list, local_dram_list, bw_scalefactor_list = gen_settings_for_graph("sssp")
    graph(res_name, benchmark_list, local_dram_list, bw_scalefactor_list)