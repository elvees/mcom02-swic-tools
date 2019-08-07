/*
 * Tool to send/receive file via SpaceWire interface on ELVEES MCom-02 SoC
 *
 * Copyright 2019 RnD Center "ELVEES", JSC
 *
 * SPDX-License-Identifier: GPL-2.0
 */

#include <errno.h>
#include <error.h>
#include <fcntl.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include <linux/elvees-swic.h>

#define print_verbose(fmt, arg...) if (verbose) printf(fmt, ##arg)

struct elvees_swic_speed speed;

int tx_speed = TX_SPEED_408;
int rx_speed;
int mtu = 16 * 1024;
int packets = -1;
int verbose = 0;

enum operation_type {
    SWIC_WRITE,
    SWIC_READ
};

static void swic_write(int fd, FILE *file)
{
    ssize_t written, transmitted = 0;
    struct timespec start, stop;
    uint64_t elapsed_time = 0;
    size_t bytes;

    if (ioctl(fd, SWICIOC_SET_MTU, mtu))
        error(EXIT_FAILURE, errno, "Failed to set MTU");

    void *tx_data = malloc(mtu);
    if (!tx_data)
        error(EXIT_FAILURE, 0, "Failed to allocate memory");

    while (!feof(file)) {
        bytes = fread(tx_data, 1, mtu, file);
        if (ferror(file))
            error(EXIT_FAILURE, errno, "Failed to read data from file");

        if (bytes == 0)
            break;

        clock_gettime(CLOCK_MONOTONIC, &start);
        written = write(fd, tx_data, bytes);
        clock_gettime(CLOCK_MONOTONIC, &stop);

        if (errno == ENOLINK)
            error(EXIT_FAILURE, errno, "Link is not set");
        else if (written != bytes)
            error(EXIT_FAILURE, 0, "Failed to write data");

        transmitted += written;

        elapsed_time += (stop.tv_sec * 1000000 + stop.tv_nsec  / 1000) -
                        (start.tv_sec * 1000000 + start.tv_nsec / 1000);

        if (packets != -1 && --packets == 0)
            break;
    }

    if (ioctl(fd, SWICIOC_GET_SPEED, &speed))
        error(EXIT_FAILURE, errno, "Failed to get RX speed");

    print_verbose("Tranmitter TX speed: %.1f Mbit/s\n", speed.tx / 1000.0);
    print_verbose("Tranmitter RX speed: %.1f Mbit/s\n", speed.rx / 1000.0);

    print_verbose("MTU (packet size): %d bytes\n", mtu);
    print_verbose("Transfered data size: %d bytes\n", transmitted);
    print_verbose("Transfered elapsed time: %f s\n", (double)elapsed_time / 1000000);
    print_verbose("Throughput of transmit: %f Mbit/s\n",
                  8 * (double)transmitted / (double)elapsed_time);

    free(tx_data);
}

static void swic_read(int fd, FILE *file)
{
    ssize_t read_bytes, sum_bytes = 0;
    struct timespec start, stop;
    uint64_t elapsed_time = 0;
    size_t written = 0;

    void *rx_data = malloc(ELVEES_SWIC_MAX_PACKET_SIZE);
    if (!rx_data)
        error(EXIT_FAILURE, 0, "Failed to allocate memory");

    while (1) {
        clock_gettime(CLOCK_MONOTONIC, &start);
        read_bytes = read(fd, rx_data, ELVEES_SWIC_MAX_PACKET_SIZE);
        clock_gettime(CLOCK_MONOTONIC, &stop);

        sum_bytes += read_bytes;

        elapsed_time += (stop.tv_sec * 1000000 + stop.tv_nsec  / 1000) -
                        (start.tv_sec * 1000000 + start.tv_nsec / 1000);

        if (errno == ENOLINK)
            error(EXIT_FAILURE, errno, "Link is not set");
        else if (read_bytes == 0)
            error(EXIT_FAILURE, errno, "Failed to read data");

        written = fwrite(rx_data, 1, read_bytes, file);
        fflush(file);

        if (written != read_bytes)
            error(EXIT_FAILURE, errno, "Failed to write data");

        if (packets != -1 && --packets == 0)
            break;
    }

    if (ioctl(fd, SWICIOC_GET_SPEED, &speed))
        error(EXIT_FAILURE, errno, "Failed to get RX speed");

    print_verbose("Receiver TX speed: %.1f Mbit/s\n", speed.tx / 1000.0);
    print_verbose("Receiver RX speed: %.1f Mbit/s\n", speed.rx / 1000.0);
    print_verbose("Received data size: %d bytes\n", sum_bytes);
    print_verbose("Received elapsed time: %f s\n", (double)elapsed_time / 1000000);
    print_verbose("Throughput of receive: %f Mbit/s\n",
                  8 * (double)sum_bytes / (double)elapsed_time);

    if (ioctl(fd, SWICIOC_SET_LINK, 0))
        error(EXIT_FAILURE, errno, "Failed to disconnect the link");

    free(rx_data);
}

static void help(const char *program_name)
{
        printf("Synopsys: %s input output [options]\n\n", program_name);
        puts("Options:");
        puts("    -n arg    number of packets");
        puts("    -s arg    TX speed");
        puts("    -m arg    maximum transmit unit (packet size)");
        puts("    -v        print verbose");
}

int main(int argc, char* argv[]) {
    const char *filename = NULL, *device = NULL;
    struct timespec start, stop;
    uint64_t total_time = 0;
    struct stat filestatus;
    int opt;

    clock_gettime(CLOCK_MONOTONIC, &start);

    while ((opt = getopt(argc, argv, "hn:s:m:v")) != -1) {
        switch (opt) {
            case 'h': help(argv[0]); return EXIT_SUCCESS;
            case 'n': packets = atoi(optarg); break;
            case 's': tx_speed = atoi(optarg); break;
            case 'm': mtu = atoi(optarg); break;
            case 'v': verbose++; break;
            default: error(EXIT_FAILURE, 0, "Try %s -h for help.", argv[0]);
        }
    }

    if (argc < optind + 2)
        error(EXIT_FAILURE, 0, "Not enough arguments");

    const char *from = argv[optind];
    const char *to = argv[optind + 1];

    enum operation_type optype;

    if (stat(from, &filestatus) == -1)
        error(EXIT_FAILURE, errno, "Failed to get file status");

    if ((filestatus.st_mode & S_IFMT) == S_IFREG) {
        optype = SWIC_WRITE;
        device = to;
        filename = from;
    } else if ((filestatus.st_mode & S_IFMT) == S_IFCHR) {
        optype = SWIC_READ;
        device = from;
        filename = to;
    } else
        error(EXIT_FAILURE, 0, "Unsupported file type");

    FILE *file = (optype == SWIC_WRITE) ? stdin : stdout;
    if (filename) {
        char *filemode = (optype == SWIC_WRITE) ? "rb" : "wb";
        file = fopen(filename, filemode);
        if (!file)
            error(EXIT_FAILURE, errno, "Failed to open %s file", filename);
    }

    int fd = open(device, O_RDWR);
    if (fd < 0)
        error(EXIT_FAILURE, errno, "Failed to open %s device", device);

    if (ioctl(fd, SWICIOC_SET_LINK, 1))
        error(EXIT_FAILURE, errno, "Failed to set link");

    enum swic_link_state link_status;

    print_verbose("Waiting for link...\n");
    while (1) {
        if (ioctl(fd, SWICIOC_GET_LINK_STATE, &link_status))
            error(EXIT_FAILURE, errno, "Failed to get link state");
        if (link_status == LINK_RUN) {
            print_verbose("Link is set\n");
            break;
        }
        usleep(10);
    }

    if (ioctl(fd, SWICIOC_SET_TX_SPEED, tx_speed))
        error(EXIT_FAILURE, errno, "Failed to set TX speed");

    if (optype == SWIC_WRITE) {
        print_verbose("Transfer mode: transmitter\n");
        print_verbose("Transmission device: %s\n", to);
        swic_write(fd, file);
    } else {
        print_verbose("Transfer mode: receiver\n");
        print_verbose("Receiving device: %s\n", from);
        swic_read(fd, file);
    }
    clock_gettime(CLOCK_MONOTONIC, &stop);

    total_time += (stop.tv_sec * 1000000 + stop.tv_nsec / 1000) -
                  (start.tv_sec * 1000000 + start.tv_nsec / 1000);
    print_verbose("Total time: %f s\n", (double)total_time / 1000000);

    close(fd);
    fclose(file);

    return EXIT_SUCCESS;
}
