# -*- coding: utf-8 -*-
# Initial Code from djangotools/utils/debug_live.py

import os, re, sys, time, datetime, thread, threading, atexit, traceback

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


from django.conf import settings

outfile_date=datetime.date.today()
outfile_dir=os.path.expanduser('~/tmp/live_trace')

def set_outfile():
    global outfile
    outfile = os.path.join(outfile_dir, '%s.log' % outfile_date.strftime('%Y-%m-%d'))
set_outfile()

other_code=re.compile(r'/(django|python...)/')

def stacktraces(my_thread_id, pid):
    global outfile_date
    global outfile
    code=[]
    now=datetime.datetime.now()
    for thread_id, stack in sys._current_frames().items():
        if thread_id==my_thread_id:
            continue # Don't print this monitor thread
        code.append("\n\n#START date: %s\n# ProcessId: %s\n# ThreadID: %s" % (now, pid, thread_id))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
        code.append('#END')
    if not code:
        return
    if outfile=='-':
        for line in code:
            print(line)
    else:
        # TODO: this is not nice, since you can give outfile_name to start() and at 00:00 o'clock
        # the outfile suddenly changes
        if now.date()!=outfile_date: 
            outfile_date=now.date()
            outfile=os.path.join(outfile_dir, '%s.log' % outfile_date.strftime('%Y-%m-%d'))

        outfile_base=os.path.dirname(outfile)
        if not os.path.exists(outfile_base):
            os.makedirs(outfile_base)

        fd=open(outfile, 'at')
        fd.write('\n'.join(code))
        fd.close()

def monitor(interval, parent_thread):
    pid=os.getpid()
    my_thread_id=thread.get_ident() # ID of myself (monitoring thread).
    while monitor_thread:
        parent_thread.join(interval)
        if not parent_thread.is_alive():
            break
        stacktraces(my_thread_id, pid)

monitor_thread=None

def exiting():
    global monitor_thread
    monitor_thread=None

def start(interval, outfile_name=None):
    global monitor_thread, outfile
    if monitor_thread:
        return

    if outfile_name:
        outfile=outfile_name

    set_outfile()

    assert not os.path.islink(outfile), outfile # well known temporary name.... symlink attack...
    monitor_thread = threading.Thread(target=monitor, args=[interval, threading.current_thread()])

    #monitor_thread.setDaemon(True) # http://bugs.python.org/issue1856
    # we use parent_thread.join(interval) now.
    # http://stackoverflow.com/questions/16731115/how-to-debug-a-python-seg-fault
    # http://stackoverflow.com/questions/18098475/detect-interpreter-shut-down-in-daemon-thread

    atexit.register(exiting)
    monitor_thread.start()

def do_test(args):
    start(.1, outfile_name='-')
    i=0
    while i<1000:
        i=i+1
        time.sleep(.001)

def read_logs(args):
    # The outfile can be huge, don't read the whole file into memory.
    counter=dict() # We need to support Python2.6. Not available: collections.Counter()
    cur_stack=[]
    py_line=''
    code_line=''
    if args.action=='test':
        return do_test(args)
    if args.action=='sum-all-frames':
        sum_all_frames=True
    else: # sum-last-frame
        sum_all_frames=False
    print 'logfile', args.logfile
    count_stacks=0
    for line in open(args.logfile):
        if line.startswith('#END'):
            count_stacks+=1
            if sum_all_frames:
                frames=cur_stack
            else:
                frames=cur_stack[-1:]
            for frame in frames:
                counter[frame]=counter.get(frame, 0)+1
            cur_stack=[]
            continue
        if line[0] in '\n#':
            continue
        if line.startswith('File:'):
            py_line=line.rstrip()
            continue
        if line.startswith(' '):
            code_line=line.rstrip()
            if not (py_line, code_line) in cur_stack:
                # If there is a recursion, count the line only once per stacktrace
                cur_stack.append((py_line, code_line))
            continue
        print 'ERROR unparsed', line
    for i, (count, (py, code)) in enumerate(sorted([(count, frame) for (frame, count) in counter.items()], reverse=True)):
        if i>args.most_common:
            break
        if not other_code.search(py):
            py='%s      <====' % py
        print '% 5d %.2f%% %s\n    %s' % (count, count*100.0/count_stacks, py, code)

def main():
    import argparse
    parser=argparse.ArgumentParser(description=
'''Read stacktraces log which where created by live_trace. Logs are searched in %s. By default a new file is created for every day. If unsure, use sum-last-frame without other arguments to see the summary of today's output.\n\nlive_trace: A "daemon" thread monitors the process and writes out stracktraces of every N (float) seconds. This command line tool helps to see where the interpreter spent the most time.\n\nEvery stacktrace has several frames (call stack). In most cases you want to see "sum-last-frame" ("last" means "deepest" frames: that's where the interpreter was interrupted by the monitor thread). A simple regex tries to mark our code (vs python/django code) with <====.''' % (outfile_dir))
    parser.add_argument('action', choices=['sum-all-frames', 'sum-last-frame', 'test'])
    parser.add_argument('--most-common', '-m', metavar='N', default=30, type=int, help='Display the N most common lines in the stacktraces')
    parser.add_argument('--log-file', '-l', metavar='LOGFILE', help='Logfile defaults to ~/tmp/live-trace/YYYY-MM-DD.log', dest='logfile', default=outfile)
    args=parser.parse_args()
    read_logs(args)

