#!/bin/sh

#usage:
#  gf.sh <filename> <num_frames> <interval>

echo "gphoto2 --capture-image-and-download --frames $2 --interval $3 --filename /home/pi/projects/gphoto2/$1-%Y%m%d_%H%M%S_%f.%C"
gphoto2 --capture-image-and-download --frames $2 --interval $3 --filename /home/pi/projects/gphoto2/$1-%Y%m%d_%H%M%S_%f.%C
