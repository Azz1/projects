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

sudo nodejs  ../nodejs/stream-server.js soul &
sudo python httpserver.py 8080 192.168.111.80 $cameraonly
