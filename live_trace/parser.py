# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import collections
import re

from live_trace.main import ArgumentParser

other_code = re.compile(r'/(django|python...)/')


class ParseError(Exception):
    pass


Frame = collections.namedtuple('Frame', ('filename_line_no_and_method', 'source_code'))


def read_logs(args):
    counter = FrameCounter(args)
    counter.read_logs()
    return counter


class FrameCounter(object):
    count_stacks = 0
    Frame = Frame

    def __init__(self, args):
        assert isinstance(args, ArgumentParser.Namespace), args
        self.args = args
        self.frames = dict()

    def read_logs(self):
        for logfile in self.args.logfiles:
            with open(logfile) as fd:
                self.read_logs_of_fd(fd)

    def read_logs_of_fd(self, fd):

        # The outfile can be huge, don't read the whole file into memory.
        cur_stack = []
        py_line = ''
        code_line = ''
        for line in fd:
            if line.startswith('#END'):
                self.count_stacks += 1
                if self.args.sum_all_frames:
                    frames = cur_stack
                else:
                    frames = cur_stack[-1:]
                for frame in frames:
                    self.frames[frame] = self.frames.get(frame, 0) + 1
                cur_stack = []
                continue
            if line[0] in '\n#':
                continue
            if line.startswith('File:'):
                py_line = line.rstrip()
                continue
            if line.startswith(' '):
                code_line = line.rstrip()
                if not (py_line, code_line) in cur_stack:
                    # If there is a recursion, count the line only once per stacktrace
                    cur_stack.append(self.Frame(py_line, code_line))
                continue
            raise ParseError('unparsed: %s' % line)

    def print_counts(self):
        for line in self.print_counts_to_lines():
            print(line)

    our_code_marker = '<===='

    def print_counts_to_lines(self):
        for i, (count, frame) in enumerate(
                sorted([(count, frame) for (frame, count) in self.frames.items()], reverse=True)):
            if i > self.args.most_common:
                break
            filename = frame.filename_line_no_and_method
            if not other_code.search(filename):
                filename = '%s      %s' % (filename, self.our_code_marker)
            yield '% 5d %.2f%% %s\n    %s' % (count, count * 100.0 / self.count_stacks, filename, frame.source_code)
