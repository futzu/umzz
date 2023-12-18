"""
umzz.py
"""
import os
import sys
import time
from collections import deque
from multiprocessing import Process, Pipe
from operator import itemgetter
from m3ufu import M3uFu
from new_reader import reader
from x9k3 import  X9K3, argue


MAJOR = 0
MINOR = 0
MAINTENANCE = 21


def version():
    return  f'v{MAJOR}.{MINOR}.{MAINTENANCE}'

class UMZZ:
    def __init__(self, m3u8_list, args):
        self.master = None
        self.m3u8_list = m3u8_list
        self.args = args
        self.sidecar = args.sidecar_file
        self.last_lines = []
        self.pipes = []
        self.variants = []
        self.base = args.output_dir
        print("BASE", self.base)

    def add_variant(self, m3u8, dir_name):
        """
        add_variant creates a pipe for a variant to receive SCTE-35
        and starts a Process for a variant.
        """
        recvr, sendr = Pipe()
        self.pipes.append(sendr)
        v = Process(
            target=self.mp_run,
            args=(
                recvr,
                m3u8,
                dir_name,
            ),
        )
        v.start()
        print(v._name, " is up")
        self.variants.append(v)

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
                for line in these_lines:
                    line = line.decode().strip().split("#", 1)[0]
                    if "," in line:
                        insert_pts, cue = line.split(",", 1)
                        for pipe in self.pipes:
                            pipe.send((insert_pts, cue))

    def chk_sidecar(self):
        """
        chk_sidecar checks the sidecar file once a second
        for new SCTE-35 Cues.
        """
        time.sleep(0.1)
        self.load_sidecar()
        return True

    def is_running(self):
        """
        is_running checks to see if variant Processes are running
        """
        for v in self.variants:
            if v.is_alive():
                return True
            self.variants.pop(self.variants.index(v))
            print(v._name, " is down")
            time.sleep(0.1)
        return False

    def go(self):
        """
        go writes the new master.m3u8.
        """
        dir_name = 0
        with open(self.base + "/master.m3u8", "w",encoding ="utf-8") as master:
            master.write("#EXTM3U\n#EXT-X-VERSION:6\n\n")
            for m3u8 in self.m3u8_list:
                if "#EXT-X-STREAM-INF" in m3u8.tags:
                    master.write("\n".join(m3u8.lines[:-1]))
                    master.write("\n")
                    dn = self.base + "/" + str(dir_name)
                    if not os.path.isdir(dn):
                        os.mkdir(dn)
                    master.write(f"{dir_name}/index.m3u8\n")
                    self.add_variant(m3u8, dn)
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
            if self.is_running():
                self.chk_sidecar()
            else:
                return False

    def mk_x9mp(self, pipe, manifest, dir_name):
        """
        mk_x9mp generates an X9MP instance and
        sets default values
        """
        x9mp = X9MP()
        x9mp.sidecar_pipe = pipe
        x9mp.args = self.args
        x9mp.args.output_dir = dir_name
        x9mp._tsdata = manifest.media
        x9mp.args.input = manifest.media
        if self.sidecar:
            self.load_sidecar()  # don't miss any cues
            x9mp.args.sidecar_file = dir_name + "/" + self.sidecar
        return x9mp

    def mp_run(self, pipe, manifest, dir_name):
        """
        mp_run is the process started for each variant.
        """
        x9mp = self.mk_x9mp(pipe, manifest, dir_name)
        x9mp.decode()
        while self.args.replay:
            segnum = x9mp.segnum
            x9mp = self.mk_x9mp(pipe, manifest, dir_name)
            x9mp.args.continue_m3u8 = True
            x9mp.continue_m3u8()
            x9mp.segnum = segnum
            x9mp.decode()


class X9MP(X9K3):
    """
    X9MP IS X9K3 modified to use multiprocessing
    for Adaptive Bit Rate.
    """

    def __init__(self, tsdata=None, show_null=False):
        super().__init__(tsdata, show_null)
        self.sidecar_pipe = None
       # self.timer.start() # already called by super().decode()
        self.args = None

    def _load_sidecar(self):
        """
        _load_sidecar reads (pts, cue) pairs from
        the sidecar file and loads them into x13.sidecar
        if live, blank out the sidecar file after cues are loaded.
        """
        if self.sidecar_pipe:
            if self.sidecar_pipe.poll():
                insert_pts, cue = self.sidecar_pipe.recv()
                insert_pts = float(insert_pts)
                if insert_pts == 0.0 and self.args.live:
                    insert_pts = self.next_start
                if [insert_pts, cue] not in self.sidecar:
                    print("Cue from Sidecar: ", insert_pts, cue)
                    self.sidecar.append([insert_pts, cue])
                    self.sidecar = deque(sorted(self.sidecar, key=itemgetter(0)))
           # self._chk_sidecar_cues(pid)

    def apply_args(self):
        """
        _apply_args  uses command line args
        to set X9K3 instance vars, this is here
        to short out the call to apply_args when
        we call super().__init__ .
        """
        return True

    def decode(self, func=False):
        """
        decode iterates mpegts packets
        and passes them to _parse.
        This is over-ridden so we can
        call super().apply_args()
        """
        super().apply_args()
        super().decode()


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
    cli()
