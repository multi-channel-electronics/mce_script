SHELL=/bin/bash

# subdirectories; if the subdirectory contains a Makefile and/or configure
# script and/or configure.ac file, they will be handled.  If none of these
# are present, the contents of the directory are simply installed verbatim by
# the install rule below, recursively descending into subdirectories and
# preserving symlinks
SUBDIRS:=idl_pro python script template test_suite utilities

# conditionalise defile-mas on whether the defile program is insalled
DEFILE=$(shell which defile)
ifneq (${DEFILE},)
SUBDIRS:=defile-mas ${SUBDIRS}
endif

all clean:
	for d in $(SUBDIRS); do \
		if [ -e $$d/Makefile ]; then \
			( cd $$d && make $@ ); \
		elif [ -e $$d/configure ]; then \
			( cd $$d && ./configure && make $@ ) \
		elif [ -e $$d/configure.ac ]; then \
		  ( cd $$d && autoreconf -vifs && ./configure && make $@ ); \
		fi; \
	done

# The identity file; because "make install" is usually run via sudo, we
# take care to report the real instead of effective user.
id:
	@echo " MCE SCRIPT INSTALLATION IDENTITY" > id
	@echo "----------------------------------" >> id
	@echo >> id
	@echo "Install date: `date -u`" >> id
	@if [ -z $$SUDO_USER ]; then \
		echo "Installed by: $$USER" >> id; \
	else \
		echo "Installed by: $$SUDO_USER" >> id; \
	fi
	@echo "Install host: $$HOSTNAME" >> id
	@echo >> id
	@echo "Source path: `pwd`" >> id
	@echo "SVN version: `svnversion`" >> id
	@echo >> id
	@echo "SVN Info:" >> id
	@svn info | tail -n +2 | sed -e 's/^/    /' >> id
	@if [ ! -z $$SUDO_USER ]; then chown $$SUDO_USER:$$SUDO_GROUP id; fi

# Force regeneration of the id file whenever "make install" is run.
.PHONY: id

install: id
	@if test -z "$$MAS_VAR"; then \
		echo "Set MAS_VAR before running make install."; \
		echo "(If MAS_VAR *is* set, try \"sudo -E make install\")"; \
		exit 1; \
	fi;
	@if test ! -x $$MAS_VAR; then \
		echo "$$MAS_VAR is not executable!  Cannot continue"; \
		exit 1; \
	fi
	@export MAS_ROOT=$$($$MAS_VAR --mas-root); \
	if [ -d $$MAS_ROOT -a `stat --printf=%i .` = `stat --printf=%i $$MAS_ROOT` ]; then \
		echo "Install path $$MAS_ROOT is the same as the source directory!"; \
		exit 1; \
	fi; \
	export MAS_USER=$$($$MAS_VAR --user); \
	export MAS_GROUP=$$($$MAS_VAR --group); \
	install -vm 2755 -o $${MAS_USER} -g $${MAS_GROUP} -d $${MAS_ROOT}; \
	for d in $(SUBDIRS); do \
		if [ -e $$d/Makefile ]; then \
			( cd $$d && make $@ ); \
		else \
			dirlist=`find $$d -name .svn -prune -printf '' -o \
					\( -type d -print \)`; \
			grep -v '^#' dne > $${MAS_ROOT}/DO.NOT.EDIT; \
			chown $${MAS_USER}:$${MAS_GROUP} $${MAS_ROOT}/DO.NOT.EDIT; \
			for s in $$dirlist; do \
				echo "Installing $$s -> $${MAS_ROOT}/$$s"; \
				install -vm 2755 -o $${MAS_USER} -g $${MAS_GROUP} -d $${MAS_ROOT}/$$s; \
				grep -v '^#' dne > $${MAS_ROOT}/$$s/DO.NOT.EDIT; \
				chown $${MAS_USER}:$${MAS_GROUP} $${MAS_ROOT}/$$s/DO.NOT.EDIT; \
				filelist=`find $$s -maxdepth 1 -type f -executable`; \
				if test ! -z "$$filelist"; then \
					install -vm 2755 -o $${MAS_USER} -g $${MAS_GROUP} $$filelist $${MAS_ROOT}/$$s; \
				fi; \
				filelist=`find $$s -maxdepth 1 -type f \\! -executable`; \
				if test ! -z "$$filelist"; then \
					install -vm 0644 -o $${MAS_USER} -g $${MAS_GROUP} $$filelist $${MAS_ROOT}/$$s; \
				fi; \
				linklist=`find $$s -maxdepth 1 -type l`; \
				if test ! -z "$$linklist"; then \
					for x in $$linklist; do \
						target=`readlink $$x`; \
						name=`basename $$x`; \
						( cd $${MAS_ROOT}/$$s && ln -sf $$target $$name ); \
					done; \
				fi; \
			done; \
		fi; \
	done; \
	install -vm 0644 -o $${MAS_USER} -g $${MAS_GROUP} id $${MAS_ROOT};
