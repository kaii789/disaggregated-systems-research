#!/usr/bin/env python
from base import *

def run_gran(config_name, compression_name, benchmark_name, x_axis, x_axis_label, x_axis_config_param, program_command, result_name, cwd=None
):
    # Multithread
    res1 = []
    t1 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "multipage-{}-{}".format(compression_name, benchmark_name), os.path.abspath(config_name), x_axis_config_param, program_command, res1, cwd))

    t1.start()
    t1.join()

    multipage = res1[0]

    data = {
        x_axis_label: x_axis,
        'IPC': multipage
    }
    df = pd.DataFrame(data)
    graph = df.plot(x=x_axis_label, y="IPC")
    fig = graph.get_figure()
    fig.savefig("{}.png".format(result_name))

if __name__ == "__main__":
    # IPC vs Compression Gran
    # Assume no compression/decompression latency
    x_axis_label = "Page Buffer Size"
    x_axis_config_param = "perf_model/dram/multipage/page_buffer_capacity"
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

    # For each benchmark, launch sweep w/ lz4
    num_pages = [1, 5, 10, 20]
    result_name = "lz4_ipc_vs_page_buffer_size"
    compression_name = "lz4"
    for benchmark_name, program_command, cwd in program_info:
        t = threading.Thread(target=run_gran, args=("./multipage_lz4", compression_name, benchmark_name, num_pages, x_axis_label, x_axis_config_param, program_command, result_name, cwd))
        t.start()
