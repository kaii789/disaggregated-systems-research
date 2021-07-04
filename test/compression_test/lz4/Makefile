CC = gcc
CFLAGS = -Wall -Wextra -fno-ipa-cp
## -fno-ipa-cp is needed such that the compiler does not optimize the function send_lock
## and ALSO keep exactly the same name SEND_LOCK() to it in order to catch it in pintool

## Remove some warnings.
CFLAGS += -Wno-unused-parameter -Wno-unused-variable -Wno-unused-function

all: lz4_test_int lz4_test_float

INC_FILE = 
LIBS += -lpthread -lrt -llz4

## Additional source files
SRC_FILES = lz4_test.c

lz4_test_int: ${SRC_FILES}  ${INC_FILE}
	$(CC) $(CFLAGS) $^ -DINT -o $@ $(LIBS) 

lz4_test_float: ${SRC_FILES}  ${INC_FILE}
	$(CC) $(CFLAGS) $^ -DFLOAT -o $@ $(LIBS) 

clean:
	rm -f lz4_test_int lz4_test_float
