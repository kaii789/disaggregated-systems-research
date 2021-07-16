CC = g++
CFLAGS = -O3 -std=c++11 -Wall -Wextra -fno-ipa-cp
## -fno-ipa-cp is needed such that the compiler does not optimize the function send_lock
## and ALSO keep exactly the same name SEND_LOCK() to it in order to catch it in pintool

## Remove some warnings.
CFLAGS += -Wno-unused-parameter -Wno-unused-variable -Wno-unused-function

all: scrimp scrimp_pthread

INC_FILE = 
LIBS += -lpthread -lrt

## Additional source files
SRC_FILES = scrimp.cpp tools.cpp cas_lock.h

scrimp: ${SRC_FILES}  ${INC_FILE}
	$(CC) $(CFLAGS) -DCUSTOM $^ -o $@ $(LIBS)

scrimp_pthread: ${SRC_FILES}  ${INC_FILE}
	$(CC) $(CFLAGS) -DPTHREAD $^ -o $@ $(LIBS)

clean:
	rm -f scrimp scrimp_pthread



