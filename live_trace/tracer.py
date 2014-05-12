import sys
import os, atexit, datetime
import threading, traceback

# http://stackoverflow.com/questions/13193278/understand-python-threading-bug
threading._DummyThread._Thread__stop = lambda x: True

import logging
logger=logging.getLogger(__name__)
del(logging)

is_running=threading.Semaphore()
is_running_tracer=[]
class TracerAlreadyRunning(Exception):
    pass

class Tracer(object):
    stop_after_next_sleep=False
    interval=None

    def __init__(self, interval=1.0):
        if not is_running.acquire(blocking=False):
            raise TracerAlreadyRunning(is_running_tracer[0].init_stacktrace)
        # Singleton per Process
        self.init_stacktrace=''.join(traceback.format_stack())
        is_running_tracer.append(self)
        self.interval=interval
        self.thread=threading.Thread(target=self.monitor)
        self.parent_thread=threading.current_thread()
        self.pid=os.getpid()
        atexit.register(self.stop)

    @classmethod
    def could_start(self):
        if not is_running.acquire(blocking=False):
            return False
        is_running.release()
        return True

    @classmethod
    def global_stop(cls):
        for tracer in is_running_tracer:
            tracer.stop()

    def open_outfile(self, now=None):
        raise NotImplementedError()

    def close_outfile(self, fd):
        raise NotImplementedError(self.__class__)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_after_next_sleep=True
        if self.thread.is_alive():
            self.thread.join()
        try:
            is_running_tracer.pop(-1)
        except IndexError:
            logger.error('is_running_tracer empty?')
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

class TracerToStream(Tracer):
    def __init__(self, interval, stream):
        '''
        Example: outfile_template: '{:%Y/%m/%d}/foo.log'
        '''
        Tracer.__init__(self, interval)
        self.stream=stream

    def open_outfile(self):
        return self.stream

    def close_outfile(self, fd):
        pass

    
class TracerToLogTemplate(Tracer):
    '''
    For long running processes: Log to file with current datetime template.
    '''

    def __init__(self, interval, outfile_template):
        '''
        Example: outfile_template: '{:%Y/%m/%d}/foo.log'
        '''
        Tracer.__init__(self, interval)
        self.outfile_template=outfile_template

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
