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
    
    
    ## Text
    text = cv2.putText(
                      img = frame,
                      text = "ePANDA",
                      org = (0, 50),
                      fontFace = cv2.FONT_HERSHEY_DUPLEX,
                      fontScale = 2.0,
                      color = (125, 246, 55),
                      thickness = 3,
                      lineType = cv2.LINE_AA)
    
    #frame = cv2.resize(frame, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

    #image = np.zeros(frame.shape, np.uint8)


    cv2.imshow('Input', text)

    c = cv2.waitKey(1)
    if c == 27:
        break

cap.release()
cv2.destroyAllWindows()