
import os
from m3ufu import M3uFu
from x9k3 import argue
from x9abr import X9Abr


def cli():
    """
    cli provides one function call
    for running x13  with command line args
    Two lines of code gives you a full x9abr command line tool.

     from x9abr import cli
     cli()

    """
    args = argue()
    print(args)
    fu = M3uFu()
    fu.m3u8 = args.input
    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)
    fu.decode()
   # [print(segment) for segment in fu.segments]
    x9abr =X9Abr(fu.segments,args.output_dir,"sidecar.txt")
    x9abr.go()

if __name__ == '__main__':
    cli()
