"""
umzz2.py
"""
import datetime
import io
import os
import sys
import time
from collections import deque
from multiprocessing import Process, Pipe
from operator import itemgetter
from pathlib import Path

from m3ufu import M3uFu
from iframes import IFramer
from new_reader import reader
from threefive import Cue
from x9k3 import Chunk, X9K3, SCTE35, SlidingWindow,Timer,argue
#from .version import version


class UMZZ2:
    def __init__(self, m3u8_list, base, sidecar):
        self.master = None
        self.m3u8_list = m3u8_list
        self.sidecar = sidecar
        self.pipes = []
        self.variants = []
        self.base = base
        print("BASE",base)

    def add_variant(self, m3u8, dir_name):
        """
        add_variant creates a pipe for a variant to receive SCTE-35
        and starts a Process for a variant.
        """
##        if m3u8.tags:
##            if "#EXT-X-MEDIA-TYPE" in m3u8.tags:
##                if m3u8.tags["#EXT-X-MEDIA-TYPE"] in ["CLOSED-CAPTIONS", "SUBTITLES"]:
##                    print(f'skipping {m3u8.tags["#EXT-X-MEDIA-TYPE"]}')
##                    return
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
        _load_sidecar reads (pts, cue) pairs from
        the sidecar file and loads them into X9K3.sidecar
        if live, blank out the sidecar file after cues are loaded.
        """
        if self.sidecar:
            with reader(self.sidecar) as sidefile:
                for line in sidefile:
                    line = line.decode().strip().split("#", 1)[0]
                    if len(line):
                        insert_pts, cue = line.split(",", 1)
                        for pipe in self.pipes:
                            print(insert_pts, cue)
                            pipe.send((insert_pts, cue))
                sidefile.close()
                with open(self.sidecar, "w") as scf:
                    scf.close()

    def chk_sidecar(self):
        """
        chk_sidecar checks the sidecar file once a second
        for new SCTE-35 Cues.
        """
        time.sleep(.5)
        self.load_sidecar()
        return True

    def is_running(self):
        """
        is_running checks to see if variant Processes are running
        """
        self.chk_sidecar()
        for v in self.variants:
            if v.is_alive():
                return True
            self.variants.pop(self.variants.index(v))
            print(v._name, " is down")
        return False

    def go(self):
        """
        go writes the new master.m3u8.
        """
        dir_name = 0
        with open(self.base + "/master.m3u8", "w") as master:
            master.write("#EXTM3U\n#EXT-X-VERSION:6\n\n")
            for m3u8 in self.m3u8_list:
                #   print(vars(m3u8))
                self.chk_sidecar()
                if "#EXT-X-STREAM-INF" in m3u8.tags:
                  #  for k, v in m3u8.tags.items():
                    #    print(f"{k}:{v}")
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
            if not self.is_running():
                return False

    def mp_run(self, pipe,manifest,dir_name):
        args =argue()
        x9mp = X9MP()
        x9mp.sidecar_pipe = pipe
        args.output_dir = dir_name
        args.live = True
        args.input =manifest.media
        x9mp.args = args
        x9mp.decode()
        while args.replay:
            segnum =x9mp.segnum
            x9mp = X9MP()
            x9mp.sidecar_pipe = pipe
            x9mp.args.output_dir = dir_name
            x9mp.args.live = True
            args.input =manifest.media
            x9mp.args = args
            x9mp.args.continue_m3u8=True
            x9mp.continue_m3u8()
            x9mp.segnum =segnum
            x9mp.decode()



class X9MP(X9K3):
    """
    X9MP IS X9K3 modified to use multiprocessing
    for Adaptive Bit Rate.
    """

    def __init__(self, tsdata=None, show_null=False):
        super().__init__(tsdata, show_null)
        self.sidecar_pipe = None
        self.timer.start()

    def _load_sidecar(self, pid):
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
                if insert_pts >= self.pid2pts(pid):
                    if [insert_pts, cue] not in self.sidecar:
                        self.sidecar.append([insert_pts, cue])
                        self.sidecar = deque(sorted(self.sidecar, key=itemgetter(0)))



def cli():
    """
    cli provides one function call
    for running shari with command line args
    Two lines of code gives you a full umzz command line tool.

     from umzz import cli
     cli()

    """
    args = argue()
  #  if args.version:
   #     print(f"umzz {version}")
    #    sys.exit()
    print(args)
    if not args.sidecar_file:
        args.sidecar_file='sidecar.txt'
    Path(args.sidecar_file).touch()
    fu = M3uFu()
    fu.m3u8 = args.input
    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)
    fu.decode()
    um = UMZZ2(fu.segments, args.output_dir, args.sidecar_file)
    um.go()
    return


if __name__ == "__main__":
    cli()
