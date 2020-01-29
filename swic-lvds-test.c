/*
 * Tool to test SpaceWire LVDS controller on ELVEES MCom-02 SoC
 *
 * Copyright 2020 RnD Center "ELVEES", JSC
 *
 * SPDX-License-Identifier: GPL-2.0
 */

#include <argp.h>
#include <error.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/stat.h>

#include <linux/elvees-swic.h>

const char *argp_program_version = "swic-lvds-test 1.0";
const char *argp_program_bug_address = "<support@elvees.com>";

static char doc[] = \
"\nTest SWIC LVDS controller\n\
\n\tDEVICE\tSpaceWire device to be used";

static char args_doc[] = "DEVICE";

static struct argp_option options[] = {
    {"iters",  'i', "ITERS",    0, "Iterations to test on LVDS controller" },

    { 0 }
};

struct arguments {
    char *device;
    int test;
};

static void check_device(char *arg, struct argp_state *state)
{
    struct stat filestatus;

    if (stat(arg, &filestatus) == -1)
        argp_failure(state, 1, errno, "Failed to get device file status.");
    if (!S_ISCHR(filestatus.st_mode))
        argp_failure(state, 1, 0, "Unsupported device type.");
}

static error_t parse_option(int key, char *arg, struct argp_state *state)
{
    struct arguments *arguments = state->input;

    switch (key) {
    case 'i':
        arguments->test = atoi(arg);
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
    struct elvees_swic_lvds_test lvds;

    /* Default values. */
    arguments.device = NULL;
    arguments.test = -1;

    argp_parse(&argp, argc, argv, 0, 0, &arguments);

    int fd = open(arguments.device, O_RDWR);
    if (fd < 0)
        error(EXIT_FAILURE, errno, "Failed to open %s device", arguments.device);

    if (arguments.test != -1)
        lvds.iters = arguments.test;
    else
        lvds.iters = 10000;

    if (ioctl(fd, SWICIOC_LVDS_TEST, &lvds))
        error(EXIT_FAILURE, errno, "Failed to start LVDS test");
    printf("LVDS test results:\n");
    printf("\t\tLVDS test iterations: %d\n", lvds.iters);
    printf("\t\tS_LVDS: \"0\" = %d, \"1\" = %d\n",
           lvds.s_lvds_0, lvds.s_lvds_1);
    printf("\t\tD_LVDS: \"0\" = %d, \"1\" = %d\n",
           lvds.d_lvds_0, lvds.d_lvds_1);

    return 0;
}
