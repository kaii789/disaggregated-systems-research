#!/usr/bin/env python
from base import *

def run_gran(benchmark_name, x_axis, x_axis_label, x_axis_config_param, program_command, result_name, cwd=None
):
    # Multithread
    res1, res2, res3, res4, res5 = [], [], [], [], []
    t1 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "c0-{}".format(benchmark_name), os.path.abspath("./no_compression_no_partition_queues"), x_axis_config_param, program_command, res1, cwd))
    t2 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "bdi-{}".format(benchmark_name), os.path.abspath("./bdi"), x_axis_config_param, program_command, res2, cwd))
    t3 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "fpc-{}".format(benchmark_name), os.path.abspath("./fpc"), x_axis_config_param, program_command, res3, cwd))
    t4 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "lz4-{}".format(benchmark_name), os.path.abspath("./lz4"), x_axis_config_param, program_command, res4, cwd))
    t5 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "fve-{}".format(benchmark_name), os.path.abspath("./fve"), x_axis_config_param, program_command, res5, cwd))

    for t in [t1, t2, t3, t4, t5]:
        t.start()

    for t in [t1, t2, t3, t4, t5]:
        t.join()

    c0 = res1[0]
    bdi = res2[0]
    fpc = res3[0]
    lz4 = res4[0]
    fve = res5[0]

    data = {
        x_axis_label: x_axis,
        'c0': c0,
        'bdi': bdi,
        'fpc': fpc,
        'lz4': lz4,
        'fve': fve
    }
    df = pd.DataFrame(data)
    graph = df.plot(x=x_axis_label, y=["c0", "bdi", "fpc", "lz4", "fve"], kind="bar")
    fig = graph.get_figure()
    fig.savefig("{}-{}".format(benchmark_name, result_name))

if __name__ == "__main__":
    # IPC vs Compression Gran
    # Assume no compression/decompression latency for LZ4
    x_axis_label = "Remote Bandwidth Scalefactor"
    x_axis_config_param = "perf_model/dram/remote_mem_bw_scalefactor"
    program_info = [
        ("sssp-bcsstk05", "../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/bcsstk05.mtx 1", None),
        # ("sssp-bcsstk25", "../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/bcsstk25.mtx 1", None),
        # ("sssp-roadNet-PA", "../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/roadNet-PA.mtx 1", None),
        # ("spdmv-bcsstk25", "../../../benchmarks/spmv/bench_spdmv  ../../../test/crono/inputs/bcsstk25.mtx 1 1", None),
        # ("spdmv-roadNet-PA", "../../../benchmarks/spmv/bench_spdmv  ../../../test/crono/inputs/roadNet-PA.mtx 1 1", None),
        # ("stream-copy", "../../../benchmarks/stream/stream_sniper 0", None),
        # ("stream-scale", "../../../benchmarks/stream/stream_sniper 1", None),
        # ("stream-add", "../../../benchmarks/stream/stream_sniper 2", None),
        # ("stream-triad", "../../../benchmarks/stream/stream_sniper 3", None),
        # ("ligra-bfs", "../../../benchmarks/ligra/apps/BFS -s -rounds 1 ../../../benchmarks/ligra/inputs/rMat_1000000", None),
        # ("ligra-pagerank", "../../../benchmarks/ligra/apps/PageRank -s -rounds 1 ../../../benchmarks/ligra/inputs/rMat_1000000", None),
        # ("tinynet", "./darknet classifier predict cfg/imagenet1k.data cfg/darknet19.cfg tiny.weights data/dog.jpg", "../../benchmarks/darknet")
    ]

    # For each benchmark, launch sweep
    bandwidth_scalefactor = [4, 32]
    result_name = "ipc_vs_bandwidth_scalefactor_bar"
    for benchmark_name, program_command, cwd in program_info:
        t = threading.Thread(target=run_gran, args=(benchmark_name, bandwidth_scalefactor, x_axis_label, x_axis_config_param, program_command, result_name, cwd))
        t.start()

