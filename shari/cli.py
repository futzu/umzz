
import os
from m3ufu import M3uFu
from x9k3 import argue
from .shari import Shari


def cli():
    """
    cli provides one function call
    for running shari with command line args
    Two lines of code gives you a full shari command line tool.

     from shari import cli
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
    shar =Shari(fu.segments,args.output_dir,"sidecar.txt")
    shar.go()

if __name__ == '__main__':
    cli()
