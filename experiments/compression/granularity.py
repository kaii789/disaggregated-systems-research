#!/usr/bin/env python
from base import *

def run_gran(config_name, benchmark_name, x_axis, x_axis_label, x_axis_config_param, program_command, result_name, cwd=None
):
    # Multithread
    res1 = []
    t1 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "bdi-{}".format(benchmark_name), os.path.abspath(config_name), x_axis_config_param, program_command, res1, cwd))

    t1.start()
    t1.join()

    bdi = res1[0]

    data = {
        x_axis_label: x_axis,
        'IPC': bdi
    }
    df = pd.DataFrame(data)
    graph = df.plot(x=x_axis_label, y="IPC")
    fig = graph.get_figure()
    fig.savefig("{}.png".format(result_name))

if __name__ == "__main__":
    # IPC vs Compression Gran
    x_axis_label = "Compression Granularity(bytes)"
    x_axis_config_param = "perf_model/dram/compression_model/compression_granularity"
    program_info = [
        # ("sssp", "../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/bcsstk05.mtx 1", None),
        # ("ligra-bfs", "../../../benchmarks/ligra/apps/BFS -s -rounds 1 ../../../benchmarks/ligra/inputs/rMat_1000000", None),
        ("ligra-pagerank", "../../../benchmarks/ligra/apps/PageRank -s -rounds 1 ../../../benchmarks/ligra/inputs/rMat_1000000", None),
        ("tinynet", "./darknet classifier predict cfg/imagenet1k.data cfg/darknet19.cfg tiny.weights data/dog.jpg", "../../benchmarks/darknet")
    ]

    # For each benchmark, launch sweep w/ bdi
    bdi_gran = [32, 64, 128, 256]
    result_name = "bdi_ipc_vs_compression_gran"
    for benchmark_name, program_command, cwd in program_info:
        t = threading.Thread(target=run_gran, args=("./bdi", benchmark_name, bdi_gran, x_axis_label, x_axis_config_param, program_command, result_name, cwd))
        t.start()

    # For each benchmark, launch sweep w/ lz4
    lz4_gran = [1024, 2048, 4096]
    result_name = "lz4_ipc_vs_compression_gran"
    for benchmark_name, program_command, cwd in program_info:
        t = threading.Thread(target=run_gran, args=("./lz4", benchmark_name, lz4_gran, x_axis_label, x_axis_config_param, program_command, result_name, cwd))
        t.start()
