"""
shari.py
"""


from multiprocessing import Process,Pipe
import os
import time
from new_reader import reader
from x9mp import X9MP


MAJOR = "0"
MINOR = "0"
MAINTAINENCE = "01"


def version():
    """
    version prints x9abr's version as a string

    Odd number versions are releases.
    Even number versions are testing builds between releases.

    Used to set version in setup.py
    and as an easy way to check which
    version you have installed.

    """
    return f"{MAJOR}.{MINOR}.{MAINTAINENCE}"



class  Shari:
    def __init__(self,m3u8_list,base,sidecar):
        self.master=None
        self.m3u8_list = m3u8_list
        self.sidecar=sidecar
        self.pipes=[]
        self.variants =[]
        self.base=base

    def add_variant(self,m3u8,dir_name):
        if m3u8.tags:
            if "#EXT-X-MEDIA-TYPE" in m3u8.tags:
                if m3u8.tags["#EXT-X-MEDIA-TYPE"] in ["CLOSED-CAPTIONS","SUBTITLES"]:
                    print(f'skipping {m3u8.tags["#EXT-X-MEDIA-TYPE"]}')
                    return
        recvr,sendr= Pipe()
        self.pipes.append(sendr)
        v = Process(target=self.mp_run,args=(recvr,m3u8,dir_name,))
        v.start()
        print(v._name," is up")
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
                            pipe.send((insert_pts,cue))
                sidefile.close()
                with open(self.sidecar, "w") as scf:
                    scf.close()

    def chk_sidecar(self):
        time.sleep(1)
        self.load_sidecar()
        return True

    def is_running(self):
        self.chk_sidecar()
        for v in self.variants:
            if v.is_alive():
                return True
            print(v._name," is down")
        return False

    def go(self):
        dir_name = 0
        with open(self.base+"/master.m3u8","w") as master:
            master.write('#EXTM3U\n#EXT-X-VERSION:6\n\n')
            for m3u8 in self.m3u8_list:
          #      self.chk_sidecar()
                master.write("\n".join(m3u8._lines[:-1]))
                master.write('\n')
                dn = self.base+"/"+str(dir_name)
                if not os.path.isdir(dn):
                    os.mkdir(dn)
                master.write(f'{dir_name}/index.m3u8\n')
                self.add_variant(m3u8,dn)
                dir_name +=1
        while True:
            if not self.is_running():
                return False

    def mp_run(self,pipe,manifest,dir_name):
        x9mp = X9MP()
        x9mp.sidecar_pipe = pipe
        x9mp.args.output_dir=dir_name
        x9mp.args.live= True
        try:
            x9mp.decode_m3u8(manifest=manifest.media)
        except:
            print(manifest.media, "...........Failed")
