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

    def test_output(self):
        outfile=tempfile.mktemp(prefix='live_trace_test_output', suffix='.log')
        logger.info('outfile: %s' % outfile)
        monitor_thread=live_trace.start(self.interval, outfile_template=outfile)

        self.assertRaises(live_trace.TracerAlreadyRunning, live_trace.start, (self.interval,), **dict(outfile_template=outfile))

        for i in xrange(100):
            time.sleep(.01)
        monitor_thread.stop()
        content=open(outfile).read()
        self.assertTrue(content)
