# Ultra Mega zoom zoom

### Live Adaptive Bitrate HLS SCTE35 Cue Injection 

##### Give me a minute, it's almost ready.



 * umzz
     * Handles __live streams in realtime__.
     * supports __mpegts__ segments that use __h264, h265, and mpeg2__ video codecs.
     * __Does not encode__. Use any encoder you like and pass umzz the master.m3u8.
     * __Adds the SCTE-35 Cues__ to each variant, and __adjusts segments__ to start on iframes.
     * Keeps variants in sync so __adaptive bitrate HLS works properly__.
     * Outputs a __new master.m3u8__, new __variant m3u8s__, and __variant segments with SCTE-35__.


#### How does umzz work?

```js
a@debian:~/$ umzz -h
usage: umzz [-h] [-i INPUT] [-o OUTPUT_DIR] [-s SIDECAR_FILE] [-t TIME]
                [-T HLS_TAG] [-w WINDOW_SIZE] [-d] [-l] [-r] [-S] [-v] [-p]
```

####  `[ -i INPUT ]`

<details> <summary> umzz takes a master.m3u8 as input from any of these sources. </summary>

 * Sources
    * file
    * Stdin
    * HTTP(s)
    * UDP Unicast
    * Multicast
* Supported Video 
    * Containers:
        * MPEGTS
    * Codecs:
        * h264
        * h265
        * mpeg2
    * HLS:
        * Audio and Video in the same segment. 
    
</details>  

#### `[ -o OUTPUT_DIR ]`

* Base directory for new HLS. default is the current directory. 

#### `[ -s SIDECAR_FILE ]`

<details> <summary>SCTE-35 cues are loaded from a Sidecar file.</summary>

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

#### `[-t TIME]`
* new target segment duration. Default is 2 seconds.


