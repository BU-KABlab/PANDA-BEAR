# -*- coding: utf-8 -*-
"""
Created on Tue Jun 27 14:57:23 2023

@author: Kab Lab
"""

import cv2
import numpy as np

cap = cv2.VideoCapture(0)

# Check if the webcam is opened correctly
if not cap.isOpened():
    raise IOError("Cannot open webcam")

while True:
    ret, frame = cap.read()
    width = int(cap.get(3))
    height = int(cap.get(4))
    
    ## lines
    #line1 = cv2.line(frame, (0,0),(width,height), (255,0,0),(10))
    #line2 = cv2.line(line1, (0,height),(width,0), (255,0,0),(10))
    
    ## rectangles
    #rect = cv2.rectangle(frame, (100,100), (200,200), (128,128,128),5)
    
    
    
    frame = cv2.resize(frame, None, fx=1, fy=1, interpolation=cv2.INTER_AREA)
    
    crop_img = frame[100:height-100, 210:width-180]
    
    # convert image to grayscale
    gray_img = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
      
    # Shi-Tomasi corner detection function
    # We are detecting only 100 best corners here
    # You can change the number to get desired result.
    corners = cv2.goodFeaturesToTrack(gray_img, 200, 0.7, 10)
      
    # convert corners values to integer
    # So that we will be able to draw circles on them
    corners = np.int0(corners)
      
    # draw red color circles on all corners
    for i in corners:
        x, y = i.ravel()
        cv2.circle(crop_img, (x, y), 3, (255, 0, 0), -1)
  
    ## Text
    # text = cv2.putText(
    #                   img = frame,
    #                   text = "ePANDA",
    #                   org = (0, 25),
    #                   fontFace = cv2.FONT_HERSHEY_DUPLEX,
    #                   fontScale = 1.0,
    #                   color = (125, 246, 55),
    #                   thickness = 1,
    #                   lineType = cv2.LINE_AA)
    
    

    #image = np.zeros(frame.shape, np.uint8)


    cv2.namedWindow('ePANDA Cam',cv2.WINDOW_NORMAL)
    cv2.imshow('ePANDA Cam', crop_img)
    c = cv2.waitKey(1)
    if c == 27:
        break

cap.release()
cv2.destroyAllWindows()