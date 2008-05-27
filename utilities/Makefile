CC=gcc

CFLAGS+=-Wall

TARGETS= eat_packets runfile_scan extract_frames ascii_frame

INSTALL_DIR=..

all: $(TARGETS)

install: $(TARGETS)
	cp $(TARGETS) $(INSTALL_DIR)

eat_packets: eat_packets.o sequence.o

extract_frames: extract_frames.o

runfile_scan: scan.c runfile.o runfile.h
	$(CC) $(CFLAGS) scan.c runfile.o -o runfile_scan

ascii_frame: ascii_frame.o

runfile.o: runfile.c runfile.h

tidy:
	-rm *~ *.o

clean: tidy
	-rm $(TARGETS)
