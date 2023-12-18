# Ultra Mega zoom zoom

### Live Adaptive Bitrate HLS SCTE35 Cue Injection 
## Latest Version `v0.0.21`
* Updates for x9k3 v0.2.31
---
* umzz
     * Handles __live streams in realtime__.
     * supports __mpegts__ segments that use __h264, h265, and mpeg2__ video codecs.
     * __Does not encode__. Use any encoder you like and pass umzz the master.m3u8.
     * __Adds the SCTE-35 Cues__ to each variant, and __adjusts segments__ to start on iframes.
     * Keeps variants in sync so __adaptive bitrate HLS works properly__.
     * Outputs a __new master.m3u8__, new __variant m3u8s__, and __variant segments with SCTE-35__.




<details><summary><b>Install</b></summary>
    
```lua
    python3 -mpip install umzz
```
 * and / or 

```lua
    pypy3 -mpip install umzz
```
    
</details>    


## `Inputs`

<details> <summary> umzz takes a master.m3u8 as input,<B> More on inputs.</B> </summary>

##### Don't use a master.m3u8 over a network, 
<br>it will have problems. You're trying to download 
<br>and parse all the renditions at the same time. 
<br> Instead use ffmpeg to pull one rendition off the network
<br>and use it to  create a new local master.m3u8.
<br> This is the faster way to do it

* something like
  
```smalltalk
ffmpeg  -re -copyts    
-i https://example.com/rendition4.m3u8  \ 
-g 30 -r 30 -flags +cgop \         
-c:v libx264 -preset faster \       
-b:v:0 2500k -b:v:1 256k  \          
-filter:v:0 scale=1920:1080 -filter:v:1 scale=512:288 \
-c:a aac -b:a 64k \                          
-map 0:v -map 0:a -map 0:v -map 0:a  \ 
-f hls -var_stream_map "v:0,a:0 v:1,a:1" \
-master_pl_name master.m3u8   \
fu3/mo_%v.m3u8  
```

* While ffmpeg is working, wait a few seconds and then startup umzz.
  ```lua
  umzz -i fu3/master.m3u8 -s my_sidecar.txt -l
  ```
* and you'll be good to go.



</details>  


## `Command Line`    


<details><summary><b>cli tool</b></summary>

```smalltalk
usage: umzz [-h] [-i INPUT] [-c] [-d] [-l] [-n] [-o OUTPUT_DIR] [-p] [-r]
            [-s SIDECAR_FILE] [-S] [-t TIME] [-T HLS_TAG] [-w WINDOW_SIZE]
            [-v]

optional arguments:
  -h, --help            show this help message and exit

  -i INPUT, --input INPUT
                        Input source, like /home/a/vid.ts or
                        udp://@235.35.3.5:3535 or https://futzu.com/xaa.ts or
                        https://example.com/not_a_master.m3u8 [default: stdin]

  -c, --continue_m3u8   Resume writing index.m3u8 [default:False]

  -d, --delete          delete segments (enables --live) [default:False]

  -l, --live            Flag for a live event (enables sliding window m3u8)
                        [default:False]

  -n, --no_discontinuity
                        Flag to disable adding #EXT-X-DISCONTINUITY tags at
                        splice points [default:False]

  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        Directory for segments and index.m3u8 (created if
                        needed) [default:'.']

  -p, --program_date_time
                        Flag to add Program Date Time tags to index.m3u8 (
                        enables --live) [default:False]

  -r, --replay          Flag for replay aka looping (enables --live,--delete)
                        [default:False]

  -s SIDECAR_FILE, --sidecar_file SIDECAR_FILE
                        Sidecar file of SCTE-35 (pts,cue) pairs.[default:None]

  -S, --shulga          Flag to enable Shulga iframe detection mode
                        [default:False]

  -t TIME, --time TIME  Segment time in seconds [default:2]

  -T HLS_TAG, --hls_tag HLS_TAG
                        x_scte35, x_cue, x_daterange, or x_splicepoint
                        [default:x_cue]

  -w WINDOW_SIZE, --window_size WINDOW_SIZE
                        sliding window size (enables --live) [default:5]

  -v, --version         Show version
```


</details>


## `Writing Code`
<details> <summary>using umzz <B>programmatically</B>


</summary>



```py3
    from umzz import do, argue

    args =argue()

    args.input = "/home/a/slow/master.m3u8"
    args.live = True
    args.replay = True
    args.sidecar_file="sidecar.txt"
    args.output_dir = "out-stuff"

    do(args)
```

* set any command line options programmatically with args.
* the vars in args correspond to the long_names of the cli tool.
* the vars in args can be access via dot notation
* these are the defaults returned from argue() .

|  vars in args    |  default value |
|------------------|----------------|
| input            |sys.stdin.buffer|
| continue_m3u8    |   False        |
| delete           |   False        |
| live             |   False        |
| no_discontinuity |   False        |
| output_dir       |    '.'         |
| program_date_time|   False        |
| replay           |   False        |
| sidecar_file     |   None         |
| shulga           |   False        |
| time             |     2          |
| hls_tags         |  'x_cue'       |
| window_size      |     5          |
   


</details>

## `SCTE-35`
<details> <summary>SCTE-35 cues are load from a sidecar file. <b>More on sidecar files.<b> </summary>

Sidecar Cues will be handled the same as SCTE35 cues from a video stream.   
line format for text file  `insert_pts, cue`
       
pts is the insert time for the cue, A four second preroll is standard. 
cue can be base64,hex, int, or bytes
     
  ```smalltalk
  a@debian:~/umzz$ cat sidecar.txt
  
  38103.868589, /DAxAAAAAAAAAP/wFAUAAABdf+/+zHRtOn4Ae6DOAAAAAAAMAQpDVUVJsZ8xMjEqLYemJQ== 
  38199.918911, /DAsAAAAAAAAAP/wDwUAAABef0/+zPACTQAAAAAADAEKQ1VFSbGfMTIxIxGolm0= 

      
```
  ```smalltalk
  umzz -i  noscte35-master.m3u8  -s sidecar.txt 
  ```
#### You can do dynamic cue injection with a `Sidecar file`
   ```js
   touch sidecar.txt
   
   umzz -i master.m3u8 -s sidecar.txt 
   
   # Open another terminal and printf cues into sidecar.txt
   
   printf '38103.868589, /DAxAAAAAAAAAP/wFAUAAABdf+/+zHRtOn4Ae6DOAAAAAAAMAQpDVUVJsZ8xMjEqLYemJQ==\n' > sidecar.txt
   
   ```
#### `Sidecar files` can now accept 0 as the PTS insert time for Splice Immediate. 
 
 

#### Specify 0 as the insert time,  the cue will be insert at the start of the next segment.

 ```js
 printf '0,/DAhAAAAAAAAAP/wEAUAAAAJf78A/gASZvAACQAAAACokv3z\n' > sidecar.txt

 ```
 
 ####  A CUE-OUT can be terminated early using a `sidecar file`.
> While umzz is running, in the middle of a CUE-OUT send a splice insert
 > with the out_of_network_indicator flag not set 
 > and the splice immediate flag set.

 ```js
 printf '0,/DAcAAAAAAAAAP/wCwUAAAABfx8AAAEAAAAA3r8DiQ==\n' > sidecar.txt
```
*  It will cause the CUE-OUT to end at the next segment start for all of the variants.
 ```js
#EXT-X-CUE-OUT 13.4
./seg5.ts:	start:112.966667	end:114.966667	duration:2.233334
#EXT-X-CUE-OUT-CONT 2.233334/13.4
./seg6.ts:	start:114.966667	end:116.966667	duration:2.1
#EXT-X-CUE-OUT-CONT 4.333334/13.4
./seg7.ts:	start:116.966667	end:118.966667	duration:2.0
#EXT-X-CUE-OUT-CONT 6.333334/13.4
./seg8.ts:	start:117.0	        end:119.0	duration:0.033333
#EXT-X-CUE-IN None
./seg9.ts:	start:119.3	        end:121.3	duration:2.3

``` 
    
</details>

    
<details><summary> Quick Example </summary>
    
 
* if you have a master.m3u8 like 

```js
a@debian:~/umzz$ cat ~/stuff/master.m3u8
#EXTM3U
#EXT-X-VERSION:6
#EXT-X-STREAM-INF:BANDWIDTH=83222,RESOLUTION=864x486,CODECS="avc1.42c01f,mp4a.40.2"
stream_0.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=83222,RESOLUTION=1280x720,CODECS="avc1.42c01f,mp4a.40.2"
stream_1.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=83222,RESOLUTION=640x360,CODECS="avc1.42c01e,mp4a.40.2"
stream_2.m3u8
```

* and you want to add a splice insert  at PTS 13140.123456, create a sidecar file and add the following line.
```js 
a@debian:~/umzz$ cat sidecar.txt
13140.123456,/DAhAAAAAAAAAP/wEAUAAAAJf78A/gASZvAACQAAAACokv3z
```
* then run this. 
```js

a@debian:~/umzz$ umzz -i ~/stuff/master.m3u8 -s sidecar.txt -o fu
```
* in the base dir fu is the new HLS with SCTE-35 
```js
a@debian:~/umzz$ ls -ald fu/* fu/*/index.m3u8
drwxr-xr-x 1 a a 1816 Apr  9 06:07 fu/0
-rw-r--r-- 1 a a 3171 Apr  9 06:07 fu/0/index.m3u8
drwxr-xr-x 1 a a 1816 Apr  9 06:07 fu/1
-rw-r--r-- 1 a a 3171 Apr  9 06:07 fu/1/index.m3u8
drwxr-xr-x 1 a a 1816 Apr  9 06:07 fu/2
-rw-r--r-- 1 a a 3171 Apr  9 06:07 fu/2/index.m3u8
-rw-r--r-- 1 a a  320 Apr  9 06:07 fu/master.m3u8
```
    
</details>    
