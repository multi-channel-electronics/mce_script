import time

def filename(rc=None, action=None, array_id=None, directory=None,
        ctime=None):

    if (directory is None):
        directory = ""

    if (ctime is None):
        ctime = time.time();

    ctime_string = "%10i" % (ctime)
    name = ctime_string
    acq_id = ctime_string

    name = directory + "/" + name
    if (array_id is not None):
        name += "_" + array_id

    if (rc is not None):
        name += "_RC" + rc

    if (action is not None):
        name += "_" + action

    return name
