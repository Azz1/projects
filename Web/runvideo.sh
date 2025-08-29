#!/bin/sh

if [ "$#" -eq 10 ]
then
  echo "sudo rpicam-vid --width $1 --height $2 --roi $9,$9,${10},${10} --shutter $3 --analoggain $4 --brightness $5 --sharpness $6 --contrast $7 --nopreview --saturation $8 -t 999999 -o - | ffmpeg -i - -f mpegts -codec:v mpeg1video -b:v 300k -r 24 http://127.0.0.1:8082/soul/$1/$2"
  sudo rpicam-vid --width $1 --height $2 --roi $9,$9,${10},${10} --shutter $3 --analoggain $4 --brightness $5 --sharpness $6 --contrast $7 --nopreview --saturation $8 -t 999999 -o - | ffmpeg -i - -f mpegts -codec:v mpeg1video -b:v 300k -r 24 http://127.0.0.1:8082/soul/$1/$2 &
elif [ "$#" -eq 11 ]
then
  echo "sudo rpicam-vid ${11} --width $1 --height $2 --roi $9,$9,${10},${10} --shutter $3 --analoggain $4 --brightness $5 --sharpness $6 --contrast $7 --nopreview --saturation $8 -t 999999 -o - | ffmpeg -i - -f mpegts -codec:v mpeg1video -b:v 300k -r 24 http://127.0.0.1:8082/soul/$1/$2"
  sudo rpicam-vid ${11} --width $1 --height $2 --roi $9,$9,${10},${10} --shutter $3 --analoggain $4 --brightness $5 --sharpness $6 --contrast $7 --nopreview --saturation $8 -t 999999 -o - | ffmpeg -i - -f mpegts -codec:v mpeg1video -b:v 300k -r 24 http://127.0.0.1:8082/soul/$1/$2 &
else
  echo "sudo rpicam-vid ${11} ${12} --width $1 --height $2 --roi $9,$9,${10},${10} --shutter $3 --analoggain $4 --brightness $5 --sharpness $6 --contrast $7 --nopreview --saturation $8 -t 999999 -o - | ffmpeg -i - -f mpegts -codec:v mpeg1video -b:v 300k -r 24 http://127.0.0.1:8082/soul/$1/$2"
  sudo rpicam-vid ${11} ${12} --width $1 --height $2 --roi $9,$9,${10},${10} --shutter $3 --analoggain $4 --brightness $5 --sharpness $6 --contrast $7 --nopreview --saturation $8 -t 999999 -o - | ffmpeg -i - -f mpegts -codec:v mpeg1video -b:v 300k -r 24 http://127.0.0.1:8082/soul/$1/$2 &
fi
