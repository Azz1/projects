#!/bin/sh

sudo raspivid -w 700 -h 525 -br 50 -ss 15000 -ISO 800 -sh 0 -co 0 -sa 0 -t 999999 -o - | nc 192.168.111.99 5001
