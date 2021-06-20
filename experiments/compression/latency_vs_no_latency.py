#!/usr/bin/env python
from base import *

def run_latency_vs_no_latency(x_axis, x_axis_label, x_axis_config_param, program_command, result_name, cwd=None
):
    # Multithread
    res1, res2 = [], []
    t1 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "latency0", os.path.abspath("./no_compression_latency"), x_axis_config_param, program_command, res1, cwd))
    t2 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "latency1", os.path.abspath("./yes_compression_latency"), x_axis_config_param, program_command, res2, cwd))

    for t in [t1, t2]:
        t.start()

    for t in [t1, t2]:
        t.join()

    no_compression_latency = res1[0]
    yes_compression_latency = res2[0]

    data = {
        x_axis_label: x_axis,
        'CL: Off': no_compression_latency,
        'CL: On': yes_compression_latency,
    }
    df = pd.DataFrame(data)
    graph = df.plot(x=x_axis_label, y=["CL: Off", "CL: On"], kind="bar")
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
    t1 = threading.Thread(target=run_latency_vs_no_latency, args=(bandwidth_scalefactor, x_axis_label, x_axis_config_param, program_command, result_name))

    t1.start()