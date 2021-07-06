#!/usr/bin/env python
from base import *

def sweep_thread_two_config(data, result_filename, config_name, config_param1, config_param2, config_param3, val1, val2, program_command, cwd):
    run_directory = "./{}-{}-{}-{}-{}".format(result_filename, config_param1.split("/")[-1], val1, config_param3.split("/")[-1], val2)
    sniper_path = os.path.abspath("../../run-sniper")
    output_directory = os.path.abspath("./{}".format(run_directory))
    if not cwd: cwd = run_directory
    command = "{} -v -n 1 -c {} -g --{}={} -g --{}={} -g --{}={} -d {} -- {}".format(sniper_path, config_name, config_param1, val1, config_param2, val1, config_param3, val2, output_directory, program_command)
    subprocess.call("mkdir {}".format(run_directory), shell=True)
    subprocess.call(command, shell=True, cwd=cwd)
    ipc = get_ipc(run_directory)
    print(ipc)
    data['IPC'].append(ipc)
    #log_compression_stats(run_directory, "{}.log".format(result_filename), program_command, config_param1, val1, config_param3, val2)

def run_experiment_two_config(x_axis, x_axis1, x_axis2, result_filename, config_name, config_param1, config_param2, config_param3, program_command, cwd):

    data = {x_axis:x_axis1,
            'IPC':[]}

    thread_pool = []
    for val1 in x_axis1:
        for val2 in x_axis1:
            t = threading.Thread(target=sweep_thread_two_config, args=(data, result_filename, config_name, config_param1, config_param2, config_param3, val1, val2, program_command, cwd))
            thread_pool.append(t)
            t.start()

    for t in thread_pool:
        t.join()

    # df = pd.DataFrame(data)
    # graph = df.plot(x=x_axis, y="IPC")
    # fig = graph.get_figure()
    # fig.savefig(result_filename)

    return data['IPC']

def thread_experiment_two_config(x_axis, x_axis1, x_axis2, result_filename, config_name, config_param1, config_param2, config_param3, program_command, res, cwd
):
    experiment_res = run_experiment_two_config(x_axis, x_axis1, x_axis2, result_filename, config_name, config_param1, config_param2, config_param3, program_command, cwd) # "{}-{}".format(result_filename, program_command)
    res.append(experiment_res)

def run_ideal_ratio(x_axis1, x_axis2, x_axis_label, x_axis_config_param, x_axis_config_param2, x_axis_config_param3, program_command, result_name, cwd=None
):
    # Multithread
    res1 = []
    t1 = threading.Thread(target=thread_experiment_two_config, args=(x_axis_label, x_axis1, x_axis2, "ratio", os.path.abspath("./yes_compression_no_partition_queues"), x_axis_config_param, x_axis_config_param2, x_axis_config_param3, program_command, res1, cwd))

    for t in [t1]:
        t.start()

    for t in [t1]:
        t.join()

    yes_compression = res1[0]

    data = {
        x_axis_label: x_axis,
        'C: On': yes_compression,
    }
    df = pd.DataFrame(data)
    graph = df.plot(x=x_axis_label, y=["C: On"], kind="bar")
    fig = graph.get_figure()
    fig.savefig(result_name)

def run_ideal_latency(x_axis, x_axis_label, x_axis_config_param, program_command, result_name, cwd=None
):
    # Multithread
    res1 = []
    t1 = threading.Thread(target=thread_experiment, args=(x_axis_label, x_axis, "latency", os.path.abspath("./yes_compression_no_partition_queues"), x_axis_config_param, program_command, res1, cwd))

    for t in [t1]:
        t.start()

    for t in [t1]:
        t.join()

    yes_compression = res1[0]

    data = {
        x_axis_label: x_axis,
        'C: On': yes_compression,
    }
    df = pd.DataFrame(data)
    graph = df.plot(x=x_axis_label, y=["C: On"], kind="bar")
    fig = graph.get_figure()
    fig.savefig(result_name)

if __name__ == "__main__":
    # IPC vs Compression/Decompression latency
    latency = [0, 50, 500, 2000]
    compressed_page_size = [64, 1024, 2048]
    x_axis_label = "Compression/Decompression Latency"
    x_axis_config_param = "perf_model/dram/compression_model/ideal/compression_latency"
    x_axis_config_param2 = "perf_model/dram/compression_model/ideal/decompression_latency"
    x_axis_config_param3 = "perf_model/dram/compression_model/ideal/compressed_page_size"
    #program_command = "../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/bcsstk05.mtx 1"
    program_command = "../../../benchmarks/ligra/apps/BFS -s -rounds 1 ../../../benchmarks/ligra/inputs/rMat_1000000" # TODO: change me
    result_name = "ipc_vs_compression_latency"
    t1 = threading.Thread(target=run_ideal_ratio, args=(latency, compressed_page_size, x_axis_label, x_axis_config_param, x_axis_config_param2, x_axis_config_param3, program_command, result_name))

    # Darknet
    # program_command = "./darknet classifier predict cfg/imagenet1k.data cfg/darknet19.cfg tiny.weights data/dog.jpg" # TODO: change me
    # cwd = "../../benchmarks/darknet"
    # t1 = threading.Thread(target=run_compression_queue_experiment, args=(bandwidth_scalefactor, x_axis_label, x_axis_config_param, program_command, result_name, cwd))

    # IPC vs Compressed Page Size
    #compressed_page_size = [64, 1024, 2048]
    #x_axis_label = "Compressed Page Size(bytes)"
    #x_axis_config_param = "perf_model/dram/compression_model/ideal/compressed_page_size"
    #program_command = "../../../test/crono/apps/sssp/sssp ../../../test/crono/inputs/bcsstk05.mtx 1"
    #program_command = "../../../benchmarks/ligra/apps/BFS -s -rounds 1 ../../../benchmarks/ligra/inputs/rMat_1000000" # TODO: change me
    #result_name = "ipc_vs_compressed_page_size"
    #t2 = threading.Thread(target=run_ideal_latency, args=(compressed_page_size, x_axis_label, x_axis_config_param, program_command, result_name))

    t1.start()
    #t2.start()
