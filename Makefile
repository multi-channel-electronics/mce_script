# subdirectories with their own Makefiles
SUBDIRS=utilities

# subdirectories without Makefiles; these are simply installed verbatim
# by the install rule below
SUBDIRS_INSTALL=python script template test_suite

all:
	for d in $(SUBDIRS); do ( cd $$d && make $@ ); done

install:
	@if test -z "${MAS_ROOT}"; then \
		echo "Set MAS_ROOT before running make install"; false; \
	else \
		install -d ${MAS_ROOT}; \
		for d in $(SUBDIRS); do ( cd $$d && make $@ ); done; \
		dirlist=`find $(SUBDIRS_INSTALL) -name .svn -prune -printf '' -o \
						\( -type d -print \)`; \
		grep -v '^#' dne > ${MAS_ROOT}/DO.NOT.EDIT; \
		for d in $$dirlist; do \
			echo "Installing $$d -> ${MAS_ROOT}/$$d"; \
			install -d ${MAS_ROOT}/$$d; \
			grep -v '^#' dne > ${MAS_ROOT}/$$d/DO.NOT.EDIT; \
			filelist=`find $$d -maxdepth 1 -type f`; \
			if test ! -z "$$filelist"; then \
				cp $$filelist ${MAS_ROOT}/$$d; \
			fi; \
			linklist=`find $$d -maxdepth 1 -type l`; \
			if test ! -z "$$linklist"; then \
				for x in $$linklist; do \
					target=`readlink $$x`; \
					name=`basename $$x`; \
					( cd ${MAS_ROOT}/$$d && ln -sf $$target $$name ); \
				done; \
			fi; \
		done; \
	fi
