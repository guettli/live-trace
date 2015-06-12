import tempfile
import unittest
from live_trace.main import ArgumentParser
from live_trace.parser import FrameCounter
from live_trace.tracer import Tracer

from live_trace.writer import WriterToLogTemplate


class Test(unittest.TestCase):
    def test_manual_writing(self):
        outfile = tempfile.mktemp(prefix='test_manual_writing_', suffix='.log')
        Tracer.log_stracktraces_to_file(outfile)
        args = ArgumentParser.Namespace()
        args.logfiles.append(outfile)
        frame_counter = FrameCounter(args)
        frame_counter.read_logs()
        self.assertEqual(1, len(frame_counter.frames))
