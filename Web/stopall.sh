sudo kill -9  `ps -ef | grep python | grep root | egrep -v sudo | awk '{print $2}'`
sudo kill -9  `ps -ef | grep nodejs | grep root | egrep -v sudo | awk '{print $2}'`
