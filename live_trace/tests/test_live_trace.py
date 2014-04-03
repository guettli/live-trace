import os
import time
import datetime
import tempfile
import unittest

import logging
logger=logging.getLogger(__name__)
del(logging)

import live_trace
from live_trace.tracer import Tracer, TracerAlreadyRunning

import pytest

@pytest.mark.readonlysdf
class Test(unittest.TestCase):
    interval=0.01

    def test_get_outfile(self):
        tracer=Tracer(outfile_template='abc')
        self.assertEqual('abc', tracer.get_outfile())
        now=datetime.datetime(2014, 3, 26, 12, 14)
        tracer.outfile_template='{:%Y/%m/%d}/foo.log'
        self.assertEqual('2014/03/26/foo.log', tracer.get_outfile(now=now))

        out_dir=tempfile.mktemp(prefix='live_trace_get_outfile')
        tracer.outfile_template=os.path.join(out_dir, '{:%Y/%m/%d}/foo.log')
        tracer.open_outfile(now=now)
        self.assertTrue(os.path.exists(os.path.join(out_dir, '2014/03/26')))
        tracer.stop()

    def test_read_logs(self):
        outfile=tempfile.mktemp(prefix='live_trace_test_output', suffix='.log')
        logger.info('outfile: %s' % outfile)
        monitor_thread=live_trace.start(self.interval, outfile_template=outfile)

        self.assertRaises(TracerAlreadyRunning, live_trace.start, (self.interval,), **dict(outfile_template=outfile))

        time_to_sleep=0.01
        for i in xrange(100):
            time.sleep(time_to_sleep) # This line should appear
        monitor_thread.stop()
        content=open(outfile).read()
        self.assertTrue(content)

        parser=live_trace.get_argument_parser()
        args=parser.parse_args(['analyze', outfile])
        counter=live_trace.parser.read_logs(args)
        found=False
        for frame, count in counter.frames.items():
            if 'time.sleep(time_to_sleep) # This line should appear' in frame.source_code:
                found=True
                break
        self.assertGreater(count, 60)
        self.assertGreater(120, count)
        self.assertIn('test_live_trace.py', frame.filename)

    def test_print_logs(self):
        parser=live_trace.get_argument_parser()
        args=parser.parse_args(['analyze', '-'])
        from live_trace.parser import Frame, FrameCounter
        counter=FrameCounter(args)
        counter.count_stacks=94

        counter.frames={
            Frame(filename='File: "/usr/lib64/python2.7/threading.py", line 243, in wait', 
                  source_code='  waiter.acquire()'): 1, 
            Frame(filename='File: "/home/foog/src/live-trace/live_trace/tests/test_live_trace.py", line 38, in test_read_logs', 
                  source_code='  time.sleep(time_to_sleep) # This line should appear'): 92}
        
        lines=list(counter.print_counts_to_lines())
        self.assertEqual(2, len(lines))
        sleep_line=lines[0]
        self.assertIn('tests/test_live_trace.py', sleep_line)
        self.assertIn(counter.our_code_marker, sleep_line)

        threading_line=lines[1]
        self.assertIn('threading.py', threading_line)
        self.assertIn('waiter.acquire()', threading_line)

    def test_non_existing_logfile(self):        
        parser=live_trace.get_argument_parser()
        args=parser.parse_args(['analyze', 'file-which-does-not-exist'])
        self.assertRaises(IOError, args.func, args)

    def test_run_command(self):
        parser=live_trace.get_argument_parser()
        args=parser.parse_args(['run', '--interval', '10', 'live-trace', 'sleep', '0.1'])
        def on_exit(args, code):
            self.assertIn(code, [0, None])
        args.func(args, on_exit_callback=on_exit)

    def _________test_run_and_analyze_command(self):
        parser=live_trace.get_argument_parser()
        args=parser.parse_args(['run-and-analyze', '--interval', '10', 'live-trace', 'sleep', '0.1'])
        def on_exit(code):
            self.assertIn(code, [0, None])
        args.func(args)
        
