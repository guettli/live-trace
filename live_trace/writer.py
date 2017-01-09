# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import datetime
import os
import sys


class BaseWriter(object):
    def write_traceback(self, lines_as_string):
        fd_out = self.open_outfile()
        fd_out.write(lines_as_string)
        self.close_outfile(fd_out)

    def open_outfile(self, now=None):
        raise NotImplementedError()

    def close_outfile(self, fd):
        raise NotImplementedError()


class WriterToStream(BaseWriter):
    def __init__(self, stream):
        self.stream = stream

    def open_outfile(self):
        return self.stream

    def close_outfile(self, fd):
        pass


class WriterToLogTemplate(BaseWriter):
    '''
    For long running processes: Log to file with current datetime template.
    '''

    def __init__(self, outfile_template):
        '''
        Example: outfile_template: '{:%Y/%m/%d}/foo.log'
        '''
        self.outfile_template = outfile_template

    def get_outfile(self, now=None):
        if now is None:
            now = datetime.datetime.now()
        return self.outfile_template.format(now)

    def open_outfile(self, now=None):
        if self.outfile_template == '-':
            return sys.stdout
        outfile = self.get_outfile(now)
        outfile_base = os.path.dirname(outfile)
        if not os.path.exists(outfile_base):
            os.makedirs(outfile_base)
        return open(outfile, 'at')

    def close_outfile(self, fd):
        if self.outfile_template == '-':
            return
        fd.close()
