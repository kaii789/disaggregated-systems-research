#!/usr/bin/env python
from base import *

def run_gran(compression_name, benchmark_name, x_axis, x_axis_label, x_axis_config_param, program_command, result_name, cwd=None
):
    # Multithread
    res1, res2, res3 = [], [], []
    t1 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "multipage-no_compression-{}".format(benchmark_name), os.path.abspath("./multipage_no_compression"), x_axis_config_param, program_command, res1, cwd))
    t2 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "multipage-{}-cl0-{}".format(compression_name, benchmark_name), os.path.abspath("./multipage_lz4"), x_axis_config_param, program_command, res2, cwd))
    t3 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "multipage-{}-cl1-{}".format(compression_name, benchmark_name), os.path.abspath("./multipage_lz4_cl1"), x_axis_config_param, program_command, res3, cwd))

    for t in [t1, t2, t3]:
        t.start()

    for t in [t1, t2, t3]:
        t.join()

    multipage_no_compression = res1[0]
    multipage_yes_compression_no_latency = res2[0]
    multipage_yes_compression_yes_latency = res3[0]

    data = {
        x_axis_label: x_axis,
        'C: Off': multipage_no_compression,
        'C: On, CL: Off': multipage_yes_compression_no_latency,
        'C: On, CL: On': multipage_yes_compression_yes_latency
    }
    df = pd.DataFrame(data)
    graph = df.plot(x=x_axis_label, y=["C: Off", "C: On, CL: Off", "C: On, CL: On"], kind="bar")
    fig = graph.get_figure()
    fig.savefig(result_name)

if __name__ == "__main__":
    # IPC vs Compression Gran
    # Assume no compression/decompression latency
    x_axis_label = "Page Buffer Size"
    x_axis_config_param = "perf_model/dram/multipage/page_buffer_capacity"
    program_info = [
        ("sssp", "../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/bcsstk05.mtx 1", None),
        # ("ligra-bfs", "../../../benchmarks/ligra/apps/BFS -s -rounds 1 ../../../benchmarks/ligra/inputs/rMat_1000000", None),
        # ("ligra-pagerank", "../../../benchmarks/ligra/apps/PageRank -s -rounds 1 ../../../benchmarks/ligra/inputs/rMat_1000000", None),
        # ("ligra-pagerank", "../../../benchmarks/ligra/apps/PageRank -s -rounds 1 ../../../benchmarks/ligra/inputs/sx-mathoverflow-ligra", None),
        # ("tinynet", "./darknet classifier predict cfg/imagenet1k.data cfg/darknet19.cfg tiny.weights data/dog.jpg", "../../benchmarks/darknet")
    ]

    # For each benchmark, launch sweep w/ lz4
    num_pages = [1, 5, 10, 20]
    result_name = "lz4_ipc_vs_page_buffer_size"
    compression_name = "lz4"
    for benchmark_name, program_command, cwd in program_info:
        t = threading.Thread(target=run_gran, args=(compression_name, benchmark_name, num_pages, x_axis_label, x_axis_config_param, program_command, result_name, cwd))
        t.start()

