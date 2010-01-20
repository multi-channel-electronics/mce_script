import time

def filename(rc=None, action=None, array_id=None, directory=None,
        ctime=None):

    if (directory == None):
        directory = ""

    if (ctime == None):
        ctime = time.time();

    ctime_string = "%10i" % (ctime)
    name = ctime_string
    acq_id = ctime_string

    name = directory + "/" + name
    if (array_id != None):
        name += "_" + array_id

    if (rc != None):
        name += "_RC" + rc

    if (action != None):
        name += "_" + action

    return name
