#!/usr/bin/python3
import os
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
import cv2
from skimage import measure

def thresh_mask(mask,thresh):
    #thresholds binary image in np array based on thresh
    mask[np.where(mask<thresh)] = 0
    mask[np.where(mask>=thresh)] = 1
    return mask

def get_largest_connected_comp(mask):
    #accepts binary image and returns image with largest connected component
    mask = mask.astype('uint8')
    nb_components, output, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=4)
    sizes = stats[:, -1]

    max_label = 1
    max_size = sizes[1]
    for i in range(2, nb_components):
        if sizes[i] > max_size:
            max_label = i
            max_size = sizes[i]

    mask_lcc = np.zeros(output.shape)
    mask_lcc[output == max_label] = 1
    return mask_lcc

def pad_image(image, cx, cy, desired_size):
  """ Crop a 2D image using a bounding box centred at (cx, cy) with specified size """
  X,Y = image.shape[0:2] 
  r_x,r_y = int(desired_size[0] / 2),int(desired_size[1] / 2)
  x1, x2 = cx - r_x, cx + r_x
  y1, y2 = cy - r_y, cy + r_y
  x1_, x2_ = max(x1, 0), min(x2, X)
  y1_, y2_ = max(y1, 0), min(y2, Y)
  # Crop the image
  crop = image[x1_: x2_, y1_: y2_]
  # Pad the image if the specified size is larger than the input image size
  if crop.ndim == 3:
    crop = np.pad(crop,((x1_ - x1, x2 - x2_), (y1_ - y1, y2 - y2_), (0, 0)),'constant')
  elif crop.ndim == 4:
    crop = np.pad(crop,((x1_ - x1, x2 - x2_), (y1_ - y1, y2 - y2_), (0, 0), (0, 0)),'constant')
  else:
    print('Error: unsupported dimension, crop.ndim = {0}.'.format(crop.ndim))
    exit(0)
  return crop

def crop_image(image,og_size,cx,cy,desired_size):
  X,Y = og_size 
  r_x,r_y = int(desired_size[0] / 2),int(desired_size[1] / 2)
  x1, x2 = cx - r_x, cx + r_x
  y1, y2 = cy - r_y, cy + r_y
  x1_, x2_ = max(x1, 0), min(x2, X)
  y1_, y2_ = max(y1, 0), min(y2, Y)
  # Crop the image
  crop = image[x1_: x2_, y1_: y2_]
  return crop

def load_nii_image(image_path,frames=[],pad = True,dim = [800,800]):
#loads nii to np and can zero pad to dim
#returns padded nps from specific frames
    print("Analysing: " + image_path)
    image_nb = nib.load(image_path)
    head = image_nb.header
    image_data = image_nb.get_fdata()
    [x,y,z,t] = image_data.shape
    if(frames == []):
        frames = np.arange(1,t+1)
    cx,cy = int(x/2),int(y/2)
    image_data_padded = pad_image(image_data,cx,cy,[dim[0],dim[1]])
    image_frames = np.empty([0,dim[0],dim[1],1])
    for i in range(len(frames)):
        frame = image_data_padded[:,:,0,frames[i]-1]
        print(frame.shape)
        print(image_frames.shape)
        frame = frame[np.newaxis,:,:,np.newaxis]
        image_frames = np.append(image_frames,frame,axis = 0) 

    image_frames /= 255.0
    affine = image_nb.affine
#only pad frames that we want doesnt work get mem error :(
#    for i in range(len(frames)):
#        image_data_frame = image_data[:,:,0,frames[i]-1]
#        image_data_frame = image_data_frame[np.newaxis,:,:,np.newaxis]
#        image_frames = np.append(image_frames,image_data_frame,axis = 0)
#    print(image_frames.shape)
#    [t,x,y,z] = image_frames.shape
#    cx,cy = int(x/2),int(y/2)
#    image_data_padded = pad_image(image_frames,cx,cy,[dim[0],dim[1]])
#
#    return_dim = [len(frames),dim[0],dim[1]]
#    print(return_dim)
#    print(image_data_padded.shape)
#    image_ds = np.empty_like(return_dim)

    return image_frames,head,affine


def load_nii_ds(dataset_path,load_cone = True):
#given path to dataset(ie 2CH_dataset)
#get mask filenames and frames
    path_masks = os.path.join(dataset_path,"masks/")
    path_image = os.path.join(dataset_path,"image/")

#mask filenames contain image filenames and specific frames
    masks_filenames = os.listdir(path_masks)
    image_filenames = []
    frames = []

#get image names and frames from mask as well as add full path to masks
    for mask in masks_filenames:
        image_filenames.append(mask[:-10] + mask[-7:])
        frames.append(int(mask[-9:-7]))

    image_headers = []
#get dim information from images and store headers in list 
#TODO
#get largest dim for square image
    for image in image_filenames:
        image_nb = nib.load(os.path.join(path_image,image))
        head = image_nb.header
        image_headers.append(head)
        dim = head.get_data_shape()
#        if (dim[0] > DIM_X):
#            DIM_X = dim[0]
#        if (dim[1] > DIM_Y):
#            DIM_Y = dim[1]

    DIM_X = 800 
    DIM_Y = 800
#load images into numpy arrays with padding to acc every image
    num_samples = len(image_filenames)
    image_ds = np.empty([num_samples,DIM_X,DIM_Y,1])

    for index,image in enumerate(image_filenames):
        print("Analysing: " + image)
        image_nb = nib.load(os.path.join(path_image,image))
        image_data = image_nb.get_fdata()
        [x,y,z,t] = image_data.shape
        cx,cy = int(x/2),int(y/2)
        image_data_padded = pad_image(image_data,cx,cy,[DIM_X,DIM_Y])
        image_data_padded_frame = image_data_padded[:,:,0,frames[index]-1]
        image_ds[index,:,:,0] = image_data_padded_frame

    masks_vent_ds = np.empty([num_samples,DIM_X,DIM_Y,1])
    masks_cone_ds = np.empty([0,DIM_X,DIM_Y,1])
    image_cone_index = []

#    masks_cone_ds = np.empty([0,DIM_X,DIM_Y,1]) 
    for index,mask in enumerate(masks_filenames):
        print("Analysing: " + mask)
        mask_nb = nib.load(os.path.join(path_masks,mask))
        mask_data = mask_nb.get_fdata()
        if(mask_data.ndim == 3):
            [x,y,z] = mask_data.shape
        else:
            [x,y] = mask_data.shape
        cx,cy = int(x/2),int(y/2)
        mask_data_padded = pad_image(mask_data,cx,cy,[DIM_X,DIM_Y])[:,:,0]
        max_mask_val = int(np.amax(mask_data_padded))

        #if there are more than 2 masks
        if(max_mask_val >= 2):
            mask_data_padded_vent = np.copy(mask_data_padded)
            mask_data_padded_vent[np.where(mask_data_padded_vent == 1)] = 0
            masks_vent_ds[index,:,:,0] = mask_data_padded_vent/max_mask_val

            mask_data_padded_cone = np.copy(mask_data_padded)
            mask_data_padded_cone[np.where(mask_data_padded_cone == 2)] = 1
            mask_data_padded_cone = mask_data_padded_cone[np.newaxis,:,:,np.newaxis]
            masks_cone_ds = np.append(masks_cone_ds,mask_data_padded_cone,axis = 0)

            image_cone_index.append(index)
        else:
            masks_vent_ds[index,:,:,0] = mask_data_padded

    #get images associated with cones for cone ds
    print(image_cone_index)
    image_vent_ds = np.copy(image_ds)
#    image_cone_ds = np.empty_like(masks_cone_ds)
#    image_ds.take(image_ds,image_cone_index,axis = 0,out = image_cone_ds)
    image_cone_ds = image_ds[image_cone_index,:,:,:]
    print(image_cone_ds.shape)
    #remap from from 0-255 to 0-1
    image_cone_ds /= 255.0
    image_vent_ds /= 255.0

    if(load_cone == True):
        return image_cone_ds,image_vent_ds,masks_cone_ds,masks_vent_ds,image_headers
    else:
        return image_vent_ds,masks_vent_ds,image_headers




























#def _nii_to_np_array(file_name):
#  image = nib.load(file_name)
#  data = image.get_fdata()
#  return data
#
#def _process_pathname(f_name):
#  image = nib.load(f_name)
#  data = image.get_fdata()
#  head = image.header
#  #f_np = _nii_to_np_array(f_name)
#  image = data
#  return image,head

#def crop_image(image, cx, cy, size):
#  """ Crop a 3D image using a bounding box centred at (cx, cy) with specified size """
#  X, Y = image.shape[:2]
#  r = int(size / 2)
#  x1, x2 = cx - r, cx + r
#  y1, y2 = cy - r, cy + r
#  x1_, x2_ = max(x1, 0), min(x2, X)
#  y1_, y2_ = max(y1, 0), min(y2, Y)
#  # Crop the image
#  crop = image[x1_: x2_, y1_: y2_]
#  # Pad the image if the specified size is larger than the input image size
#  if crop.ndim == 3:
#    crop = np.pad(crop,((x1_ - x1, x2 - x2_), (y1_ - y1, y2 - y2_), (0, 0)),'constant')
#  elif crop.ndim == 4:
#    crop = np.pad(crop,((x1_ - x1, x2 - x2_), (y1_ - y1, y2 - y2_), (0, 0), (0, 0)),'constant')
#  else:
#    print('Error: unsupported dimension, crop.ndim = {0}.'.format(crop.ndim))
#    exit(0)
#  return crop


