sudo kill -9  `ps -ef | grep raspivid | grep root | egrep -v sudo | awk '{print $2}'`
