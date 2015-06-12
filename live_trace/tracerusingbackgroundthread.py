import os
import atexit
import threading
from .tracer import Tracer

# http://stackoverflow.com/questions/13193278/understand-python-threading-bug
threading._DummyThread._Thread__stop = lambda x: True

import logging

logger = logging.getLogger(__name__)
del (logging)

is_running = threading.Semaphore()
is_running_tracer = []


class TracerAlreadyRunning(Exception):
    pass


class TracerUsingBackgroundThread(Tracer):
    stop_after_next_sleep = False
    interval = None

    def __init__(self, writer, interval=1.0):
        super(TracerUsingBackgroundThread, self).__init__(writer)

        if not is_running.acquire(blocking=False):
            raise TracerAlreadyRunning(is_running_tracer[0].init_stacktrace)

        is_running_tracer.append(self)
        self.interval = interval
        self.thread = threading.Thread(target=self.monitor)
        self.parent_thread = threading.current_thread()
        self.pid = os.getpid()
        atexit.register(self.stop)

    @classmethod
    def could_start(cls):
        if not is_running.acquire(blocking=False):
            return False
        is_running.release()
        return True

    @classmethod
    def global_stop(cls):
        for tracer in is_running_tracer:
            tracer.stop()

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_after_next_sleep = True
        if self.thread.is_alive():
            self.thread.join()
        try:
            is_running_tracer.pop(-1)
        except IndexError:
            return
        is_running.release()

    def monitor(self):
        while not self.stop_after_next_sleep:
            self.parent_thread.join(self.interval)
            if not self.parent_thread.is_alive():
                break
            self.log_stacktraces()
