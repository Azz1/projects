PRJ = main
PRJ1 = libepi.so

CFLAGS = -lrt -lpthread 
CFLAGS1 = -fPIC -Wl,-soname,libepi.so -lrt -lpthread 
SRC = arduPi.cpp cmdinterface.cpp


all:
	sudo g++ $(CFLAGS) $(SRC) -o $(PRJ)
	sudo g++ -shared $(CFLAGS1) $(SRC) -o $(PRJ1)
	sudo cp $(PRJ1) /usr/lib/

.PHONY : clean
clean:
	sudo rm $(PRJ)
	sudo rm $(PRJ1)
