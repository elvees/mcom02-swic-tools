#!/usr/bin/env python3

# Copyright 2019-2020 RnD Center "ELVEES", JSC

import argparse
import csv
import math
import os
import re
import subprocess


def save_log(dev, mode, throughput_app, total_time, tx_speed, mtu_list):
    log = []

    for i in range(len(mtu_list)):
        log.append({'Device': dev[i],
                    'Mode': mode[i],
                    'Throughput, Mbit/s': throughput_app[i],
                    'Total time, s': total_time[i],
                    'TX speed, Mbit/s': tx_speed[i],
                    'MTU, bytes': mtu_list[i]})

    with open('/tmp/log.csv', 'a') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=log_fieldnames)
        writer.writerows(log)


def save_info_to_file(filename, tx_speed, rx_speed, tm, mtu_list):
    info = []

    data_fieldnames = ['Transmitter TX speed, Mbit/s',
                       'Receiver TX speed, Mbit/s',
                       'Bytes, bytes',
                       'Time, s',
                       'Throughput, Mbit/s',
                       'MTU, bytes']

    for i in range(len(mtu_list)):
        info.append({'Transmitter TX speed, Mbit/s': tx_speed[i],
                     'Receiver TX speed, Mbit/s': rx_speed[i],
                     'Bytes, bytes': filesize,
                     'Time, s': tm[i],
                     'Throughput, Mbit/s': 8 * filesize / (float(tm[i]) * 1024*1024),
                     'MTU, bytes': mtu_list[i]})

    with open('/tmp/' + filename, 'w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=data_fieldnames)
        writer.writeheader()
        writer.writerows(info)


def run_procs(list_of_lists_of_args):
    stdouts = []
    process = []

    for i, proc in enumerate(list_of_lists_of_args):
        process.append(subprocess.Popen(proc,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT))

    for i, proc in enumerate(process):
        stdouts.append(proc.communicate()[0])

    for proc, stdout in zip(process, stdouts):
        if proc.returncode != 0:
            print('Non zero return code, stdout/stderr: {}'.format(
                                         stdout.decode('UTF-8')))
    return stdouts


def check(inputfile, outputfile, speed_tx, speed_rx, mtu, packets, stdouts):
    with open(inputfile, 'wb') as fout:
        fout.write(os.urandom(filesize))

    run_procs([
        ['swic',
         '--speed', str(speed_tx),
         '--mtu', str(mtu),
         '--link', 'up',
         '/dev/spacewire0'
         ],
        ['swic',
         '--speed', str(speed_rx),
         '--mtu', str(mtu),
         '--link', 'up',
         '/dev/spacewire1'
         ]
        ])

    stdouts = run_procs([
        ['swic-xfer',
         '/dev/spacewire0',
         's',
         '-f', inputfile,
         '-v'],
        ['swic-xfer',
         '/dev/spacewire1',
         'r',
         '-f', outputfile,
         '-n', str(packets),
         '-v'],
        ])

    run_procs([
        ['swic', '--link', 'down', '/dev/spacewire0'],
        ['swic', '--link', 'down', '/dev/spacewire1'],
        ])

    if args.v:
        print('data exchange with tx_speed = {}, rx_speed = {}, mtu = {} is successful'
              .format(speed_tx, speed_rx, mtu))
    return stdouts


def save_output_data(output1, output2, dev, mode, throughput_app, total_time, tm):
    for output in (output1, output2):
        total_time.append(re.findall(r'Total time: (\d+.\d+)', output)[0])
        mode.append(re.findall(r'Transfer mode: (\w+)', output)[0])

    throughput_app.append(re.findall(r'Throughput of transmit: (\d+.\d+)', output1)[0])
    dev.append(re.findall('Transmission device: (.+)', output1)[0])

    tm.append(re.findall(r'Received elapsed time: (\d+.\d+)', output2)[0])
    throughput_app.append(re.findall(r'Throughput of receive: (\d+.\d+)', output2)[0])
    dev.append(re.findall('Receiving device: (.+)', output2)[0])


def save_input_data(collections, values):
    for collect, value in zip(collections, values):
        collect.append(value)


def test_speed(throughput_app, total_time, rx_speed, tx_speed, mtu_list, mode, dev, tm, stdouts):
    tx_speed_pool = [408, 120, 4.8]
    rx_speed_pool = [408, 360, 312, 264, 216, 168, 120, 72, 4.8, 2.4]

    packets = math.ceil(filesize / mtu)

    for speed_tx in tx_speed_pool:
        for speed_rx in rx_speed_pool:
            for i in range(num_msr):
                save_input_data([tx_speed, rx_speed, mtu_list], [speed_tx, speed_rx, mtu])
                stdouts = check(inputfile, outputfile, speed_tx, speed_rx, mtu, packets, stdouts)
                save_output_data(stdouts[0].decode("utf-8"),
                                 stdouts[1].decode("utf-8"),
                                 dev, mode, throughput_app,
                                 total_time, tm)

    save_info_to_file("data-test-speed.csv", tx_speed, rx_speed, tm, mtu_list)
    save_log(dev, mode, throughput_app, total_time, tx_speed, mtu_list)


def test_mtu(throughput_app, total_time, rx_speed, tx_speed, mtu_list, mode, dev, tm, stdouts):
    tx_speed_pool = [408, 120, 4.8]
    speed_rx = 408
    mtu_pool = [128, 512, 1024,  5120, 10240, 16384]

    for speed_tx in tx_speed_pool:
        for mtu in mtu_pool:
            for i in range(num_msr):
                packets = math.ceil(filesize / mtu)

                save_input_data([tx_speed, rx_speed, mtu_list], [speed_tx, speed_rx, mtu])
                stdouts = check(inputfile, outputfile, speed_tx, speed_rx, mtu, packets, stdouts)
                save_output_data(stdouts[0].decode("utf-8"),
                                 stdouts[1].decode("utf-8"),
                                 dev, mode, throughput_app,
                                 total_time, tm)

    save_info_to_file("data-test-mtu.csv", tx_speed, rx_speed, tm, mtu_list)
    save_log(dev, mode, throughput_app, total_time, tx_speed, mtu_list)


if __name__ == '__main__':
    throughput_app = []
    total_time = []
    rx_speed = []
    tx_speed = []
    mtu_list = []
    mode = []
    dev = []
    tm = []
    stdouts = [None, None]

    outputfile = '/tmp/output.bin'
    inputfile = '/tmp/input.bin'

    log_fieldnames = ['Device',
                      'Mode',
                      'Throughput, Mbit/s',
                      'Total time, s',
                      'TX speed, Mbit/s',
                      'MTU, bytes']

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', help='input_file_size', default=1024*1024)
    parser.add_argument('-n', help='number_of_measurements', default=2)
    parser.add_argument('-m', help='mtu', default=1024*1024)
    parser.add_argument('-v', help='enable debug info')

    args = parser.parse_args()
    num_msr = args.n
    filesize = args.i
    mtu = args.m

    with open('/tmp/log.csv', 'w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=log_fieldnames)
        writer.writeheader()

    test_speed(throughput_app, total_time, rx_speed, tx_speed, mtu_list, mode, dev, tm, stdouts)

    throughput_app = []
    total_time = []
    rx_speed = []
    tx_speed = []
    mtu_list = []
    mode = []
    dev = []
    tm = []

    test_mtu(throughput_app, total_time, rx_speed, tx_speed, mtu_list, mode, dev, tm, stdouts)

    os.remove(inputfile)
    os.remove(outputfile)
