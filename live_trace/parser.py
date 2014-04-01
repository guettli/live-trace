import re
import collections

other_code=re.compile(r'/(django|python...)/')

class ParseError(Exception):
    pass

Frame=collections.namedtuple('Frame', ('filename', 'source_code'))

'''

'File: "/usr/lib64/python2.7/threading.py", line 243, in wait'

'  waiter.acquire()'

'''

class FrameCounter(object):
    count_stacks=0
    def __init__(self):
        self.frames=dict()

def read_logs(args):
    # The outfile can be huge, don't read the whole file into memory.
    counter=FrameCounter()
    cur_stack=[]
    py_line=''
    code_line=''
    for line in open(args.logfile):
        if line.startswith('#END'):
            counter.count_stacks+=1
            if args.sum_all_frames:
                frames=cur_stack
            else:
                frames=cur_stack[-1:]
            for frame in frames:
                counter.frames[frame]=counter.frames.get(frame, 0)+1
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
                cur_stack.append(Frame(py_line, code_line))
            continue
        raise ParseError('unparsed: %s' % line)
    return counter

def print_counts(args, counter):
    for line in print_counts_to_lines(args, counter):
        print line

our_code_marker='<===='
def print_counts_to_lines(args, counter):
    for i, (count, frame) in enumerate(sorted([(count, frame) for (frame, count) in counter.frames.items()], reverse=True)):
        if i>args.most_common:
            break
        filename=frame.filename
        if not other_code.search(filename):
            filename='%s      %s' % (filename, our_code_marker)
        yield '% 5d %.2f%% %s\n    %s' % (count, count*100.0/counter.count_stacks, filename, frame.source_code)
