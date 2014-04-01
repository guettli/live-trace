import os
import atexit

import live_trace

def start(interval, outfile_template=None):
    tracer = live_trace.Tracer(interval=interval, outfile_template=outfile_template)
    # tracer.thread.setDaemon(True) # http://bugs.python.org/issue1856
    # we use parent_thread.join(interval) now.
    # http://stackoverflow.com/questions/16731115/how-to-debug-a-python-seg-fault
    # http://stackoverflow.com/questions/18098475/detect-interpreter-shut-down-in-daemon-thread

    tracer.start()
    return tracer
