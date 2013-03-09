#!/bin/sh

# find defile.m4
if [ -e /usr/share/aclocal/defile.m4 ]; then
  true # no special option needed
elif [ -e /usr/local/share/aclocal/defile.m4 ]; then
  INCLUDE="-I /usr/local/share/aclocal"
else
  echo "I can't find defile.m4.  If it's in autoconf's search path, you should"
  echo "be able to just run:"
  echo
  echo "  autoreconf -vifs"
  echo
  echo "otherwise, you'll have to tell autotools where to find it:"
  echo
  echo "  autoreconf -vifs -I /path/containing/defile.m4/"
  echo
  echo "Good luck."
  exit 1
fi

autoreconf -vifs $INCLUDE
