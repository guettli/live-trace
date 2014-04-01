import os
import time
import datetime
import tempfile
import unittest

import logging
logger=logging.getLogger(__name__)
del(logging)

import live_trace

class Test(unittest.TestCase):
    interval=0.01

    def test_get_outfile(self):
        tracer=live_trace.Tracer(outfile_template='abc')
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

        self.assertRaises(live_trace.TracerAlreadyRunning, live_trace.start, (self.interval,), **dict(outfile_template=outfile))

        time_to_sleep=0.01
        for i in xrange(100):
            time.sleep(time_to_sleep) # This line should appear
        monitor_thread.stop()
        content=open(outfile).read()
        self.assertTrue(content)

        parser=live_trace.get_argument_parser()
        args=parser.parse_args(['analyze', '--log-file', outfile])
        counter=live_trace.parser.read_logs(args)
        found=False
        for frame, count in counter.items():
            if 'time.sleep(time_to_sleep) # This line should appear' in frame.source_line:
                found=True
                break
        self.assertGreater(count, 80)
        self.assertGreater(120, count)
        self.assertIn('test_live_trace.py', frame.filename)

    def test_non_existing_logfile(self):        
        parser=live_trace.get_argument_parser()
        args=parser.parse_args(['analyze', '--log-file', 'file-which-does-not-exist'])
        self.assertRaises(IOError, args.func, args)
