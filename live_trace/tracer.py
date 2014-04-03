import sys
import os, atexit, datetime
import threading, traceback

is_running=threading.Semaphore()
is_running_stack=[] # for debugging

class TracerAlreadyRunning(Exception):
    pass

class Tracer(object):
    stop_after_next_sleep=False
    interval=None

    def __init__(self, interval=1.0, outfile_template=None):
        if not is_running.acquire(blocking=False):
            raise TracerAlreadyRunning(is_running_stack[-1])
        # Singleton per Process
        is_running_stack.append(traceback.format_stack())
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
