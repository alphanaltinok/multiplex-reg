#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
    Image registration by translation of two frames
    
    Both frames are resized to the larger dimensions by 0-padding
    
    Output written to the output_directory with the same filenames and types

    Usage:
        
        python /full/path/to/reg.py /full/path/to/input/root/ /full/path/to/output/root/ 
'''


# todo:
#   dockerize
#


import numpy as np

from PIL import Image
# need to increase the limit to accommodate large size images
Image.MAX_IMAGE_PIXELS = None

from skimage.feature import register_translation

import tifffile
import psutil
import glob2
import os
import sys


def pad_frame(f1, mx, my):
    # pad smaller sized frames
    if f1.shape[0] < mx:
        f1 = np.pad(f1, [(0,mx-f1.shape[0]), (0,0)], mode='constant')
    if f1.shape[1] < my:
        f1 = np.pad(f1, [(0,0), (0,my-f1.shape[1])], mode='constant')
    return f1


def get_max_frame_size(tif_files):
    # inconsistent frame sizes: use the largest frame size for all
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
    return maxx, maxy


def register_frame(im1, im2):
    
    larger_dim = max(im1.shape)
    
    down_sample = larger_dim // 10000 + 1
    
    im1d = im1[0::down_sample, 0::down_sample].copy()
    im2d = im2[0::down_sample, 0::down_sample].copy()

    print('\nDown sampling factor:', down_sample)

    shift, error, diffphase = register_translation(im1d, im2d, upsample_factor=down_sample)
    shift = shift * [down_sample,down_sample]
    
    print('Shift:',shift)
    print('Error:',error)
    print('Diffphase:',diffphase,'\n')
    
    im2 = np.roll(im2, shift.astype(int), [0,1])
    
    return im1, im2
    

def main(in_folder, out_folder):

    # we expect two tif files in the input folder
    tif_files = glob2.glob(os.path.join(in_folder, '*.tif'))
    
    if not len(tif_files) == 2:
        print('Expected two (2) TIF files in input folder.  Found:', len(tif_files))
        exit()
    
    # check image sizes against available mem
    mem = psutil.virtual_memory()
    tif1 = tifffile.TiffFile(tif_files[0])
    tif2 = tifffile.TiffFile(tif_files[1])
    tsz1 = tif1.fstat.st_size
    tsz2 = tif2.fstat.st_size
    if (tsz1 + tsz2) > mem.available * 0.75:
        print('Not enough memory to read both frames.')
        exit()
    
    # largest image size
    mx,my = get_max_frame_size(tif_files)

    im_src = tifffile.imread(tif_files[0])
    im_dst = tifffile.imread(tif_files[1])

    im_src = np.squeeze(im_src)
    im_dst = np.squeeze(im_dst)

    im_src = pad_frame(im_src, mx, my)
    im_dst = pad_frame(im_dst, mx, my)

    im1, im2 = register_frame(im_src, im_dst)
    
    print('Writing frames.')

    tifffile.imwrite(tif_files[0].replace(in_folder, out_folder), data=im1)
    tifffile.imwrite(tif_files[1].replace(in_folder, out_folder), data=im2)
    

if __name__ == '__main__':
    
    log_file = 'output/output.log'
    sys.stdout = open(log_file, 'a')

    print('\nProcess started:', sys.argv[0],'\n')

    main('input/','output/')

