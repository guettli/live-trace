.. image:: https://travis-ci.org/guettli/live-trace.svg?branch=master
    :target: https://travis-ci.org/guettli/live-trace
    
    
live-trace
==========

live-trace is a Python library to log stacktraces of a running application in a
daemon thread N times per second.  The log file can be analyzed to see
where the interpreter spends most of the time.  It is called
"live-trace" since it can be used on production systems without
noticeable performance impact.

Alternatives
============

live-trace is a very simple script. I guess (never used it), this is a far better solution: https://github.com/uber/pyflame

Or this one: https://github.com/benfred/py-spy


Why?
====

If you want to see why a particular request is slow, then use a profiler, not live-trace.

Use live-trace if you want to see the bird's-eye view. If you ask yourself the question:

  What is the interpreter doing all day long?

Then use live-trace in your production environment. Let it collect a lot of snaphosts of the interpreter state.
The current implementation uses stacktraces for freezing the state of the interpreter. 
After running for some hours you can aggregate the collected stacktraces
and identify hot spots.


Usage
=====

Usage run-and-analyze::

    you@unix> live-trace run-and-analyze your-python-script.py

Usage run, analyze later::

    you@unix> live-trace run your-python-script.py

    The collected stacktraces will be written to $TMP/live_trace/YYYY-MM-DD....log

    Now you can analyze the collected stacktraces:

    you@unix> live-trace analyze tmp/live_trace/2017-01-09-11-23-40.log

Development
===========

# Installing for development
pip install -e git+https://github.com/guettli/live-trace.git#egg=live-trace

# Running tests
cd src/live-trace
python setup.py test

Django Middleware
=================

The django middleware is optional. The tool live-trace is a general python tool.
If you want to use live-trace in other web frameworks, take this as template.

You can start the watching thread your django middleware like this::

    MIDDLEWARE_CLASSES=[
        ...
        'live_trace.django_middleware.LiveTraceMiddleware',
    ]

Optional, update the `settings.py`::

    live_trace_interval=0.1 # Default is every 0.3 second. Set to None to disable live-tracing.

Example
=======

The tool does some guessing which code is from you, and which code is from Python or Django.

Since Python and Django code is already optimized, your code gets highlighted with "<====".

That's most likely your code and this could be a bottle neck::

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
