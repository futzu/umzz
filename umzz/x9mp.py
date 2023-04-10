"""
x9mp.py
"""


import datetime
import io
import os
import sys
from collections import deque
from operator import itemgetter
from iframes import IFramer
from new_reader import reader
from threefive import Cue
from x9k3 import X9K3, SCTE35
from .chunky import Chunk
from .sliding import SlidingWindow
from .timer import Timer
from .version import version


class X9MP(X9K3):
    """
    X9MP IS X9K3 modified to use multiprocessing
    for Adaptive Bit Rate.
    """

    def __init__(self, tsdata=None, show_null=False):
        super().__init__(tsdata, show_null)
        self._tsdata = tsdata
        self.in_stream = tsdata
        self.active_segment = io.BytesIO()
        self.iframer = IFramer(shush=True)
        self.window = SlidingWindow(500)
        self.scte35 = SCTE35()
        self.sidecar = deque()
        self.sidecar_pipe = None
        self.timer = Timer()
        self.m3u8 = "index.m3u8"
        # self.args = argue()
        self.apply_args()
        self.started = None
        self.next_start = None
        self.segnum = 0
        self.media_seq = 0
        self.discontinuity_sequence = 0
        self.media_list = []

    def _args_output_dir(self):
        if not os.path.isdir(self.args.output_dir):
            os.mkdir(self.args.output_dir)
        # self.m3u8 = self.mk_uri(self.args.output_dir, "index.m3u8")

    def apply_args(self):
        """
        _apply_args  uses command line args
        to set X9K3MP instance vars
        """
        self._args_input()
        self._args_hls_tag()
        self._args_output_dir()
        self._args_flags()
        self._args_window_size()
        if isinstance(self._tsdata, str):
            self._tsdata = reader(self._tsdata)

    @staticmethod
    def _clean_line(line):
        if isinstance(line, bytes):
            line = line.decode(errors="ignore")
        line = line.replace("\n", "").replace("\r", "")
        return line

    def _add_cue_tag(self, chunk):
        """
        _add_cue_tag adds SCTE-35 tags,
        handles break auto returns,
        and adds discontinuity tags as needed.
        """
        if self.scte35.break_timer is not None:
            if self.scte35.break_timer >= self.scte35.break_duration:
                self.scte35.break_timer = None
                self.scte35.cue_state = "IN"
        tag = self.scte35.mk_cue_tag()
        if tag:
            print(tag)
            if self.scte35.cue_state in ["OUT", "IN"]:
                chunk.add_tag("#EXT-X-DISCONTINUITY", None)
            kay = tag
            vee = None
            if ":" in tag:
                kay, vee = tag.split(":", 1)
            chunk.add_tag(kay, vee)
            # print(kay, vee)

    def _header(self):
        """
        header generates the m3u8 header lines
        """
        m3u = "#EXTM3U"
        m3u_version = "#EXT-X-VERSION:3"
        target = f"#EXT-X-TARGETDURATION:{int(self.args.time+1)}"
        seq = f"#EXT-X-MEDIA-SEQUENCE:{self.media_seq}"
        dseq = f"#EXT-X-DISCONTINUITY-SEQUENCE:{self.discontinuity_sequence}"
        umzzv = f"#EXT-X-UMZZ-VERSION:{version}"
        bumper = ""
        return "\n".join(
            [
                m3u,
                m3u_version,
                target,
                seq,
                dseq,
                umzzv,
                bumper,
            ]
        )
    def _chk_pdt_flag(self, chunk):
        if self.args.program_date_time:
            iso8601 = f"{datetime.datetime.utcnow().isoformat()}Z"
            chunk.add_tag("#Iframe", f"{self.started}")
            chunk.add_tag("#EXT-X-PROGRAM-DATE-TIME", f"{iso8601}")

    def _chk_live(self, seg_time):
        if self.args.live:
            self.window.pop_pane()
            self.timer.throttle(seg_time * 0.95)
            self._discontinuity_seq_plus_one()

    def _mk_chunk_tags(self, chunk, seg_time):
        self._add_cue_tag(chunk)
        self._chk_pdt_flag(chunk)
        chunk.add_tag("#EXTINF", f"{seg_time:.6f},")

    def _print_segment_details(self, seg_name, seg_time):
        one = f"{seg_name}:   start: {self.started:.6f}   "
        two = f"end: {self.next_start:.6f}   duration: {seg_time:.6f}"
        print(f"{one}{two}", file=sys.stderr)

    def _write_segment(self):
        seg_file = f"seg{self.segnum}.ts"
        seg_name = self.mk_uri(self.args.output_dir, seg_file)
        seg_time = round(self.next_start - self.started, 6)
        with open(seg_name, "wb") as seg:
            seg.write(self.active_segment.getbuffer())
        chunk = Chunk(seg_name, self.segnum)
        self._mk_chunk_tags(chunk, seg_time)
        self.window.push_pane(chunk)
        self._write_m3u8()
        self._print_segment_details(seg_name, seg_time)
        self._start_next_start()
        if self.scte35.break_timer is not None:
            self.scte35.break_timer += seg_time
        self.scte35.chk_cue_state()
        self._chk_live(seg_time)

    def _write_m3u8(self):
        self.media_seq = self.window.panes[0].num
        m3u8uri = self.mk_uri(self.args.output_dir, self.m3u8)
        with open(m3u8uri, "w+") as m3u8:
            m3u8.write(self._header())
            m3u8.write(self.window.all_panes())
            self.segnum += 1
            if not self.args.live:
                m3u8.write("#EXT-X-ENDLIST")
        self.active_segment = io.BytesIO()

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

    def _chk_sidecar_cues(self, pid):
        """
        _chk_sidecar_cues checks the insert pts time
        for the next sidecar cue and inserts the cue if needed.
        """
        if self.sidecar:
            if float(self.sidecar[0][0]) <= self.pid2pts(pid):
                raw = self.sidecar.popleft()
                self.scte35.cue_time = float(raw[0])
                self.scte35.cue = Cue(raw[1])
                self.scte35.cue.decode()
                self._chk_cue_time(pid)
                self._chk_slice_point(self.pid2pts(pid))

    def _discontinuity_seq_plus_one(self):
        if self.window.panes:
            if "#EXT-X-DISCONTINUITY" in self.window.panes[0].tags:
                self.discontinuity_sequence += 1
            if "#EXT-X-DISCONTINUITY" in self.window.panes[-1].tags:
                self._reset_stream()

    def _chk_slice_point(self, now):
        """
        chk_slice_time checks for the slice point
        of a segment eoither buy self.args.time
        or by self.scte35.cue_time
        """
        if self.scte35.cue_time:
            if now >= self.scte35.cue_time:
                self.next_start = self.scte35.cue_time
                self._write_segment()
                self.scte35.cue_time = None
                self.scte35.mk_cue_state()
                return
        if now >= self.started + self.args.time:
            self._write_segment()

    def _chk_cue_time(self, pid):
        """
        _chk_cue checks for SCTE-35 cues
        and inserts a tag at the time
        the cue is received.
        """
        if self.scte35.cue:
            pts_adjust = self.scte35.cue.info_section.pts_adjustment
            if "pts_time" in self.scte35.cue.command.get():
                self.scte35.cue_time = self.scte35.cue.command.pts_time + pts_adjust
            else:
                self.scte35.cue_time = self.pid2pts(pid) + pts_adjust
            print("Cue Time", self.scte35.cue_time)

    def _parse_scte35(self, pkt, pid):
        cue = super()._parse_scte35(pkt, pid)
        if cue:
            cue.decode()
            cue.show()
            self.scte35.cue = cue
            self._chk_cue_time(pid)
        return cue

    def _parse(self, pkt):
        pid = self._parse_info(pkt)
        self._parse_pts(pkt, pid)
        now = self.pid2pts(pid)
        if not self.started:
            self._start_next_start(pts=now)
        self._load_sidecar(pid)
        self._chk_sidecar_cues(pid)
        if self._pusi_flag(pkt):
            self._chk_slice_point(now)
            if self.args.shulga:
                self._shulga_mode(pkt, now)
            else:
                i_pts = self.iframer.parse(pkt)
                if i_pts:
                    prgm = self.pid2prgm(pid)
                    self.maps.prgm_pts[prgm] = i_pts * 90000.0
                    self._chk_slice_point(i_pts)
        self.active_segment.write(pkt)

    def decode(self, func=False):
        """
        decode iterates mpegts packets
        and passes them to _parse.

        """
        self.timer.start()
        super().decode()

    def loop(self):
        """
        loop  loops a video in the hls manifest.
        sliding window and throttled to simulate live playback,
        segments are deleted when they fall out the sliding window.
        """
        if self.in_stream.endswith("m3u8"):
            self.decode_m3u8(manifest=self.in_stream)
        else:
            self.decode()
        self._reset_stream()
        with open(self.m3u8, "w+") as m3u8:
            m3u8.write("#EXT-X-DISCONTINUITY")
        self._tsdata = reader(self.in_stream)
        return True

    def run(self):
        """
        run calls replay() if replay is set
        or else it calls decode()
        """
        self.apply_args()
        if self.in_stream.endswith("m3u8"):
            self.decode_m3u8(manifest=self.in_stream)
        if self.args.replay:
            while True:
                self.loop()
        else:
            self.decode()

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
        while True:
            with reader(manifest) as manifesto:
                m3u8 = manifesto.readlines()
                for line in m3u8:
                    line = self._clean_line(line)
                    if not line:
                        break
                    if not reload:
                        return False
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
                            if media not in self.media_list:
                                self.media_list.append(media)
                                self.media_list = self.media_list[-200:]
                                self._tsdata = reader(media)
                                self.decode()
