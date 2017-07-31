# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import argparse
import logging
import os
import sys
import tempfile
import time

from live_trace.tracerusingbackgroundthread import TracerUsingBackgroundThread, TracerAlreadyRunning

if __name__ == '__main__':
    logger = logging.getLogger(os.path.basename(sys.argv[0]))
else:
    logger = logging.getLogger(__name__)
del (logging)

outfile_dir = os.path.expanduser('~/tmp/live_trace')
outfile = os.path.join(outfile_dir, '{:%%Y-%%m-%%d-%%H-%%M-%%S}--pid%s.log' % os.getpid())

monitor_thread = None


def analyze(args):
    from . import parser
    counter = parser.read_logs(args)
    counter.print_counts()


def test(args):
    import pytest
    errno = pytest.main(['--pyargs', 'live_trace'])
    sys.exit(errno)


def get_command_from_path(cmd):
    if os.path.exists(cmd):
        return cmd
    for path in os.environ.get('PATH', '').split(os.pathsep):
        cmd_try = os.path.join(path, cmd)
        if os.path.exists(cmd_try):
            return cmd_try
    raise ValueError('Command not found: %s' % cmd)


def pre_execfile(command_args):
    command_args = list(command_args)
    cmd = command_args[0]
    sys.argv = command_args
    cmd_from_path = get_command_from_path(cmd)
    return cmd_from_path


def run(args):
    cmd_from_path = pre_execfile(args.command_args)
    tracer = start(interval=args.interval, outfile_template=args.outfile)
    live_trace_is_running__now_run_code_which_should_get_traced(args, tracer, cmd_from_path)


def live_trace_is_running__now_run_code_which_should_get_traced(args, tracer, cmd_from_path):
    execfile(cmd_from_path, {'__name__': '__main__'})
    tracer.stop()


def run_and_analyze(args):
    from .writer import WriterToStream
    cmd_from_path = pre_execfile(args.command_args)

    with tempfile.TemporaryFile() as fd:

        tracer = TracerUsingBackgroundThread(WriterToStream(fd), args.interval)
        tracer.start()
        live_trace_is_running__now_run_code_which_should_get_traced(args, tracer, cmd_from_path)
        analyze_from_fd(fd, args)

def analyze_from_fd(fd, args):
    from . import parser
    counter = parser.FrameCounter(args)
    fd.seek(0)
    counter.read_logs_of_fd(fd)
    counter.print_counts()


def version(args):
    import pkg_resources
    print(pkg_resources.get_distribution('live-trace').version)


def add_analyze_args(parser):
    parser.add_argument('--sum-all-frames', action='store_true')
    parser.add_argument('--most-common', '-m', metavar='N', default=30, type=int,
                        help='Display the N most common lines in the stacktraces')


DEFAULT_INTERVAL = 0.1


class Namespace(argparse.Namespace):
    logfiles = []
    sum_all_frames = True

class ArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        super(ArgumentParser, self).__init__(
            description='''Read stacktraces log which where created by live_trace. Logs are searched in %s. By default a new file is created for every day. If unsure, use sum-last-frame without other arguments to see the summary of today's output.\n\nlive_trace: A "daemon" thread monitors the process and writes out stracktraces of every N (float) seconds. This command line tool helps to see where the interpreter spent the most time.\n\nEvery stacktrace has several frames (call stack). In most cases you want to see "sum-last-frame" ("last" means "deepest" frames: that's where the interpreter was interrupted by the monitor thread). A simple regex tries to mark our code (vs python/django code) with <====.''' % (
                outfile_dir))

        subparsers = self.add_subparsers(title='subcommands',
                                         description='valid subcommands')

        # argparse does strange stuff
        # http://stackoverflow.com/questions/8757338/sub-classing-the-argparse-argument-parser
        subparsers._parser_class = argparse.ArgumentParser

        parser_analyze = subparsers.add_parser('analyze')
        add_analyze_args(parser_analyze)
        parser_analyze.add_argument('logfiles', help='defaults to %s' % outfile.replace('%', '%%'), default=[outfile],
                                    nargs='+')
        parser_analyze.set_defaults(func=analyze)

        parser_test = subparsers.add_parser('test')
        parser_test.set_defaults(func=test)

        parser_run = subparsers.add_parser('run')
        parser_run.set_defaults(func=run)
        parser_run.add_argument('--out-file', metavar='LOGFILE', help='defaults to %s' % outfile.replace('%', '%%'),
                                dest='outfile', default=outfile)
        parser_run.add_argument('--interval', metavar='FLOAT_SECS', help='Dump stracktraces every FLOAT_SECS seconds.',
                                default=DEFAULT_INTERVAL, type=float)
        parser_run.add_argument('command_args', nargs=argparse.PARSER)

        parser_run_and_analyze = subparsers.add_parser('run-and-analyze')
        parser_run_and_analyze.set_defaults(func=run_and_analyze)
        parser_run_and_analyze.add_argument('--interval', metavar='FLOAT_SECS',
                                            help='Dump stracktraces every FLOAT_SECS seconds.',
                                            default=DEFAULT_INTERVAL, type=float)
        add_analyze_args(parser_run_and_analyze)
        parser_run_and_analyze.add_argument('command_args', nargs=argparse.PARSER)

        parser_version = subparsers.add_parser('version')
        parser_version.set_defaults(func=version)

    def parse_args(self, args=None):
        return super(ArgumentParser, self).parse_args(args, namespace=self.Namespace())

    Namespace = Namespace


def main():
    parser = ArgumentParser()
    args = parser.parse_args()
    args.func(args)


def start_idempotent(interval=0.1, outfile_template='-'):
    try:
        start(interval, outfile_template)
    except TracerAlreadyRunning as exc:
        pass

def start(interval=0.1, outfile_template='-'):
    '''
    interval: Monitor interpreter every N (float) seconds.
    outfile_template: output file.
    '''
    from .writer import WriterToLogTemplate
    tracer = TracerUsingBackgroundThread(WriterToLogTemplate(outfile_template=outfile_template), interval=interval)
    # tracer.thread.setDaemon(True) # http://bugs.python.org/issue1856
    # we use parent_thread.join(interval) now.
    # http://stackoverflow.com/questions/16731115/how-to-debug-a-python-seg-fault
    # http://stackoverflow.com/questions/18098475/detect-interpreter-shut-down-in-daemon-thread

    tracer.start()
    return tracer


def stop():
    from .tracerusingbackgroundthread import TracerUsingBackgroundThread
    TracerUsingBackgroundThread.global_stop()
