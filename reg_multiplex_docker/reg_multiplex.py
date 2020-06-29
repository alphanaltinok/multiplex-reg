#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
    Image registration (translation) for multiplexed frames
    
    A multiplexed image consists of multiple rounds of imaging.
    Each round has a DAPI frame along with several non-DAPI frames.
    Frames are assumed to be registered within each round, however, rounds
    may be translated during imaging.
    
    Rounds are identified by the integer ROUND ID in the filename, separated
    by dot '.', prior to file type and marker.  E.g. in the following
    
        UNMCPC.LIV.3rf77.1.DAPI.tif
    
    Round ID = 1
    Marker = DAPI

    All frames are assumed to be in TIF format.

    This script translates all DAPI channels across all rounds.
    The DAPI frame of a random round is selected as fixed and all other 
    frames from other rounds are translated with respect to this frame.

    Input frames are read from input/ subfolder and output is written to
    output/ subfolder from where the script was run.  Some frame sizes are
    inconsistent, so all frames are 0-padded to the max size of all frames.

'''

import numpy as np

from PIL import Image
Image.MAX_IMAGE_PIXELS = None

from skimage.feature import register_translation

import tifffile
import glob2
import os
import sys
import psutil


def pad_frame(f1, mx, my):
    # pad smaller sized frames to the largest frame size
    if f1.shape[0] < mx:
        f1 = np.pad(f1, [(0,mx-f1.shape[0]), (0,0)], mode='constant')
    if f1.shape[1] < my:
        f1 = np.pad(f1, [(0,0), (0,my-f1.shape[1])], mode='constant')
    return f1


def get_max_frame_size(tif_files):
    # guard for inconsistent frame sizes: use the largest frame size for all
    maxx = 0
    maxy = 0
    minx = np.inf
    miny = np.inf
    for f in tif_files:
        tif = tifffile.TiffFile(f)
        x, y = tif.pages[0].shape[0:2]
        print(x, y, f)
        maxx = max(maxx,x)
        maxy = max(maxy,y)
        minx = min(minx,x)
        miny = min(miny,y)
    print('\n')
    print('Max xy (output frame size):',maxx,maxy)
    print('Min xy:',minx,miny)
    print('Difference xy:',maxx-minx,maxy-miny,np.round((maxx-minx)/maxx,2),np.round((maxy-miny)/maxy,2))
    return maxx, maxy        



def main(in_folder, out_folder):

    # scan all files for largest images size
    tif_files = glob2.glob(os.path.join(in_folder, '*.tif'))
    
    # check memory
    mem = psutil.virtual_memory()
    tif1 = tifffile.TiffFile(tif_files[0])
    tif2 = tifffile.TiffFile(tif_files[1])
    tsz1 = tif1.fstat.st_size
    tsz2 = tif2.fstat.st_size
    if (tsz1 + tsz2) > mem.available * 0.75:
        print('Not enough memory to read two frames.')
        exit()
    
    
    # show round and file info
    rounds = list(set([os.path.basename(x).split('.')[-3] for x in tif_files]))
    max_rounds = max(rounds)
    print('Imaging rounds:', rounds)

    dapis = [x for x in tif_files if os.path.basename(x).split('.')[-2].lower()=='dapi']
    print('Number of DAPI frames:', len(dapis))
 
    if not str(len(dapis)) == max_rounds:
        print('The number of DAPI frames does not match with the number of imaging rounds.')
    
    if len(dapis) < 2:
        print('At least two DAPI frames needed for registration.')
        exit()
    
    tifs = dict()
    for r in rounds:
        a = [x for x in tif_files if os.path.basename(x).split('.')[-3]==r and not os.path.basename(x).split('.')[-2].lower()=='dapi']
        tifs[r] = a
    
    # largest image size
    mx,my = get_max_frame_size(tif_files)
    
    # adjust all histograms of all frames might help
    
    # write fixed files
    fix_dapi = dapis.pop()
    fix_id = os.path.basename(fix_dapi).split('.')[-3]
    fix_frames = tifs[fix_id]
    
    for f in fix_frames:
        im = tifffile.imread(f)
        im = np.squeeze(im)
        im = pad_frame(im, mx, my)
        tifffile.imwrite(f.replace('input','output'),data=im)
        
    # read fixed dapi only once
    im_fix = tifffile.imread(fix_dapi)
    im_fix = np.squeeze(im_fix)
    im_fix = pad_frame(im_fix, mx, my)

    # write fixed dapi frame
    tifffile.imwrite(fix_dapi.replace('input','output'),data=im_fix)
    
    down_sample = max(im_fix.shape) // 10000 + 1    
    im_fix_small = im_fix[0::down_sample, 0::down_sample]
    
    print('Fixed DAPI frame:', im_fix.shape, fix_dapi)
    print('Down sample factor:', down_sample, '\n')

    errors = dict()
    for r in rounds:
        errors[r] = 0
    
    while dapis:
        mov_dapi = dapis.pop()
        mov_id = os.path.basename(mov_dapi).split('.')[-3]
        mov_frames = tifs[mov_id]
        
        # read the moving frame
        im_mov = tifffile.imread(mov_dapi)
        im_mov = np.squeeze(im_mov)
        im_mov = pad_frame(im_mov, mx, my)
        im_mov_small = im_mov[0::down_sample, 0::down_sample]
        
        print('Registering round:', mov_id)
        
        shift, error, diffphase = register_translation(im_fix_small, im_mov_small, upsample_factor=down_sample)
        
        shift = shift * [down_sample, down_sample]

        errors[mov_id] = error

        print('DAPI frame:', im_mov.shape, mov_dapi, 'error: {:.2f}'.format(error), 'phase: {:.4E}'.format(diffphase))

        im_mov_shifted = np.roll(im_mov, shift.astype(int), [0,1])
        print('Writing:', im_mov_shifted.shape, mov_dapi.replace('input','output'))
        tifffile.imwrite(mov_dapi.replace('input','output'), data=im_mov_shifted)

        # translate all non-dapi channels in this round
        for f in mov_frames:
            im = tifffile.imread(f)
            im = np.squeeze(im)
            im = pad_frame(im, mx, my)
            im = np.roll(im, shift.astype(int), [0,1])
            print('Writing:', im.shape, f.replace('input','output'))
            tifffile.imwrite(f.replace('input','output'), data=im)

    # print errors
    print('\nErrors:')
    for k, v in {k: v for k, v in sorted(errors.items(), key=lambda item: item[1], reverse=True)}.items():
        print('Round', k, 'error {:.2f}'.format(v))

    

if __name__ == '__main__':

    log_file = 'output/output.log'
    sys.stdout = open(log_file, 'a')

    print('\nProcess started:', sys.argv[0],'\n')

    main('input/','output/')

