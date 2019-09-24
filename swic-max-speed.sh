#!/usr/bin/env bash
# Copyright 2019 RnD Center "ELVEES", JSC

# parameters
ITERS=100
F_SIZE=1024

# hardcoded values
MTU_SIZE=16
SPEED_VALS=(2.4 4.8 72 120 168 216 264 312 360 408 456 500 552 600 648 696 744 792 840 888)
STATUS=()

print_usage () {
    echo "Usage: $0 [-i <iter_count> -s <file_size>]"
    echo "  <iter_count> - number of exchange cycles (default $ITERS)"
    echo "  <file_size> - size of file to transfer in Kbytes (default $F_SIZE)"
    echo "Example: $0 -i 100 -s 1024"
    exit 1
}

while getopts "i:s:" O; do
    case "${O}" in
        i) ITERS=${OPTARG} ;;
        s) F_SIZE=${OPTARG} ;;
        *) print_usage ;;
    esac
done

echo "Cycles: $ITERS"
echo "File size: $F_SIZE Kbytes"

MTU_BYTES=$((MTU_SIZE * 1024))
PACKETS=$((F_SIZE / MTU_SIZE))

dd if=/dev/urandom of=/tmp/send.bin bs=1K count="${F_SIZE}" status=none

for MUL in  "${SPEED_VALS[@]}"; do
    swic /dev/spacewire0 -l down
    swic /dev/spacewire1 -l down

    swic /dev/spacewire0 -m "$MTU_BYTES" -s "$MUL" -l up
    swic /dev/spacewire1 -s "$MUL" -l up

    FAIL=
    for ((I = 1; I <= ITERS; I++)); do
        rm -f /tmp/receive.bin

        SEND_MD5=$(md5sum /tmp/send.bin | awk '{print $1}')

        timeout -t 10 swic-xfer /dev/spacewire0 s -f /tmp/send.bin > /dev/null 2>&1 &
        timeout -t 10 swic-xfer /dev/spacewire1 r -f /tmp/receive.bin -n "$PACKETS" > /dev/null 2>&1

        if [[ $? -eq 143 ]]; then
            STATUS+=("hang")
            FAIL=true
            break
        fi

        if [[ -f /tmp/receive.bin ]]; then
            REC_MD5=$(md5sum /tmp/receive.bin | awk '{print $1}')
        fi

        if [[ "$SEND_MD5" != "$REC_MD5" ]]; then
            STATUS+=("fail")
            FAIL=true
            break
        fi
    done

    if [[ -z $FAIL ]]; then
        STATUS+=("pass")
    fi
done

rm -f /tmp/send.bin

IFS=,
echo "${SPEED_VALS[*]}"
echo "${STATUS[*]}"
