HOST_DIR := .
BUILDDIR ?= ../bin


HOST_TARGET := ${BUILDDIR}/sls

HOST_SOURCES := $(wildcard ${HOST_DIR}/*.c)

.PHONY: all clean 

__dirs := $(shell mkdir -p ${BUILDDIR})

#COMMON_FLAGS := -Wall -Wextra -Werror -g -I${COMMON_INCLUDES}
COMMON_FLAGS := -Wall -Wextra -g -I${COMMON_INCLUDES}
HOST_FLAGS := ${COMMON_FLAGS} -std=c11 -O3 

all: ${HOST_TARGET} 

${HOST_TARGET}: ${HOST_SOURCES} ${COMMON_INCLUDES} 
	$(CC) -o $@ ${HOST_SOURCES} ${HOST_FLAGS}

clean:
	$(RM) -r $(BUILDDIR)
