#!/usr/bin/env python3

# Copyright 2019 RnD Center "ELVEES", JSC

from fcntl import ioctl
import filecmp
import math
import os
import random
import struct
import subprocess
import tempfile
import unittest

_IOC_TYPEBITS = 8
_IOC_NRBITS = 8
_IOC_NRSHIFT = 0
_IOC_SIZEBITS = 14
_IOC_WRITE = 1
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS


def _IOC(dir, type, nr, size):
    return int((dir << _IOC_DIRSHIFT) | (type << _IOC_TYPESHIFT) |
               (nr << _IOC_NRSHIFT) | (size << _IOC_SIZESHIFT))


def _IOW(type, nr, size):
    return _IOC(_IOC_WRITE, type, nr, struct.calcsize(size))


SWICIOC_SET_LINK = _IOW(ord('w'), 1, 'i')  # define SWICIOC_SET_LINK _IOW('w', 1, int)


class TestcaseSWIC(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.inputfile = '/tmp/input.bin'
        cls.filesize = int(os.environ.get('INPUT_FILE_SIZE', 1024*1024))
        with open(cls.inputfile, 'wb') as fout:
            fout.write(os.urandom(cls.filesize))
        cls.outputfile = '/tmp/output.bin'

        cls.iters = int(os.environ.get('ITERS', 5))
        cls.verbose = int(os.environ.get('VERBOSE', 0))

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.inputfile)
        super().tearDownClass()

    def tearDown(self):
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

    def check(self, speed, mtu, src, dest):
        packets = math.ceil(self.filesize / mtu)

        proc1 = subprocess.Popen(['swic-xfer', self.inputfile, src,
                                  '-s', str(speed),
                                  '-m', str(mtu),
                                  '-v'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
        proc2 = subprocess.Popen(['swic-xfer', dest, self.outputfile,
                                  '-s', str(speed),
                                  '-n', str(packets),
                                  '-v'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)

        stdouts = [None, None]

        for i, proc in enumerate([proc1, proc2]):
            stdouts[i], _ = proc.communicate()

        for proc, stdout in zip((proc1, proc2), stdouts):
            self.assertFalse(proc.returncode,
                             'Non zero return code, stdout/stderr: {}'.format(
                                                           stdout.decode('UTF-8')))

        result = filecmp.cmp(self.inputfile, self.outputfile)
        self.assertTrue(result,
                        'Input and output files mismatch, speed={}, mtu={}.'.format(speed, mtu))

    def test_sanity(self):
        speed = 8
        mtu = 16*1024

        for i in range(self.iters):
            if self.verbose:
                print('Iteration {}'.format(i+1))
            with self.subTest(i=i):
                self.check(speed, mtu, '/dev/spacewire0', '/dev/spacewire1')
                self.check(speed, mtu, '/dev/spacewire1', '/dev/spacewire0')

    def test_mtu(self):
        speed = 8
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

    def setnbreak_link(self, device):
        with open(device, 'w') as handle:
            ioctl(handle, SWICIOC_SET_LINK, 1)

            # Waiting for set link
            self.wait_event(0xF0, 0xA0)

            # Waiting for fill RX FIFO
            self.wait_event(0x100, 0x100)

            ioctl(handle, SWICIOC_SET_LINK, 0)

    def test_flush_fifo(self):
        rxfifo_size = 384
        desc_size = 16 * 1024
        num_descs = 65
        rxring_size = desc_size * num_descs
        filesize = rxring_size + rxfifo_size
        mtu = filesize / 2
        speed = 8

        input_temp = tempfile.NamedTemporaryFile()
        input_temp.write(os.urandom(filesize))
        proc = subprocess.Popen(['swic-xfer', input_temp.name,
                                 '/dev/spacewire0',
                                 '-s', str(speed),
                                 '-m', str(mtu)])
        self.setnbreak_link('/dev/spacewire1')

        proc.kill()
        proc.wait()

        self.check(speed, 1024, '/dev/spacewire0', '/dev/spacewire1')


if __name__ == '__main__':
    unittest.main(verbosity=2)
