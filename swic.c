/*
 * Tool to configure SpaceWire interface on ELVEES MCom-02 SoC
 *
 * Copyright 2019-2020 RnD Center "ELVEES", JSC
 *
 * SPDX-License-Identifier: GPL-2.0
 */

#include <argp.h>
#include <errno.h>
#include <error.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

#include <linux/elvees-swic.h>

const char *argp_program_version = "swic 1.0";
const char *argp_program_bug_address = "<support@elvees.com>";

static char doc[] = \
    "\nShow / configure SWIC interface\n\
    \n\tDEVICE\tSpaceWire device to be used";

static char args_doc[] = "DEVICE";

static struct argp_option options[] = {
    {"link",  'l', "COMMAND", 0,
        "'up' option allows and runs link setting\n"
        "'down' option disallows link setting and resets link\n"
        "'reset' option resets link, link FIFO buffers" },
    {"mtu",   'm', "MTU",     0, "Set Link interface mtu to MTU" },
    {"speed", 's', "SPEED",   0,
        "Set Link interface speed to SPEED\n"
        "{ 2.4 | 4.8 | 72 | 120 | 168 | 216 | 264 | 312 | 360 | 408 }" },

    { 0 }
};

struct arguments {
    char *device;
    int info;
    int link;
    int mtu;
    int tx_speed;
};

static void check_device(char *arg, struct argp_state *state)
{
    struct stat filestatus;

    if (stat(arg, &filestatus) == -1)
        argp_failure(state, 1, errno, "Failed to get device file status.");
    if (!S_ISCHR(filestatus.st_mode))
        argp_failure(state, 1, 0, "Unsupported device type.");
}

static void get_tx_speed(char *arg, struct argp_state *state)
{
    struct arguments *arguments = state->input;

    if (strcmp(arg, "2.4") == 0)
        arguments->tx_speed = TX_SPEED_2P4;
    else if (strcmp(arg, "4.8") == 0)
        arguments->tx_speed = TX_SPEED_4P8;
    else if (strcmp(arg, "72") == 0)
        arguments->tx_speed = TX_SPEED_72;
    else if (strcmp(arg, "120") == 0)
        arguments->tx_speed = TX_SPEED_120;
    else if (strcmp(arg, "168") == 0)
        arguments->tx_speed = TX_SPEED_168;
    else if (strcmp(arg, "216") == 0)
        arguments->tx_speed = TX_SPEED_216;
    else if (strcmp(arg, "264") == 0)
        arguments->tx_speed = TX_SPEED_264;
    else if (strcmp(arg, "312") == 0)
        arguments->tx_speed = TX_SPEED_312;
    else if (strcmp(arg, "360") == 0)
        arguments->tx_speed = TX_SPEED_360;
    else if (strcmp(arg, "408") == 0)
        arguments->tx_speed = TX_SPEED_408;
    else
        argp_failure(state, 1, EINVAL, "Unknown speed argument");
}

static error_t parse_option(int key, char *arg, struct argp_state *state)
{
    struct arguments *arguments = state->input;

    switch (key) {
    case 'l':
        if (strcmp(arg, "up") == 0) {
            arguments->link = 1;
        } else if (strcmp(arg, "down") == 0) {
            arguments->link = 0;
        } else if (strcmp(arg, "reset") == 0) {
            arguments->link = 2;
        } else
            argp_usage(state);
        arguments->info = 0;
        break;
    case 'm':
        arguments->mtu = atoi(arg);
        arguments->info = 0;
        break;
    case 's':
        get_tx_speed(arg, state);
        arguments->info = 0;
        break;
    case ARGP_KEY_ARG:
        if (state->arg_num == 0) {
            check_device(arg, state);
            arguments->device = arg;
        } else if (state->arg_num > 0) {
            // the user provided too many arguments
            argp_usage(state);
        }
        break;
    case ARGP_KEY_NO_ARGS:
        argp_usage(state);
        break;
    default:
        return ARGP_ERR_UNKNOWN;
    }

    return 0;
}

static struct argp argp = {options, parse_option, args_doc, doc};

int main(int argc, char* argv[])
{
    struct arguments arguments;

    /* Default values. */
    arguments.device = NULL;
    arguments.info = 1;
    arguments.link = -1;
    arguments.mtu = -1;
    arguments.tx_speed = -1;

    argp_parse(&argp, argc, argv, 0, 0, &arguments);

    int fd = open(arguments.device, O_RDWR);
    if (fd < 0)
        error(EXIT_FAILURE, errno, "Failed to open %s device", arguments.device);

    if (arguments.info) {
        enum swic_link_state link_state;
        struct elvees_swic_speed speed;
        unsigned long mtu;

        if (ioctl(fd, SWICIOC_GET_LINK_STATE, &link_state))
            error(EXIT_FAILURE, errno, "Failed to get link state");
        if (ioctl(fd, SWICIOC_GET_SPEED, &speed))
            error(EXIT_FAILURE, errno, "Failed to get link speed");
        if (ioctl(fd, SWICIOC_GET_MTU, &mtu))
            error(EXIT_FAILURE, errno, "Failed to get link mtu");

        printf("%s:\tLink state: ", arguments.device);
        switch(link_state) {
            case LINK_ERROR_RESET: printf("ErrorReset\n"); break;
            case LINK_ERROR_WAIT: printf("ErrorWait\n"); break;
            case LINK_READY: printf("Ready\n"); break;
            case LINK_STARTED: printf("Started\n"); break;
            case LINK_CONNECTING: printf("Connecting\n"); break;
            case LINK_RUN: printf("Run\n"); break;
        }
        printf("\t\t\tTX speed: %d\n", speed.tx);
        printf("\t\t\tRX speed: %d\n", speed.rx);
        printf("\t\t\tMTU: %lu\n", mtu);

        return 0;
    }

    if (arguments.mtu != -1) {
        if (ioctl(fd, SWICIOC_SET_MTU, arguments.mtu))
            error(EXIT_FAILURE, errno, "Failed to set mtu");
    }

    if (arguments.tx_speed != -1) {
        if (ioctl(fd, SWICIOC_SET_TX_SPEED, arguments.tx_speed))
            error(EXIT_FAILURE, errno, "Failed to set speed");
    }

    if (arguments.link == 0 || arguments.link == 1) {
        if (ioctl(fd, SWICIOC_SET_LINK, arguments.link))
            error(EXIT_FAILURE, errno, "Failed to link %s",
                  link ? "up" : "down");
    }
    if (arguments.link == 2) {
        if (ioctl(fd, SWICIOC_RESET, 0))
            error(EXIT_FAILURE, errno, "Failed to reset");
    }

    return 0;
}
