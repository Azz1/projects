#!/bin/sh

sudo rpicam-vid --codec libav -width 700 -height 524 --brightness 0 --shutter 15000 --analoggain 8 --sharpness 1 --contrast 1 --saturation 0 -t 999999 -o - | nc 192.168.111.99 5001
