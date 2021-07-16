CC = gcc
CFLAGS = -Wall -Wextra -fno-ipa-cp
## -fno-ipa-cp is needed such that the compiler does not optimize the function send_lock
## and ALSO keep exactly the same name SEND_LOCK() to it in order to catch it in pintool

## Remove some warnings.
CFLAGS += -Wno-unused-parameter -Wno-unused-variable -Wno-unused-function

all: teenage_followers teenage_followers_pthread

INC_FILE = 
LIBS += -lpthread -lrt

## Additional source files
SRC_FILES = teenage_followers.c ../../common/graph.c

teenage_followers: ${SRC_FILES}  ${INC_FILE}
	$(CC) $(CFLAGS) -DCUSTOM  $^ -o $@ $(LIBS)

teenage_followers_pthread: ${SRC_FILES}  ${INC_FILE}
	$(CC) $(CFLAGS) -DPTHREAD $^ -o $@ $(LIBS)


clean:
	rm -f teenage_followers  teenage_followers_pthread

