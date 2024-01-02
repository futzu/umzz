"""
umzz.py
"""
from pathlib import Path
import os
import sys
import time
import multiprocessing as mp
from m3ufu import M3uFu
from new_reader import reader
from x9k3 import X9K3, argue

MAJOR = 0
MINOR = 0
MAINTENANCE = 25


def version():
    """
    version() returns the current version of umzz.
    """
    return f"v{MAJOR}.{MINOR}.{MAINTENANCE}"


class UMZZ:
    """
    The UMZZ class starts a X9MP process for each rendition
    and manages them.
    """

    def __init__(self, m3u8_list, args):
        self.master = None
        self.m3u8_list = m3u8_list
        self.args = args
        self.sidecar = args.sidecar_file
        self.side_files = []
        self.last_lines = []
        self.base = args.output_dir
        print("BASE", self.base)

    def add_rendition(self, m3u8, dir_name):
        """
        add_rendition starts a process for each rendition and
        creates a pipe for each rendition to receive SCTE-35.
        """
        p = mp.Process(
            target=self.mp_run,
            args=(
                m3u8,
                dir_name,
            ),
        )
        p.start()
        print("Rendition Process Started")

    #  self.renditions.append(p)

    def load_sidecar(self):
        """
        load_sidecar reads (pts, cue) pairs from
        the sidecar file and loads them into X9K3.sidecar
        if live, blank out the sidecar file after cues are loaded.
        """
        if self.sidecar:
            with reader(self.sidecar) as sidefile:
                these_lines = sidefile.readlines()
                if these_lines == self.last_lines:
                    return
                for side_file in self.side_files:
                    with open(side_file, "wb") as side:
                        side.writelines(these_lines)

    ##    def is_running(self):
    ##        """
    ##        is_running checks to see if rendition Processes are running
    ##        """
    ##        for r in self.renditions:
    ##            if r.is_alive():
    ##                return True
    ##            self.renditions.pop(self.renditions.index(r))
    ##            print(r._name, " is down")
    ##            return False

    def go(self):
        """
        go writes the new master.m3u8.
        """
        dir_name = 0
        with open(self.base + "/master.m3u8", "w", encoding="utf-8") as master:
            master.write("#EXTM3U\n#EXT-X-VERSION:6\n\n")
            for m3u8 in self.m3u8_list:
                if "#EXT-X-STREAM-INF" in m3u8.tags:
                    master.write("\n".join(m3u8.lines[:-1]))
                    master.write("\n")
                    dn = self.base + "/" + str(dir_name)
                    if not os.path.isdir(dn):
                        os.mkdir(dn)
                    master.write(f"{dir_name}/index.m3u8\n")
                    if self.args.sidecar_file:
                        self.side_files.append(dn + "/" + self.sidecar)
                    self.add_rendition(m3u8, dn)
                    dir_name += 1
                else:  # Copy over stuff like "#EXT-X-MEDIA-TYPE"
                    if len(m3u8.lines) > 1:
                        master.write("\n".join(m3u8.lines[:-1]))
                        media_uri = m3u8.lines[-1]
                        master.write(f"{media_uri}\n")
                        master.write("\n")
                    else:
                        master.write(m3u8.lines[0])
                        master.write("\n")
        while True:
            if self.sidecar:
                self.load_sidecar()
            time.sleep(0.2)

    def mk_x9mp(self, manifest, dir_name):
        """
        mk_x9mp generates an X9MP instance and
        sets default values
        """
        x9mp = X9K3()
        x9mp.args = self.args
        x9mp.args.output_dir = dir_name
        x9mp.args.input = manifest.media
        if x9mp.args.sidecar_file:
            x9mp.args.sidecar_file = dir_name + "/" + self.sidecar
            Path(x9mp.args.sidecar_file).touch()
            # x9mp.load_sidecar()
        return x9mp

    def mp_run(self, manifest, dir_name):
        """
        mp_run is the process started for each rendition.
        """
        x9mp = self.mk_x9mp(manifest, dir_name)
        x9mp.decode()
        while self.args.replay:
            segnum = x9mp.segnum
            x9mp = self.mk_x9mp(manifest, dir_name)
            x9mp.args.continue_m3u8 = True
            x9mp.continue_m3u8()
            x9mp.segnum = segnum
            x9mp.decode()


def do(args):
    """
    do runs umzz programmatically.
    Use like this:

    from umzz import do, argue

    args =argue()

    args.input = "/home/a/slow/master.m3u8"
    args.live = True
    args.replay = True
    args.sidecar_file="sidecar.txt"
    args.output_dir = "out-stuff"

    do(args)

    set any command line options
    programmatically with args.
    Here are the defaults returned from argue() .

    input='master.m3u8',
    continue_m3u8=False,
    delete=False,
    live=False,
    no_discontinuity=False,
    output_dir='.',
    program_date_time=False,
    replay=False,
    sidecar_file=None,
    shulga=False,
    time=2,
    hls_tag='x_cue',
    window_size=5,

    """
    fu = M3uFu()
    if not args.input:
        print("input source required (Set args.input)")
        sys.exit()
    fu.m3u8 = args.input
    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)
    fu.decode()
    um = UMZZ(fu.segments, args)
    um.go()


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
        print(version())
        sys.exit()
    print(args)
    do(args)


if __name__ == "__main__":
    mp.set_start_method("spawn")
    cli()
