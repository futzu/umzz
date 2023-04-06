import os
from m3ufu import M3uFu
from .argue import argue
from .umzz import UMZZ


def cli():
    """
    cli provides one function call
    for running umzz with command line args
    Two lines of code gives you a full umzz command line tool.

     from umzz import cli
     cli()

    """
    args = argue()
    print(args)
    fu = M3uFu()
    fu.m3u8 = args.input
    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)
    try:
        fu.decode()
        [print(segment) for segment in fu.segments]
        um =UMZZ(fu.segments,args.output_dir,"sidecar.txt")
        um.go()
    finally:
        return

if __name__ == '__main__':
    cli()
