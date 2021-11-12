
'''
    "Copyright 2020, by the California Institute of Technology. ALL RIGHTS RESERVED. 
    United States Government Sponsorship acknowledged. Any commercial use must be negotiated 
    with the Office of Technology Transfer at the California Institute of Technology.

    This software may be subject to U.S. export control laws. By accepting this software, 
    the user agrees to comply with all applicable U.S. export laws and regulations. 
    User has the responsibility to obtain export licenses, or other export authority as may be 
    required before exporting such information to foreign countries or providing access to foreign persons."



    IMAGE TRANSLATION FOR MULTIPLEXED WHOLE SLIDE IMAGES    
  
    A multiplexed image consists of multiple rounds of imaging.
    Each round has a DAPI frame along with several antigens.
    Frames in each round are assumed to be registered, but DAPI channels
    may need to be registered across rounds.

    Rounds are identified by the integer ROUND_ID in each filename, separated
    by dot '.', prior to file type and marker.  For example, the following filename
    
        UNMCPC.LIV.3rf77.1.DAPI.tif

    Round ID = 1
    Marker = DAPI
    Type = tif

    All frames are expected in TIF format (with tif extension).

    The script translates all DAPI channels across all rounds.
    The DAPI frame of a random round is fixed and all other rounds with DAPI 
    and corresponding antigens are translated with respect to this round.

    Input frames are read from 'in_folder' and output is written to 'out_folder'
    Inconsistent frame sizes are handled by padding all frames to the larges frame size.
    Multichannel RGB frames are converted to grayscale frames prior to registration.
'''

import numpy as np

from PIL import Image
Image.MAX_IMAGE_PIXELS = None

from skimage.color import rgb2gray
from skimage.util import img_as_ubyte

from skimage.registration import phase_cross_correlation

import tifffile
import glob2
import os
import sys
import psutil


def pad_frame(f, xy):
    # pad frames to the largest frame size
    if f.shape[0] < xy[0]:
        f = np.pad(f, [(0,xy[0]-f.shape[0]), (0,0)], mode='constant')
    if f.shape[1] < xy[1]:
        f = np.pad(f, [(0,0), (0,xy[1]-f.shape[1])], mode='constant')
    return f


def get_max_frame_xy(tif_files):
    mx = []
    my = []
    for f in tif_files:
        tif = tifffile.TiffFile(f)
        x, y = tif.pages[0].shape[0:2]
        print(x,y,os.path.basename(f))
        mx.append(x)
        my.append(y)
    print('\nOutput frame size:', max(mx), max(my))
    return (max(mx), max(my))


def mem_check(in_folder):
    # check available memory for two frames
    mem = psutil.virtual_memory()
    files = glob2.glob(os.path.join(in_folder, '*.tif'))
    sizes = [os.path.getsize(f) for f in files]
    msize = max(sizes)
    if msize * 2 > mem.available * 0.80:
        return False
    else:
        return True


def get_gray_frame(f, xy):
    # read tif file
    im = tifffile.imread(f)
    im = np.squeeze(im)
    # convert multi-channel images to gray
    if len(im.shape) > 2:
        im = img_as_ubyte(rgb2gray(im))
    # pad frame to max frame size
    im = pad_frame(im, xy)
    return im


def main(in_folder, out_folder):
    
    # check all frames in
    tif_files = glob2.glob(os.path.join(in_folder, '*.tif'))
    
    if not mem_check(in_folder):
        print('Not enough memory.')
        exit()

    # rounds
    rounds = list(set([os.path.basename(x).split('.')[-3] for x in tif_files]))
    max_rounds = max(rounds)
    print('\nImaging rounds:', rounds)

    # get dapi frames in each round
    dapis = [x for x in tif_files if os.path.basename(x).split('.')[-2].lower()=='dapi']
    print('\nNumber of DAPI frames:', len(dapis))
 
    if not str(len(dapis)) == max_rounds:
        print('The number of DAPI frames does not match with the number of imaging rounds.')
        exit()

    if len(dapis) < 2:
        print('At least two DAPI frames needed for registration.')
        exit()

    # antigens    
    antigens = dict()
    for r in rounds:
        a = [x for x in tif_files if os.path.basename(x).split('.')[-3]==r and not os.path.basename(x).split('.')[-2].lower()=='dapi']
        antigens[r] = a
    
    xy = get_max_frame_xy(tif_files)
    
    # write fixed round to destination
    fix_dapi = dapis.pop()
    fix_id = os.path.basename(fix_dapi).split('.')[-3]
    fix_frames = antigens[fix_id]
    for f in fix_frames:
        im = get_gray_frame(f, xy)
        tifffile.imwrite(f.replace(in_folder,out_folder), data=im)

    # read fixed dapi only once
    im_fix = get_gray_frame(fix_dapi, xy)

    # write fixed dapi frame
    tifffile.imwrite(fix_dapi.replace(in_folder, out_folder), data=im_fix)
    
    down_sample = max(im_fix.shape) // 10000 + 1    
    im_fix_small = im_fix[0::down_sample, 0::down_sample]

    print('\nFixed DAPI:', im_fix.shape, os.path.basename(fix_dapi))
    print('\nSample factor:', down_sample)

    errors = dict()
    for r in rounds:
        errors[r] = 0
    
    # loop through the rounds
    while dapis:
        mov_dapi = dapis.pop()
        mov_id = os.path.basename(mov_dapi).split('.')[-3]
        mov_frames = antigens[mov_id]
        
        # read the moving frame
        im_mov = get_gray_frame(mov_dapi, xy)
        im_mov_small = im_mov[0::down_sample, 0::down_sample]

        print('\nRegistering round:', mov_id)
        shift, error, diffphase = phase_cross_correlation(im_fix_small, im_mov_small, upsample_factor=down_sample)
        
        shift = shift * [down_sample, down_sample]

        errors[mov_id] = error
        print('error: {:.2f}'.format(error), 'phase: {:.4E}'.format(diffphase))

        im_mov_shifted = np.roll(im_mov, shift.astype(int), [0,1])
        print('Writing:', os.path.basename(mov_dapi))
        tifffile.imwrite(mov_dapi.replace(in_folder, out_folder), data=im_mov_shifted)

        # translate all non-dapi channels in this round
        for f in mov_frames:
            im = get_gray_frame(f, xy)
            im = np.roll(im, shift.astype(int), [0,1])

            print('Writing:', os.path.basename(f))
            tifffile.imwrite(f.replace(in_folder, out_folder), data=im)

    # print errors
    print('\nDisplacements:')
    for k, v in {k: v for k, v in sorted(errors.items(), key=lambda item: item[1], reverse=True)}.items():
        print('Round', k, 'displacement: {:.2f}'.format(v))

    

if __name__ == '__main__':

    log_file = os.path.join(sys.argv[2],'logfile.log')
    print('\nProcess started. Output is directed to ', log_file)
    
    sys.stdout = open(log_file, 'a')

    print('\nInput directory:', sys.argv[1])
    print('Output directory:', sys.argv[2])

    main(sys.argv[1], sys.argv[2])




 