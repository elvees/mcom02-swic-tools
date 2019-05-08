#!/usr/bin/env python3

# Copyright 2019 RnD Center "ELVEES", JSC

import argparse
import csv
import os

import matplotlib.pyplot as plt
import numpy


def group(lst, num_elem):
    return list(zip(*[iter(lst)] * num_elem))


def count_rows(input_file):
    with open(input_file) as file_:
        reader = csv.DictReader(file_)
        return sum(1 for row in reader)


def fill_data(input_file, raw_throughput, raw_rx_speed,
              raw_tx_speed, raw_mtu, row_count):
    with open(input_file) as file_:
        reader = csv.DictReader(file_)
        for row in reader:
            raw_throughput.append(float(row['Throughput, Mbit/s']))
            raw_rx_speed.append(float(row['Receiver TX speed, Mbit/s']))
            raw_tx_speed.append(float(row['Transmitter TX speed, Mbit/s']))
            raw_mtu.append(float(row['MTU, bytes']))
    for i in range(row_count):
        theor_throughput = 8 / (10 / raw_tx_speed[i] + 4 / (56 * raw_rx_speed[i]))
        rel_raw_throughput.append(raw_throughput[i] / theor_throughput)


def count_num_measurements(data1, data2, row_count):
    comb = zip(data1, data2)
    uniq_comb = len(set(comb))
    return int(row_count / uniq_comb)


def plot_test_speed(input_file,
                    rel_raw_throughput,
                    raw_throughput, raw_tx_speed,
                    raw_rx_speed,
                    throughput, tx_speed, raw_mtu):
    rx_speed = []
    rel_throughput = []

    results_dir = os.path.dirname(os.path.abspath(input_file))

    row_count = count_rows(input_file)

    fill_data(input_file, raw_throughput, raw_rx_speed,
              raw_tx_speed, raw_mtu, row_count)

    num_msr = count_num_measurements(raw_tx_speed, raw_rx_speed, row_count)

    rx_speed = group(raw_rx_speed, num_msr)
    tx_speed = group(raw_tx_speed, num_msr)
    throughput = group(raw_throughput, num_msr)
    rel_throughput = group(rel_raw_throughput, num_msr)

    for i in range(row_count // num_msr):
        rx_speed[i] = rx_speed[i][0]
        tx_speed[i] = tx_speed[i][0]
        throughput[i] = numpy.mean(throughput[i])
        rel_throughput[i] = numpy.mean(rel_throughput[i])

    tx_speed = sorted(list(set(tx_speed)), reverse=True)
    points = int(row_count / num_msr / len(tx_speed))
    graphs = len(tx_speed)

    throughput = group(throughput, points)
    rel_throughput = group(rel_throughput, points)
    rx_speed = group(rx_speed, points)

    plt.figure(figsize=(10, 5))
    plt.scatter(raw_rx_speed, raw_throughput, s=5, color='black')
    for i in range(graphs):
        plt.plot(rx_speed[i], throughput[i],
                 label='Transmitter TX speed = %.1f Mbit/s' % tx_speed[i])
    plt.title('The dependence of the SWIC channel throughput on the receiver TX speed')
    plt.xlabel('Receiver TX speed, Mbit/s')
    plt.ylabel('Throughput, Mbit/s')
    legend = plt.legend(title='MTU = %d bytes' % list(set(raw_mtu))[0],
                        fontsize=8, loc='center right', prop={'size': 8})
    plt.setp(legend.get_title(), fontsize=8)
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.grid()
    plt.savefig(os.path.join(results_dir, 'swic-rtx-tput.png'), dpi=1200)

    plt.figure(figsize=(10, 5))
    plt.scatter(raw_rx_speed, rel_raw_throughput, s=5, color='black')
    for i in range(graphs):
        plt.plot(rx_speed[i], rel_throughput[i],
                 label='Transmitter TX speed = %.1f Mbit/s' % tx_speed[i])
    plt.title('The dependence of the SWIC channel relative throughput on the receiver TX speed')
    plt.xlabel('Receiver TX speed, Mbit/s')
    plt.ylabel('Throughput / Theoretic throughput')
    legend = plt.legend(title='MTU = %d bytes' % list(set(raw_mtu))[0],
                        fontsize=8, loc='best', prop={'size': 8})
    plt.setp(legend.get_title(), fontsize=8)
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.grid()
    plt.savefig(os.path.join(results_dir, 'swic-rtx-rel-tput.png'), dpi=1200)


def plot_test_mtu(input_file,
                  rel_raw_throughput,
                  raw_throughput, raw_tx_speed,
                  raw_rx_speed,
                  throughput, tx_speed, raw_mtu):
    mtu = []

    row_count = count_rows(input_file)
    results_dir = os.path.dirname(os.path.abspath(input_file))

    fill_data(input_file, raw_throughput, raw_rx_speed,
              raw_tx_speed, raw_mtu, row_count)

    num_msr = count_num_measurements(raw_tx_speed, raw_mtu, row_count)

    tx_speed = group(raw_tx_speed, num_msr)
    throughput = group(raw_throughput, num_msr)
    mtu = group(raw_mtu, num_msr)

    for i in range(row_count // num_msr):
        tx_speed[i] = tx_speed[i][0]
        throughput[i] = numpy.mean(throughput[i])
        mtu[i] = numpy.mean(mtu[i])

    tx_speed = sorted(list(set(tx_speed)), reverse=True)
    points = int(row_count / num_msr / len(tx_speed))
    graphs = len(tx_speed)

    throughput = group(throughput, points)
    mtu = group(mtu, points)

    plt.figure(figsize=(10, 5))
    plt.scatter(raw_mtu, raw_throughput, s=5, color='black')
    for i in range(graphs):
        plt.semilogx(mtu[i], throughput[i],
                     label='Transmitter TX speed = %.1f Mbit/s' % tx_speed[i])
    plt.title('The dependence of the SWIC channel throughput on the MTU size')
    plt.xlabel('MTU (packet size), bytes')
    plt.ylabel('Throughput, Mbit/s')
    legend = plt.legend(title='Receiver TX speed = %.1f Mbit/s' % list(set(raw_tx_speed))[0],
                        fontsize=8, loc='center right', prop={'size': 8})
    plt.setp(legend.get_title(), fontsize=8)
    plt.xlim(left=100)
    plt.ylim(bottom=0)
    plt.grid()
    plt.savefig(os.path.join(results_dir, 'swic-mtu-tput.png'), dpi=1200)


if __name__ == "__main__":
    rel_raw_throughput = []
    raw_throughput = []
    raw_tx_speed = []
    raw_rx_speed = []
    throughput = []
    tx_speed = []
    raw_mtu = []

    parser = argparse.ArgumentParser()
    parser.add_argument('test_type', choices=['test_speed',
                                              'test_mtu'])
    parser.add_argument('--results_dir', default='results')

    args = parser.parse_args()
    if args.test_type is None:
        parser.print_help()
    if args.test_type == 'test_speed':
        plot_test_speed(os.path.join(args.results_dir, 'data-test-speed.csv'),
                        rel_raw_throughput,
                        raw_throughput, raw_tx_speed, raw_rx_speed,
                        throughput, tx_speed, raw_mtu)
    if args.test_type == 'test_mtu':
        plot_test_mtu(os.path.join(args.results_dir, 'data-test-mtu.csv'),
                      rel_raw_throughput,
                      raw_throughput, raw_tx_speed, raw_rx_speed,
                      throughput, tx_speed, raw_mtu)
