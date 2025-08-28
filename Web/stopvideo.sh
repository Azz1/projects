sudo kill -9  `ps -ef | grep rpicam-vid | grep root | egrep -v sudo | awk '{print $2}'`
