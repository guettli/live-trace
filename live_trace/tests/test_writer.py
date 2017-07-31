# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import datetime
import os
import unittest

from live_trace import main
from live_trace.writer import WriterToLogTemplate


class Test(unittest.TestCase):
    def test_writer_to_log_template(self):
        writer = WriterToLogTemplate(main.outfile)
        now = datetime.datetime(2017, 07, 31, 15, 34)
        time_part, pid_part = os.path.basename(writer.get_outfile(now=now)).split('--')
        self.assertEqual('2017-07-31-15-34-00', time_part)
