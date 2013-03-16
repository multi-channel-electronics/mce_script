# (C) 2013 D. V. Wiebe
#
##########################################################################
#
# This file is part of defile-mas.
#
# defile-mas is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# defile-mas is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with defile-mas; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
AUTOMAKE_OPTIONS = foreign

ACLOCAL_AMFLAGS = -I m4
               
AM_CPPFLAGS = -Wall
AM_CFLAGS = -g -O3
AM_LDFLAGS = -g
defile_LTLIBRARIES = libdefile-mas.la
libdefile_mas_la_SOURCES = defile-mas.c
libdefile_mas_la_LDFLAGS = -module -release $(PACKAGE_VERSION) -shared
libdefile_mas_la_LIBADD = -ldefile

m4/version.m4: m4/.version.stamp
	@if test ! -f $@; then \
		rm -f $<; \
		$(MAKE) $<; \
		fi

m4/.version.stamp: m4/version.m4.new
	@if diff m4/version.m4 m4/version.m4.new >/dev/null 2>&1; then \
		echo "m4/version.m4 is unchanged"; \
		else \
		rm -f m4/version.m4; \
		cp m4/version.m4.new m4/version.m4; \
		fi; \
		touch $@

m4/version.m4.new:
	echo "m4_define(DF_VERSION, [.r`svn info defile-mas.c | awk '/Revision:/ { print $$2 }'`])" > $@

.PHONY: m4/version.m4.new

CONFIGURE_DEPENDENCIES = m4/version.m4
