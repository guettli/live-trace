from django.conf import settings

DEFAULT_LIVE_TRACE_INTERVAL=0.3

class LiveTraceMiddleware:
    def __init__(self):
        u'This code gets executed once after the start of the wsgi worker process. Not for every request!'
        seconds=getattr(settings, 'LIVE_TRACE_INTERVAL', DEFAULT_LIVE_TRACE_INTERVAL)
        if not seconds:
            return
        import live_trace
        live_trace.start(seconds, live_trace.outfile)
