Python library to log stacktraces of the running application in a
daemon thread N times per second.  The log file can be analyzed to see
where the interpreter spends most of the time.  It is called
"live-trace" since it can be used on production systems without
noticeable performance impact.
