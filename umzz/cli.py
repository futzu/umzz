import os
from pathlib import Path
import sys
from m3ufu import M3uFu
from .argue import argue
from .umzz import UMZZ
from .version import version


def cli():
    """
    cli provides one function call
    for running shari with command line args
    Two lines of code gives you a full umzz command line tool.

     from umzz import cli
     cli()

    """
    args = argue()
    if args.version:
        print(f"umzz {version}")
        sys.exit()

    print(args)
    Path(args.sidecar_file).touch()
    fu = M3uFu()
    fu.m3u8 = args.input
    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)
    try:
        fu.decode()
        um = UMZZ(fu.segments, args.output_dir, args.sidecar_file)
        um.go()
    finally:
        return


if __name__ == "__main__":
    cli()
