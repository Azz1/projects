#!/bin/sh

echo "sudo raspivid -vf -hf -w $1 -h $2 -roi $9,$9,$10,$10 -ss $3 -ISO $4 -br $5 -sh $6 -co $7 -sa $8 -t 999999 -o - | ffmpeg -i - -f mpeg1video -b:v 300k -r 24 http://127.0.0.1:8082/soul/$1/$2"

sudo raspivid -vf -hf -w $1 -h $2 -roi $9,$9,$10,$10 -ss $3 -ISO $4 -br $5 -sh $6 -co $7 -sa $8 -t 999999 -o - | ffmpeg -i - -f mpeg1video -b:v 300k -r 25 http://127.0.0.1:8082/soul/$1/$2 &

