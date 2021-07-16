CC = gcc
CFLAGS = -Wall -Wextra -fno-ipa-cp
## -fno-ipa-cp is needed such that the compiler does not optimize the function send_lock
## and ALSO keep exactly the same name SEND_LOCK() to it in order to catch it in pintool

## Remove some warnings.
CFLAGS += -Wno-unused-parameter -Wno-unused-variable -Wno-unused-function

all: sssp_int sssp_float sssp_pthread

INC_FILE = 
LIBS += -lpthread -lrt

## Additional source files
SRC_FILES = sssp.c ../../common/graph.c

sssp_int: ${SRC_FILES}  ${INC_FILE}
	$(CC) $(CFLAGS) -DCUSTOM -DINT $^ -o $@ $(LIBS)

sssp_float: ${SRC_FILES}  ${INC_FILE}
	$(CC) $(CFLAGS) -DCUSTOM -DFLOAT $^ -o $@ $(LIBS)


sssp_pthread: ${SRC_FILES}  ${INC_FILE}
	$(CC) $(CFLAGS) -DPTHREAD -DINT $^ -o $@ $(LIBS)


clean:
	rm -f sssp_int sssp_float sssp_pthread
