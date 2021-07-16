#!/usr/bin/env python
from base import *

def run_compression_vs_no_compression_experiment(x_axis, x_axis_label, x_axis_config_param, program_command, result_name, cwd=None
):
    # Multithread
    res1, res2 = [], []
    t1 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "c0", os.path.abspath("./no_compression_no_partition_queues"), x_axis_config_param, program_command, res1, cwd))
    t2 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "c1", os.path.abspath("./yes_compression_no_partition_queues"), x_axis_config_param, program_command, res2, cwd))

    for t in [t1, t2]:
        t.start()

    for t in [t1, t2]:
        t.join()

    no_compression = res1[0]
    yes_compression = res2[0]

    data = {
        x_axis_label: x_axis,
        'C: Off': no_compression,
        'C: On': yes_compression
    }
    df = pd.DataFrame(data)
    graph = df.plot(x=x_axis_label, y=["C: Off", "C: On"], kind="bar")
    fig = graph.get_figure()
    fig.savefig(result_name)

if __name__ == "__main__":
    # Note: sniper is run in test/compression/{thread id}

    # IPC vs Bandwidth
    bandwidth_scalefactor = [4, 8, 16, 32]
    x_axis_label = "Remote Bandwidth Scalefactor"
    x_axis_config_param = "perf_model/dram/remote_mem_bw_scalefactor"
    program_command = "../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/bcsstk05.mtx 1"
    # program_command = "../../../benchmarks/ligra/apps/BFS -s -rounds 1 ../../../benchmarks/ligra/inputs/rMat_1000000" # TODO: change me
    result_name = "ipc_vs_bandwidth_scalefactor_bar"
    t1 = threading.Thread(target=run_compression_vs_no_compression_experiment, args=(bandwidth_scalefactor, x_axis_label, x_axis_config_param, program_command, result_name))

    # Darknet
    # program_command = "./darknet classifier predict cfg/imagenet1k.data cfg/darknet19.cfg tiny.weights data/dog.jpg" # TODO: change me
    # cwd = "../../benchmarks/darknet"
    # t1 = threading.Thread(target=run_compression_queue_experiment, args=(bandwidth_scalefactor, x_axis_label, x_axis_config_param, program_command, result_name, cwd))

    # IPC vs Local DRAM Size
    local_dram_size = [4194304, 8388608, 16777216, 33554432]
    # local_dram_size = [4000, 8000, 16000, 32000]
    x_axis_label = "Local DRAM Size(bytes)"
    x_axis_config_param = "perf_model/dram/localdram_size"
    program_command = "../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/bcsstk05.mtx 1"
    # program_command = "../../../benchmarks/ligra/apps/BFS -s -rounds 1 ../../../benchmarks/ligra/inputs/rMat_1000000" # TODO: change me
    result_name = "ipc_vs_local_dram_size_bar"
    # t2 = threading.Thread(target=run_compression_queue_experiment, args=(local_dram_size, x_axis_label, x_axis_config_param, program_command, result_name))

    t1.start()
    # t2.start()