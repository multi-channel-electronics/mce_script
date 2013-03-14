CC=gcc -std=c99

CPPFLAGS += -D_GNU_SOURCE
CFLAGS += -Wall

TARGETS= eat_packets runfile_scan extract_frames catch_rampers ascii_frame \
				 defile-mas-phony

DEPS = mce_header.h

all: $(TARGETS)

install: $(TARGETS)
	@if test -z "${MAS_VAR}"; then \
		echo "Set MAS_VAR before running make install."; \
		echo "(If MAS_VAR *is* set, try \"sudo -E make install\")"; \
		false; \
	else \
		export MAS_BIN=$$($$MAS_VAR --bin-dir); \
		export MAS_GROUP=$$($$MAS_VAR --group); \
		install -m 0755 -g $$MAS_GROUP -d $$MAS_BIN; \
		install -m 2755 -g $$MAS_GROUP $(TARGETS) $$MAS_BIN; \
		if [ -e defile-mas/Makefile ]; then cd defile-mas && ${MAKE} install; fi \
	fi

eat_packets: eat_packets.o sequence.o mce_header.o $(DEPS) 

extract_frames: extract_frames.o

catch_rampers: catch_rampers.o

runfile_scan: scan.o runfile.o
	$(CC) $(LDFLAGS) -o runfile_scan scan.o runfile.o

scan.o runfile.o :: runfile.h

# only deal with defile-mas if someone has gone in and build the Makefile
# previously
.PHONY: defile-mas-phony
defile-mas-phony: 
	@if [ -e defile-mas/Makefile ]; then cd defile-mas && ${MAKE}; fi

tidy:
	rm -f *~ *.o

clean: tidy
	@if [ -e defile-mas/Makefile ]; then cd defile-mas && ${MAKE} clean; fi
	rm -f $(TARGETS)
