OPTIND=1         # Reset in case getopts has been used previously in the shell.

# Initialize our own variables:
cameraonly=N

while getopts "h?c" opt; do
    case "$opt" in
    h|\?)
	echo "Usage: start.sh [-h -? -c]"
	echo " -h -? -------- get help"
	echo " -c ----------- camera only mode"
        exit 0
        ;;
    c)  cameraonly=Y
        ;;
    esac
done

myip=`python3 ./getip.py`
echo "current ip: " $myip
#sudo nodejs  ../nodejs/stream-server.js soul &
sudo nodejs  ../nodejs/websocket-relay.js soul &
sudo ~/env/bin/python3 httpserver.py 8080 $myip $cameraonly
