# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

from django.conf import settings

DEFAULT_LIVE_TRACE_INTERVAL = 0.3


class LiveTraceMiddleware:
    def __init__(self):
        'This code gets executed once after the start of the wsgi worker process. Not for every request.'
        seconds = getattr(settings, 'LIVE_TRACE_INTERVAL', DEFAULT_LIVE_TRACE_INTERVAL)
        if not seconds:
            return
        import live_trace
        try:
            live_trace.start(seconds, live_trace.outfile)
        except live_trace.tracer.TracerAlreadyRunning:
            # During tests the middleware gets loaded several times.
            return
