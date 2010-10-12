SHELL=/bin/bash

# subdirectories; if the subdirectory contains a Makefile, it will be used,
# otherwise these are simply installed verbatim by the install rule below,
# recursively descending into subdirectories and preserving symlinks
SUBDIRS=python script template test_suite utilities

all clean:
	for d in $(SUBDIRS); do \
		if [ -e $$d/Makefile ]; then \
			( cd $$d && make $@ ); \
		fi \
	done

install:
	@if test -z "${MAS_ROOT}"; then \
		echo "Set MAS_ROOT before running make install."; \
		echo "(Try \"sudo -E make install\")"; \
		false; \
	else \
		install -d ${MAS_ROOT}; \
		for d in $(SUBDIRS); do \
			if [ -e $$d/Makefile ]; then \
				( cd $$d && make $@ ); \
			else \
				dirlist=`find $$d -name .svn -prune -printf '' -o \
						\( -type d -print \)`; \
				grep -v '^#' dne > ${MAS_ROOT}/DO.NOT.EDIT; \
				for s in $$dirlist; do \
					echo "Installing $$s -> ${MAS_ROOT}/$$s"; \
					install -d ${MAS_ROOT}/$$s; \
					grep -v '^#' dne > ${MAS_ROOT}/$$s/DO.NOT.EDIT; \
					filelist=`find $$s -maxdepth 1 -type f`; \
					if test ! -z "$$filelist"; then \
						cp $$filelist ${MAS_ROOT}/$$s; \
					fi; \
					linklist=`find $$s -maxdepth 1 -type l`; \
					if test ! -z "$$linklist"; then \
						for x in $$linklist; do \
							target=`readlink $$x`; \
							name=`basename $$x`; \
							( cd ${MAS_ROOT}/$$s && ln -sf $$target $$name ); \
						done; \
					fi; \
				done; \
			fi; \
		done; \
	fi
