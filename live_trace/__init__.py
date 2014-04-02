# -*- coding: utf-8 -*-
# Initial Code from djangotools/utils/debug_live.py

import os, re, sys, time, datetime, thread, threading, atexit, traceback
import argparse

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

class TracerAlreadyRunning(Exception):
    pass


outfile_dir=os.path.expanduser('~/tmp/live_trace')
outfile=os.path.join(outfile_dir, '{:%Y-%m-%d-%H-%M-%S}.log')

monitor_thread=None

is_running=threading.Semaphore()

class Tracer(object):
    stop_after_next_sleep=False
    interval=None

    def __init__(self, interval=1.0, outfile_template=None):
        if not is_running.acquire(blocking=False):
            raise TracerAlreadyRunning()
        self.interval=interval
        self.outfile_template=outfile_template
        self.thread=threading.Thread(target=self.monitor)
        self.parent_thread=threading.current_thread()
        self.pid=os.getpid()
        atexit.register(self.stop)

    def get_outfile(self, now=None):
        if now is None:
            now=datetime.datetime.now()
        return self.outfile_template.format(now)
    
    def open_outfile(self, now=None):
        if self.outfile_template=='-':
            return sys.stdout
        outfile=self.get_outfile(now)
        outfile_base=os.path.dirname(outfile)
        if not os.path.exists(outfile_base):
            os.makedirs(outfile_base)
        return open(outfile, 'at')

    def close_outfile(self, fd):
        if self.outfile_template=='-':
            return
        fd.close()

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_after_next_sleep=True
        if self.thread.is_alive():
            self.thread.join()
        is_running.release()

    def monitor(self):
        while not self.stop_after_next_sleep:
            self.parent_thread.join(self.interval)
            if not self.parent_thread.is_alive():
                break
            self.log_stacktraces()

    def log_stacktraces(self):
        code=[]
        now=datetime.datetime.now()
        for thread_id, stack in sys._current_frames().items():
            if thread_id==self.thread.ident:
                continue # Don't print this monitor thread
            code.append("\n\n#START date: %s\n# ProcessId: %s\n# ThreadID: %s" % (now, self.pid, thread_id))
            for filename, lineno, name, line in traceback.extract_stack(stack):
                code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
                if line:
                    code.append("  %s" % (line.strip()))
            code.append('#END')
        if not code:
            return
        fd_out=self.open_outfile()
        fd_out.write('\n'.join(code))
        self.close_outfile(fd_out)

def analyze(args):
    from . import parser
    parser.read_logs(args)

def test(args):
    import pytest
    errno = pytest.main(['--pyargs', 'live_trace'])
    sys.exit(errno)

def run(args):
    command_args=list(args.command_args)
    cmd=command_args.pop(0)
    if os.path.exists(cmd):
        found=cmd
    else:
        found=None
        for path in os.environ.get('PATH', '').split(os.pathsep):
            cmd_try=os.path.join(path, cmd)
            if os.path.exists(cmd_try):
                found=cmd_try
                break
        if not found:
            raise ValueError('Command not found: %s' % cmd)
    start(outfile_template=args.outfile)
    sys.argv=args.command_args
    __name__='__main__'
    execfile(found)

def version(args):
    import pkg_resources
    print pkg_resources.get_distribution('live-trace').version

def sleep(args):
    time.sleep(args.secs_to_sleep)

def get_argument_parser():
    parser=argparse.ArgumentParser(description=
'''Read stacktraces log which where created by live_trace. Logs are searched in %s. By default a new file is created for every day. If unsure, use sum-last-frame without other arguments to see the summary of today's output.\n\nlive_trace: A "daemon" thread monitors the process and writes out stracktraces of every N (float) seconds. This command line tool helps to see where the interpreter spent the most time.\n\nEvery stacktrace has several frames (call stack). In most cases you want to see "sum-last-frame" ("last" means "deepest" frames: that's where the interpreter was interrupted by the monitor thread). A simple regex tries to mark our code (vs python/django code) with <====.''' % (outfile_dir))

    subparsers = parser.add_subparsers(title='subcommands',
                                       description='valid subcommands')
    parser_analyze=subparsers.add_parser('analyze')
    parser_analyze.add_argument('--sum-all-frames', action='store_true')
    parser_analyze.add_argument('--most-common', '-m', metavar='N', default=30, type=int, help='Display the N most common lines in the stacktraces')
    parser_analyze.add_argument('--log-file', '-l', metavar='LOGFILE', help='defaults to %s' % outfile.replace('%', '%%'), dest='logfile', default=outfile)
    parser_analyze.set_defaults(func=analyze)

    parser_test=subparsers.add_parser('test')
    parser_test.set_defaults(func=test)

    parser_run=subparsers.add_parser('run')
    parser_run.set_defaults(func=run)
    parser_run.add_argument('--out-file',  metavar='LOGFILE', help='defaults to %s' % outfile.replace('%', '%%'), dest='outfile', default=outfile)
    parser_run.add_argument('command_args', nargs='*')

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
    tracer = Tracer(interval=interval, outfile_template=outfile_template)
    # tracer.thread.setDaemon(True) # http://bugs.python.org/issue1856
    # we use parent_thread.join(interval) now.
    # http://stackoverflow.com/questions/16731115/how-to-debug-a-python-seg-fault
    # http://stackoverflow.com/questions/18098475/detect-interpreter-shut-down-in-daemon-thread

    tracer.start()
    return tracer

