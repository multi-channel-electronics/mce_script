CC=gcc

CFLAGS+=-Wall

TARGETS= eat_packets runfile_scan extract_frames catch_rampers ascii_frame

INSTALL_DIR=/usr/mce/bin

all: $(TARGETS)

install: $(TARGETS)
	cp $(TARGETS) $(INSTALL_DIR)

eat_packets: eat_packets.o sequence.o

extract_frames: extract_frames.o

catch_rampers: catch_rampers.o

runfile_scan: scan.c runfile.o runfile.h
	$(CC) $(CFLAGS) scan.c runfile.o -o runfile_scan

runfile.o: runfile.c runfile.h

tidy:
	-rm *~ *.o

clean: tidy
	-rm $(TARGETS)
