import datetime
import os
import sys
import traceback
from live_trace.writer import BaseWriter


class Tracer(object):

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
            for filename, lineno, name, line in traceback.extract_stack(stack):
                code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
                if line:
                    code.append("  %s" % (line.strip()))
            code.append('#END')
        if not code:
            return
        self.writer.write_traceback('\n'.join(code))

    def get_current_frames(self):
        return sys._current_frames().items()
