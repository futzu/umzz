# Ultra Mega zoom zoom
 _I had to rename the repo. I forgot my friend's wife is named shari, and it got awkward._

### `Live HLS Adaptive Bitrate RealTime SCTE35 Cue Injection and Resegmentation`

#### How does it work?
<details> <summary> umzz takes a master.m3u8 as input from any of these sources. </summary>

     * file
     * Stdin
     * HTTP(s)
     * UDP Unicast
     * Multicast
</details>  

* umzz handles live streams in realtime.
* umzz automatically shutdown at the broadcat ending.
* umzz supports mpegts segments that use h264, h265, mpeg2 video codecs.
* umzz does not encode. Use any encoder you like and pass umzz the master.m3u8.
* umzz adds the SCTE-35 Cues to each variant, ands adjusts segments to start on iframes.
* all SCTE-35 ad breaks start and end on iframes.
* variants are kept in sync so adaptive bitrate HLS works properly.
* umnzz outputs a new master.m3u8, new variant m3u8s, and variant segments with SCTE-35.

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


