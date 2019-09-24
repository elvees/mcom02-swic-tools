#!/usr/bin/env python3

# Copyright 2019 RnD Center "ELVEES", JSC

import filecmp
import itertools
import math
import os
import random
import subprocess
import tempfile
import unittest


def rand_bytes(size):
    # os.urandom() depends on the entropy in the system. This could increase
    # time of generating of data up to 1 min, which is unacceptable. This
    # function always generates data in a constant time interval. See PEP524.
    return bytearray(map(random.getrandbits, itertools.repeat(8, size)))


class TestcaseSWIC(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.inputfile = '/tmp/input.bin'
        cls.filesize = int(os.environ.get('INPUT_FILE_SIZE', 1024*1024))
        with open(cls.inputfile, 'wb') as fout:
            fout.write(rand_bytes(cls.filesize))
        cls.outputfile = '/tmp/output.bin'

        cls.iters = int(os.environ.get('ITERS', 5))
        cls.timeout = int(os.environ.get('TIMEOUT', 10))
        cls.verbose = int(os.environ.get('VERBOSE', 0))

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.inputfile)
        super().tearDownClass()

    def setUp(self):
        self.run_procs([
            ['swic', '/dev/spacewire0', '-l', 'up'],
            ['swic', '/dev/spacewire1', '-l', 'up'],
            ])

    def tearDown(self):
        self.run_procs([
            ['swic', '/dev/spacewire0', '-l', 'down'],
            ['swic', '/dev/spacewire1', '-l', 'down'],
            ])

        try:
            os.remove(self.outputfile)
        except OSError:
            pass
        super().tearDown()

    def get_speed_mbps(self, speed):
        if speed == 255:
            return 2.4
        elif speed == 0:
            return 4.8

        return 48 * (speed - 1) + 72

    def run_procs(self, procs):
        stdouts = []
        process = []

        for i, proc in enumerate(procs):
            process.append(subprocess.Popen(proc,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT))

        for i, proc in enumerate(process):
            try:
                stdouts.append(proc.communicate(timeout=self.timeout)[0])
            except subprocess.TimeoutExpired:
                proc.kill()
                stdouts.append(proc.communicate()[0])

        for proc, stdout in zip(process, stdouts):
            self.assertFalse(proc.returncode,
                             'Non zero return code, stdout/stderr: {}'.format(
                                 stdout.decode('UTF-8')))

    def check(self, speed, mtu, src, dst):
        packets = math.ceil(self.filesize / mtu)

        self.run_procs([
            ['swic', src,
             '-m', str(mtu),
             '-s', str(speed),
             '-l', 'reset'],
            ['swic', dst,
             '-s', str(speed),
             '-l', 'reset'],
            ])

        self.run_procs([
            ['swic-xfer', src, 's',
             '-f', self.inputfile,
             '-v'],
            ['swic-xfer', dst, 'r',
             '-f', self.outputfile,
             '-n', str(packets),
             '-v'],
            ])

        result = filecmp.cmp(self.inputfile, self.outputfile)
        self.assertTrue(result,
                        'Input and output files mismatch, speed={}, mtu={}.'.format(speed, mtu))

    def test_sanity(self):
        speed = 408
        mtu = 16*1024

        for i in range(self.iters):
            if self.verbose:
                print('Iteration {}'.format(i+1))
            with self.subTest(i=i):
                self.check(speed, mtu, '/dev/spacewire0', '/dev/spacewire1')
                self.check(speed, mtu, '/dev/spacewire1', '/dev/spacewire0')

    def test_mtu(self):
        speed = 408
        mtu_pool = [2**x for x in range(4, 21)]

        for i in range(self.iters):
            random.shuffle(mtu_pool)
            for mtu in mtu_pool:
                if self.verbose:
                    print('Iteration {}, mtu={}'.format(i+1, mtu))
                with self.subTest(iter=i, mtu=mtu):
                    self.check(speed, mtu, '/dev/spacewire0', '/dev/spacewire1')

    def read32(self, addr):
        return int((subprocess.check_output(['devmem',
                                             hex(addr)]).strip()).decode('UTF-8'), 16)

    def wait_event(self, mask, value):
        rx_status = self.read32(0x38084004)
        while rx_status & mask != value:
            rx_status = self.read32(0x38084004)

    def test_flush_fifo(self):
        rxfifo_size = 384
        desc_size = 16 * 1024
        num_descs = 65
        rxring_size = desc_size * num_descs
        filesize = rxring_size + rxfifo_size
        mtu = filesize / 2
        speed = 408

        if self.verbose:
            print('\nFile size {} bytes, mtu {} bytes, speed {} Mbits/s'.
                  format(filesize, mtu, speed))

        input_temp = tempfile.NamedTemporaryFile()
        input_temp.write(rand_bytes(filesize))

        self.run_procs([['swic',
                         '/dev/spacewire0',
                         '-m', str(mtu),
                         '-s', str(speed)]])

        proc = subprocess.Popen(['swic-xfer',
                                 '/dev/spacewire0', 's',
                                 '-f', input_temp.name])

        if self.verbose:
            print('\nWaiting for fill RX FIFO')
        self.wait_event(0x100, 0x100)

        self.run_procs([['swic', '/dev/spacewire1', '-l', 'down']])

        proc.kill()
        proc.wait()

        self.run_procs([['swic', '/dev/spacewire0', '-l', 'up']])
        self.run_procs([['swic', '/dev/spacewire1', '-l', 'up']])

        self.check(speed, 1024, '/dev/spacewire0', '/dev/spacewire1')


if __name__ == '__main__':
    unittest.main(verbosity=2)
