dnl (C) 2012 D. V. Wiebe
dnl
dnllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllll
dnl
dnl This file is part of defile-mas.
dnl
dnl defile-mas is free software; you can redistribute it and/or modify it
dnl under the terms of the GNU General Public License as published by the
dnl Free Software Foundation; either version 2 of the License, or (at your
dnl option) any later version.
dnl
dnl defile-mas is distributed in the hope that it will be useful, but WITHOUT
dnl ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
dnl FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
dnl License for more details.
dnl
dnl You should have received a copy of the GNU Lesser General Public License
dnl along with defile-mas; if not, write to the Free Software Foundation,
dnl Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
dnl

m4_include([m4/version.m4])

AC_INIT([defile-mas], [DF_VERSION], [dvw@ketiltrout.net])

AC_PREREQ([2.63])
AC_CONFIG_MACRO_DIR([m4])

LT_PREREQ([2.2.6b])

AC_CONFIG_SRCDIR([defile-mas.c])
AC_CONFIG_HEADER([config.h])

AM_INIT_AUTOMAKE

AC_PROG_CC
AC_PROG_CC_C_O
AC_HEADER_STDC

dnl headers

dnl data types

dnl functions

dnl libtool
LT_INIT

dnl defile
DF_CHECK_DEFILE_H
DF_CHECK_LIBDEFILE
DF_CHECK_DEFILE
DF_PLUGIN_PATH

dnl output
AC_CONFIG_FILES([Makefile])

AC_OUTPUT
