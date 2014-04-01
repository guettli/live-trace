import re
import collections

other_code=re.compile(r'/(django|python...)/')

class ParseError(Exception):
    pass

Frame=collections.namedtuple('Frame', ('filename', 'source_line'))

'''

'File: "/usr/lib64/python2.7/threading.py", line 243, in wait'

'  waiter.acquire()'

'''


def read_logs(args):
    # The outfile can be huge, don't read the whole file into memory.
    counter=dict() # We need to support Python2.6. Not available: collections.Counter()
    cur_stack=[]
    py_line=''
    code_line=''
    count_stacks=0
    for line in open(args.logfile):
        if line.startswith('#END'):
            count_stacks+=1
            if args.sum_all_frames:
                frames=cur_stack
            else:
                frames=cur_stack[-1:]
            for frame in frames:
                counter[frame]=counter.get(frame, 0)+1
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
    for i, (count, (py, code)) in enumerate(sorted([(count, frame) for (frame, count) in counter.items()], reverse=True)):
        if i>args.most_common:
            break
        if not other_code.search(py):
            py='%s      <====' % py
        print '% 5d %.2f%% %s\n    %s' % (count, count*100.0/count_stacks, py, code)
