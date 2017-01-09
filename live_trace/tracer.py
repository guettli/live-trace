# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import datetime
import os
import sys
import traceback

from live_trace.writer import BaseWriter, WriterToLogTemplate


class Tracer(object):
    file_name_parts_to_ignore = ['/_pytest/', '/live_trace/tracer']

    def __init__(self, writer):
        assert isinstance(writer, BaseWriter), writer
        self.writer = writer
        self.init_stacktrace = ''.join(traceback.format_stack())
        self.pid = os.getpid()

    def log_stacktraces(self):
        code = []
        now = datetime.datetime.now()
        for thread_id, stack in self.get_current_frames():
            code.append("\n\n#START date: %s\n# ProcessId: %s\n# ThreadID: %s" % (now, self.pid, thread_id))
            for file_name, line_no, name, line in self.extract_stack(stack):
                code.append('File: "%s", line %d, in %s' % (file_name, line_no, name))
                if line:
                    code.append("  %s" % (line.strip()))
            code.append('#END')
        if not code:
            return
        self.writer.write_traceback('\n'.join(code))

    def extract_stack(self, stack):
        for file_name, line_no, name, line in traceback.extract_stack(stack):
            skip = False
            for file_name_part in self.file_name_parts_to_ignore:
                if file_name_part in file_name:
                    skip = True
                    break
            if skip:
                continue

            yield file_name, line_no, name, line

    def get_current_frames(self):
        return sys._current_frames().items()

    @classmethod
    def log_stracktraces_to_file(cls, outfile):
        cls(WriterToLogTemplate(outfile)).log_stacktraces()
