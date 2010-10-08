CC=gcc

CFLAGS+=-Wall -std=c99 -D_GNU_SOURCE

TARGETS= eat_packets runfile_scan extract_frames catch_rampers ascii_frame

DEPS = mce_header.h

MAS_CONFIG ?= /usr/mce/bin/mas_config
MAS_BIN ?= $(shell $(MAS_CONFIG) --bin-dir)
INSTALL_DIR=${MAS_BIN}

all: $(TARGETS)

install: $(TARGETS)
	cp $(TARGETS) $(INSTALL_DIR)

eat_packets: eat_packets.o sequence.o mce_header.o $(DEPS) 

extract_frames: extract_frames.o

catch_rampers: catch_rampers.o

runfile_scan: scan.c runfile.o runfile.h
	$(CC) $(CFLAGS) scan.c runfile.o -o runfile_scan

runfile.o: runfile.c runfile.h

tidy:
	-rm *~ *.o

clean: tidy
	-rm $(TARGETS)
