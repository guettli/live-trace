# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

from django.conf import settings
from live_trace import main
from live_trace.tracerusingbackgroundthread import TracerAlreadyRunning

'''
# settings.py

# add the LiveTraceMiddleware to you MIDDLEWARE_CLASSES:
MIDDLEWARE_CLASSES=[
    'live_trace.django_middleware.LiveTraceMiddleware',
    ...,
 ])

'''

DEFAULT_LIVE_TRACE_INTERVAL = 0.3


class LiveTraceMiddleware:
    def __init__(self):
        'This code gets executed once after the start of the wsgi worker process. Not for every request.'
        seconds = getattr(settings, 'LIVE_TRACE_INTERVAL', DEFAULT_LIVE_TRACE_INTERVAL)
        if not seconds:
            return
        try:
            main.start(seconds, main.outfile)
        except TracerAlreadyRunning:
            # During tests the middleware gets loaded several times.
            return
