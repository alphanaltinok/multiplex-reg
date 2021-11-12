# multiplex-reg

## reg.py

**reg.py** registers two images by translation using a docker container.  Images should be TIF files and placed in a directory called **input**.  Registered images are written with the same filenames to a folder called **output**.  A log file is generated in the **output/** folder describing error estimates.  If image sizes differ, the larger size in each direction is used to pad images with 0's.

### Generating docker image:

1. Mode the following files are in a folder:
```
  Dockerfile
  environment.yml
  reg.py
```

2. Build the docker image in that folder:
```
docker build --tag reg .
```

3. Point to **input/** and **output/** folders and run the container:
```
docker run --rm -d -v /path/to/output:/usr/src/app/output -v /path/to/input:/usr/src/app/input --name register reg
```

## reg_multiplex.py

**reg_multiplex.py** registers frames of a **muliplexed tissue image**.  A multiplexed image consists of multiple rounds of imaging.  Images are saved as TIF files.  RGB images are converted to gray images by the script; no color information is used in translation.  Each round has a DAPI frame along with several other non-DAPI frames.  Frames are assumed to be registered within each round, however, rounds may need to be translated across rounds.  **reg_multiplex.py** translates all DAPI frames against a randomly chosen anchor frame.

Rounds are identified by the integer ROUND_ID in the filename.  ROUND_ID is found prior to the filetype and marker indicator, which are separated by dot (.).  For example, the following filename

```
  UNMCPC.LIV.3rf77.1.DAPI.tif
```

Round_id = 1

Marker = DAPI

Type = tif


Other parts of the filename appearing before these three elements can carry arbitrary information.  The last three elements are expected to appear in that order.  Input frames are expected in a folder called **input/** and output is written to a folder called **output/**.  All frames are 0-padded to the largest frame size in both dimensions.

## Setting a region of interest (ROI)

**reg_multiplex.py** supports cropping an arbitrary ROI within **100px** of the frame borders across all frames and register the resulting ROIs.  A **manifest.json** file is expected in the same **input/** folder as the frames.  This file should contain the ROI boundary coordinates as follows:

```json
{"bounding_box": [{ "top": 8000, 
                    "left": 7000, 
                    "height": 100, 
                    "width": 100}]}
```

If **manifest.json** is not found or if it contains invalid data, then registration is performed on full frames.


### Generating docker image:

1. Ensure the following files are in a folder:
```
Dockerfile
unmc.yml
reg_multiplex.py
```

2. Build the docker image in that folder:
```
docker build --tag reg_mult .
```

3. Point to input/ and output/ folders to run the container:
```
docker run --rm -d -v /path/to/input:/usr/src/app/input -v /path/to/output:/usr/src/app/output --name regmulti reg_mult
```



