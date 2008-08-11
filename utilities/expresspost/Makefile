source=expresspost.py
source_dest=/usr/src/python/expresspost/

init=expresspost
init_dest=/etc/init.d/
init_links=/etc/rc2.d/S90expresspost

install:
	install -m u+rwx,g+rwxs,o+rx --owner=mce --group=mce \
		 -d $(source_dest)
	install -m u+rwx,g+rwxs,o+rx --owner=mce --group=mce \
		 $(source) $(source_dest)
	install -m  u+rwx,g+rwxs,o+rx --owner=mce --group=mce \
		 $(init) $(init_dest)

