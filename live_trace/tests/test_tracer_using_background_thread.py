# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import datetime
import logging
import os
import tempfile
import time
import unittest

from live_trace.writer import WriterToLogTemplate

logger = logging.getLogger(__name__)
del (logging)

from live_trace.tracerusingbackgroundthread import TracerUsingBackgroundThread, TracerAlreadyRunning
from live_trace import main


class Test(unittest.TestCase):
    interval = 0.01

    def tearDown(self):
        self.assertTrue(TracerUsingBackgroundThread.could_start())  # please stop tracer in tests.

    def test_get_outfile(self):
        tracer = TracerUsingBackgroundThread(WriterToLogTemplate(outfile_template='abc'), self.interval)
        self.assertEqual('abc', tracer.writer.get_outfile())
        now = datetime.datetime(2014, 3, 26, 12, 14)
        tracer.writer.outfile_template = '{:%Y/%m/%d}/foo.log'
        self.assertEqual('2014/03/26/foo.log', tracer.writer.get_outfile(now=now))

        out_dir = tempfile.mktemp(prefix='live_trace_get_outfile')
        tracer.writer.outfile_template = os.path.join(out_dir, '{:%Y/%m/%d}/foo.log')
        tracer.writer.open_outfile(now=now)
        self.assertTrue(os.path.exists(os.path.join(out_dir, '2014/03/26')))
        tracer.stop()

    def test_read_logs(self):
        outfile = tempfile.mktemp(prefix='live_trace_test_output', suffix='.log')
        logger.info('outfile: %s' % outfile)
        monitor_thread = main.start(self.interval, outfile_template=outfile)

        self.assertRaises(TracerAlreadyRunning, main.start, (self.interval,), **dict(outfile_template=outfile))

        time_to_sleep = 0.01
        for i in xrange(100):
            time.sleep(time_to_sleep)  # This line should appear in log
        monitor_thread.stop()
        content = open(outfile).read()
        self.assertTrue(content)

        parser = main.ArgumentParser()
        args = parser.parse_args(['analyze', outfile])
        from live_trace.parser import read_logs

        counter = read_logs(args)
        found = False
        magic = 'time.sleep(time_to_sleep)  # This line should appear in log'
        for frame, count in counter.frames.items():
            if magic in frame.source_code:
                found = True
                break
        self.assertTrue(found, 'magic %r not found in %s' % (magic, outfile))
        self.assertGreater(count, 60, outfile)
        self.assertGreater(120, count, outfile)
        self.assertIn('test_tracer_using_background_thread.py', frame.filename, (frame.filename, outfile))

    def test_print_logs(self):
        parser = main.ArgumentParser()
        args = parser.parse_args(['analyze', '-'])
        from live_trace.parser import Frame, FrameCounter

        counter = FrameCounter(args)
        counter.count_stacks = 94

        counter.frames = {
            Frame(filename='File: "/usr/lib64/python2.7/threading.py", line 243, in wait',
                  source_code='  waiter.acquire()'): 1,
            Frame(
                filename='File: "/home/foog/src/live-trace/live_trace/tests/test_tracer_using_background_thread.py", line 38, in test_read_logs',
                source_code='  time.sleep(time_to_sleep) # This line should appear'): 92}

        lines = list(counter.print_counts_to_lines())
        self.assertEqual(2, len(lines))
        sleep_line = lines[0]
        self.assertIn('tests/test_tracer_using_background_thread.py', sleep_line)
        self.assertIn(counter.our_code_marker, sleep_line)

        threading_line = lines[1]
        self.assertIn('threading.py', threading_line)
        self.assertIn('waiter.acquire()', threading_line)

    def test_non_existing_logfile(self):
        parser = main.ArgumentParser()
        args = parser.parse_args(['analyze', 'file-which-does-not-exist'])
        self.assertRaises(IOError, args.func, args)

    def test_run_command(self):
        parser = main.ArgumentParser()
        args = parser.parse_args(['run', '--interval', '10', 'live-trace', 'sleep', '0.1'])

        def on_exit(args, code):
            self.assertIn(code, [0, None])

        args.func(args, on_exit_callback=on_exit)

    def test_run_and_analyze_command(self):
        parser = main.ArgumentParser()
        args = parser.parse_args(['run-and-analyze', '--interval', '0.1', 'live-trace', 'sleep', '0.1'])

        def on_exit(code):
            self.assertIn(code, [0, None])

        args.func(args)

    def test_stop_is_fast(self):
        main.start(0.01)
        start_time = time.time()
        main.stop()
        duration = time.time() - start_time
        self.assertTrue(TracerUsingBackgroundThread.could_start())
        self.assertLessEqual(duration, 0.04)
