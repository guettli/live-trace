# -*- coding: utf-8 -*-
# Initial Code from djangotools/utils/debug_live.py

import os, re, sys, time, datetime, thread, traceback
import argparse
import tempfile

import logging
if __name__=='__main__':
    logger=logging.getLogger(os.path.basename(sys.argv[0]))
else:
    logger=logging.getLogger(__name__)
del(logging)

u'''

live_trace.start(seconds_float) starts a monitor thread which print the stacktrace of all threads into
a logfile. You can report which lines are executed the most with this script:

app_foo_d@server:~$ live-trace -h
usage: live-trace [-h] [--most-common N] {sum-all-frames,sum-last-frame}

Read stacktrace log

positional arguments:
  {sum-all-frames,sum-last-frame}

optional arguments:
  -h, --help            show this help message and exit
  --most-common N       Display the N most common lines in the stacktraces

---------------------------------

You can start the watching thread your django middleware like this:

class FOOMiddleware:
    def __init__(self):
        u'This code gets executed once after the start of the wsgi worker process. Not for every request!'
        seconds=getattr(settings, 'live_trace_interval', None)
        if seconds:
            import live_trace
            live_trace.start(seconds)

# settings.py
live_trace_interval=0.3 # ever 0.3 second

# Inspired by http://code.google.com/p/modwsgi/wiki/DebuggingTechniques

You can get a simple report of the log file of stacktraces like below. The lines
which are not from django are marked with "<====". That's most likely your code
and this could be a bottle neck.

python ..../live_trace.py read
 1971 File: "/home/foo_bar_p/django/core/handlers/wsgi.py", line 272, in __call__
    response = self.get_response(request)
 1812 File: "/home/foo_bar_p/django/core/handlers/base.py", line 111, in get_response
    response = callback(request, *callback_args, **callback_kwargs)
 1725 File: "/home/foo_bar_p/django/db/backends/postgresql_psycopg2/base.py", line 44, in execute
    return self.cursor.execute(query, args)
 1724 File: "/home/foo_bar_p/django/db/models/sql/compiler.py", line 735, in execute_sql
    cursor.execute(sql, params)
 1007 File: "/home/foo_bar_p/django/db/models/sql/compiler.py", line 680, in results_iter
    for rows in self.execute_sql(MULTI):
  796 File: "/home/foo_bar_p/django/db/models/query.py", line 273, in iterator
    for row in compiler.results_iter():
  763 File: "/home/foo_bar_p/foo/utils/ticketutils.py", line 135, in __init__    <====
    filter=type_filter(root_node=self.root_node)
  684 File: "/home/foo_bar_p/django/db/models/query.py", line 334, in count
    return self.query.get_count(using=self.db)
  679 File: "/home/foo_bar_p/django/db/models/sql/query.py", line 367, in get_aggregation
    result = query.get_compiler(using).execute_sql(SINGLE)
  677 File: "/home/foo_bar_p/django/db/models/sql/query.py", line 401, in get_count
    number = obj.get_aggregation(using=using)[None]


'''



outfile_dir=os.path.expanduser('~/tmp/live_trace')
outfile=os.path.join(outfile_dir, '{:%Y-%m-%d-%H-%M-%S}.log')

monitor_thread=None



def analyze(args):
    from . import parser
    counter=parser.read_logs(args)
    counter.print_counts()

def test(args):
    import pytest
    errno = pytest.main(['--pyargs', 'live_trace'])
    sys.exit(errno)

def get_command_from_path(cmd):
    if os.path.exists(cmd):
        return cmd
    for path in os.environ.get('PATH', '').split(os.pathsep):
        cmd_try=os.path.join(path, cmd)
        if os.path.exists(cmd_try):
            return cmd_try
    raise ValueError('Command not found: %s' % cmd)

def pre_execfile(command_args):
    command_args=list(command_args)
    cmd=command_args[0]
    sys.argv=command_args
    cmd_from_path=get_command_from_path(cmd)
    return cmd_from_path

def run(args, on_exit_callback=None):
    cmd_from_path = pre_execfile(args.command_args)
    tracer=start(interval=args.interval, outfile_template=args.outfile)
    run_post_trace_start(args, tracer, cmd_from_path, on_exit_callback)

def run_post_trace_start(args, tracer, cmd_from_path, on_exit_callback=None):
    __name__='__main__'
    try:
        execfile(cmd_from_path)
    except SystemExit, exc:
        if not on_exit_callback:
            raise
    tracer.stop()
    on_exit_callback(args, exc.code)

def run_and_analyze(args):
    from .tracer import TracerToStream
    cmd_from_path=pre_execfile(args.command_args)

    with tempfile.TemporaryFile() as fd:
        def run_and_analyze_on_exit(args, code):
            from . import parser
            counter=parser.FrameCounter(args)
            fd.seek(0)
            counter.read_logs_of_fd(fd)
            counter.print_counts()
        tracer=TracerToStream(args.interval, fd)
        tracer.start()
        run_post_trace_start(args, tracer, cmd_from_path, run_and_analyze_on_exit)
        

def version(args):
    import pkg_resources
    print pkg_resources.get_distribution('live-trace').version

def sleep(args):
    time.sleep(args.secs_to_sleep)

def add_analyze_args(parser):
    parser.add_argument('--sum-all-frames', action='store_true')
    parser.add_argument('--most-common', '-m', metavar='N', default=30, type=int, help='Display the N most common lines in the stacktraces')
    
DEFAULT_INTERVAL=0.1
def get_argument_parser():
    parser=argparse.ArgumentParser(description=
'''Read stacktraces log which where created by live_trace. Logs are searched in %s. By default a new file is created for every day. If unsure, use sum-last-frame without other arguments to see the summary of today's output.\n\nlive_trace: A "daemon" thread monitors the process and writes out stracktraces of every N (float) seconds. This command line tool helps to see where the interpreter spent the most time.\n\nEvery stacktrace has several frames (call stack). In most cases you want to see "sum-last-frame" ("last" means "deepest" frames: that's where the interpreter was interrupted by the monitor thread). A simple regex tries to mark our code (vs python/django code) with <====.''' % (outfile_dir))

    subparsers = parser.add_subparsers(title='subcommands',
                                       description='valid subcommands')
    parser_analyze=subparsers.add_parser('analyze')
    add_analyze_args(parser_analyze)
    parser_analyze.add_argument('logfiles', help='defaults to %s' % outfile.replace('%', '%%'), default=[outfile], nargs='+')
    parser_analyze.set_defaults(func=analyze)

    parser_test=subparsers.add_parser('test')
    parser_test.set_defaults(func=test)

    parser_run=subparsers.add_parser('run')
    parser_run.set_defaults(func=run)
    parser_run.add_argument('--out-file', metavar='LOGFILE', help='defaults to %s' % outfile.replace('%', '%%'), dest='outfile', default=outfile)
    parser_run.add_argument('--interval', metavar='FLOAT_SECS', help='Dump stracktraces every FLOAT_SECS seconds.', default=DEFAULT_INTERVAL, type=float)
    parser_run.add_argument('command_args', nargs=argparse.PARSER)

    parser_run_and_analyze=subparsers.add_parser('run-and-analyze')
    parser_run_and_analyze.set_defaults(func=run_and_analyze)
    parser_run_and_analyze.add_argument('--interval', metavar='FLOAT_SECS', help='Dump stracktraces every FLOAT_SECS seconds.', default=DEFAULT_INTERVAL, type=float)
    add_analyze_args(parser_run_and_analyze)
    parser_run_and_analyze.add_argument('command_args', nargs=argparse.PARSER)

    parser_version=subparsers.add_parser('version')
    parser_version.set_defaults(func=version)

    parser_sleep=subparsers.add_parser('sleep')
    parser_sleep.set_defaults(func=sleep)
    parser_sleep.add_argument('secs_to_sleep', type=float, default=3.0)
    return parser

def main():
    parser=get_argument_parser()
    args=parser.parse_args()
    args.func(args)

def start(interval=0.1, outfile_template='-'):
    '''
    interval: Monitor interpreter every N (float) seconds.
    outfile_template: output file.
    '''
    from .tracer import TracerToLogTemplate
    tracer = TracerToLogTemplate(interval=interval, outfile_template=outfile_template)
    # tracer.thread.setDaemon(True) # http://bugs.python.org/issue1856
    # we use parent_thread.join(interval) now.
    # http://stackoverflow.com/questions/16731115/how-to-debug-a-python-seg-fault
    # http://stackoverflow.com/questions/18098475/detect-interpreter-shut-down-in-daemon-thread

    tracer.start()
    return tracer

