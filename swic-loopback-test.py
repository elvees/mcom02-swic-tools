#!/usr/bin/env python3

# Copyright 2019 RnD Center "ELVEES", JSC

import filecmp
import math
import os
import subprocess
import unittest


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


if __name__ == '__main__':
    unittest.main(verbosity=2)
