import os
import tempfile
import unittest
from live_trace.main import ArgumentParser
from live_trace.parser import FrameCounter
from live_trace.tracer import Tracer

class Test(unittest.TestCase):
    def test_manual_writing(self):
        outfile = tempfile.mktemp(prefix='test_manual_writing_', suffix='.log')
        Tracer.log_stracktraces_to_file(outfile)
        args = ArgumentParser.Namespace()
        args.logfiles.append(outfile)
        frame_counter = FrameCounter(args)
        frame_counter.read_logs()
        test_manual_files=[os.path.basename(frame.filename_line_no_and_method.split(' ', 2)[1]) for frame in frame_counter.frames if 'test_manual_writing' in frame.filename_line_no_and_method]
        self.assertEqual(['test_manual_writing.py",'], test_manual_files)
        content=open(outfile).read()
        self.assertNotIn('live_trace/tracer.py', content)
