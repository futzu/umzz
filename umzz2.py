"""
umzz.py
"""


from multiprocessing import Process, Pipe
import time
import os
from pathlib import Path
import sys
from m3ufu import M3uFu
import datetime
import io
from collections import deque
from operator import itemgetter
from iframes import IFramer
from new_reader import reader
from threefive import Cue
from x9k3 import Chunk, X9K3, SCTE35, SlidingWindow,Timer,argue
#from .version import version




class UMZZ:
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
        time.sleep(1)
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
        x9mp = X9MP()
        x9mp.sidecar_pipe = pipe
        x9mp.args.output_dir = dir_name
        x9mp.args.live = True
       # try:
        x9mp.decode_m3u8(manifest=manifest.media)
        #except Exception as err:
         #   print(err)
          #  print(manifest.media, "...........Failed")



class X9MP(X9K3):
    """
    X9MP IS X9K3 modified to use multiprocessing
    for Adaptive Bit Rate.
    """

    def __init__(self, tsdata=None, show_null=False):
        super().__init__(tsdata, show_null)
        self.sidecar_pipe = None
      #  self.timer = Timer()
       # self.m3u8 = "index.m3u8"
       # self.args = argue()
        #self.apply_args()
        self.media_list = []

    @staticmethod
    def _clean_line(line):
        if isinstance(line, bytes):
            line = line.decode(errors="ignore")
        line = line.replace("\n", "").replace("\r", "")
        return line


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

##    def now(self):
##        """
##        now returns the current pts
##        for the first program available.
##        """
##        try:
##            return self.as_90k(list(self.maps.prgm_pts.items())[0][1])
##        except:
##            return None

##    def _write_segment(self):
##        print("HEY")
##        if self.segnum is None:
##            self.segnum = 0
##        seg_file = f"seg{self.segnum}.ts"
##        seg_name = self.mk_uri(self.args.output_dir, seg_file)
##        seg_time = round(self.now() - self.started, 6)
##        with open(seg_name, "wb") as seg:
##            seg.write(self.active_segment.getbuffer())
##        if seg_time <= 0:
##            return
##        chunk = Chunk(seg_file, seg_name, self.segnum)
##        if self.first_segment:
##            if self.args.replay or self.args.continue_m3u8:
##                self.add_discontinuity(chunk)
##        self._mk_chunk_tags(chunk, seg_time)
##        self.window.push_pane(chunk)
##        self._write_m3u8()
##        self._print_segment_details(seg_name, seg_time)
##        self._start_next_start()
##        if self.scte35.break_timer is not None:
##            self.scte35.break_timer += seg_time
##        self.scte35.chk_cue_state()
##        self._chk_live(seg_time)


#    def addendum(self):
#        return
##    def run(self):
##        """
##        run calls replay() if replay is set
##        or else it calls decode()
##        """
##        self.apply_args()
##        if self.in_stream.endswith("m3u8"):
##            self.decode_m3u8(manifest=self.in_stream)
##        if self.args.replay:
##            while True:
##                self.loop()
##        else:
##            self.decode()
##    def _parse_pts(self, pkt, pid):
##        """
##        parse pts and store by program key
##        in the dict Stream._pid_pts
##        """
##     #   if pid not in self.pids.pcr:
##      #      print(self.pids.pcr)
##        if not self._pusi_flag(pkt):
##            return
##        payload = self._parse_payload(pkt)
##        if len(payload) > 13:
##            if self._pts_flag(payload):
##                pts = (payload[9] & 14) << 29
##                pts |= payload[10] << 22
##                pts |= (payload[11] >> 1) << 15
##                pts |= payload[12] << 7
##                pts |= payload[13] >> 1
##                prgm = self.pid2prgm(pid)
##                self.maps.prgm_pts[prgm] = pts
##                if prgm not in self.start:
##                    self.start[prgm] = pts
##               # print('PTS', pts/90000.0)
####
##    def _parse(self, pkt):
##        """
##        _parse is run on every packet.
##        """
##        super()._parse(pkt)
##        pkt_pid = self._parse_pid(pkt[1], pkt[2])
##        now = self.pid2pts(pkt_pid)
##        self._load_sidecar(pkt_pid)
##        self._chk_sidecar_cues(pkt_pid)
##        if not self.started:
##            self._start_next_start(pts=now)
##        #    print(self.started)
##        if self._pusi_flag(pkt) and self.started:
##         #   print("PUSI")
##         #   print(pkt)
##           # print(now)
##            if self.args.shulga:
##                self._shulga_mode(pkt, now)
##            else:
##                i_pts = self.iframer.parse(pkt)
##                if i_pts:
##                    self._chk_slice_point(i_pts)
##            # Split on non-Iframes for CUE-IN or CUE-OUT
##            if self.scte35.cue_time:
##                self._chk_slice_point(now)
##   
##        self.active_segment.write(pkt)
##




    def decode_m3u8(self, manifest=None):
        """
        decode_m3u8 is called when the input file is a m3u8 playlist.
        """
      #  if not  manifest.startswith('http') or not manifest.startswith('/'): 
        based = manifest.rsplit("/", 1)
        if len(based) > 1:
            base_uri = f"{based[0]}/"
        else:
            base_uri = ""
        last_segnum = -1
        reload = 25
        self.timer.start()
        while True:
            with reader(manifest) as manifesto:
                m3u8 = manifesto.readlines()
                print(self.args)
                for line in m3u8:
                    line = self._clean_line(line)
                    if not line:
                        break
                    if self.segnum == last_segnum:
                        reload -= 1
                    else:
                        reload = 25
                    last_segnum = self.segnum
                    if not line.startswith("#"):
                        if len(line):
                            if base_uri not in line:
                                media = base_uri + line
                            else:
                                media = line
                           # print(media)
                            if media not in self.media_list:
                                self.media_list.append(media)
                              #  print(self.media_list)
                                self.media_list = self.media_list[-200:]
                                self._tsdata = reader(media)
                                for pkt in self.iter_pkts():
                                     self._parse(pkt)
                                self._tsdata.close()
                              #  print(self.now())
                               # self._reset_stream()
                               # self.decode_fu()
                               # return
            if not reload:
                return False


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
    #try:
    fu.decode()
    um = UMZZ(fu.segments, args.output_dir, args.sidecar_file)
    um.go()
   # finally:
    return


if __name__ == "__main__":
    cli()
