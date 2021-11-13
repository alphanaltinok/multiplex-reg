
# IMAGE TRANSLATION FOR MULTIPLEXED WHOLE SLIDE IMAGES   
  
A multiplexed image consists of multiple rounds of imaging.  Each round has a DAPI frame along with several antigen frames.  Frames in each round are assumed to be registered, but across rounds the frames may have been translated during imaging.

Rounds are identified by the integer ROUND_ID in each filename, separated by dot '.', prior to file type and marker.  For example, the following filename

```
  UNMCPC.LIV.3rf77.1.DAPI.tif
```

Round ID = 1
Marker = DAPI
Type = tif

The script **reg_multiplex_wsi.py** translates all DAPI frames across all rounds.  The DAPI frame of a random round is fixed and all other rounds with DAPI frames are translated with respect to this round.  Corresponding translation vectors are applied to the rest of the antigen frames in each round.

All frames are expected in TIF format (with tif extension).  Input frames are read from **in_folder** and output is written to **out_folder**.  Inconsistent frame sizes are handled by 0-padding all frames to the larges frame size.  Multichannel RGB frames are converted to grayscale frames prior to registration.


## Docker

To generate a docker image:

1. Mode the following files are in a folder:
```
  Dockerfile
  environment.yml
  register_multiplex_wsi.py
```

2. Build the docker image in that folder:
```
docker build --tag mul_reg_wsi .
```

3. Point to **input/** and **output/** folders and run the container:
```
docker run --rm -d -v /path/to/output:/usr/src/app/output -v /path/to/input:/usr/src/app/input --name register mul_reg_wsi
```
