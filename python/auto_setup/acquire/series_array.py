# -- Handy ruler ------------------------------------------------------|

import subprocess

def series_array(file_name, rc, ramp_bias = 0, quiet = 0,
        directory="/data/cryo/current_data"):
    """Ramp the SA bias and feedback to acquire a V-phi curve.  The 
    
    Returns None.  
    """

    rc_name=rc.replace(' ','')

    # Communication
    if (not quiet):
        if (ramp_bias):
            print """

###########################################################################
#2) The second step is to ramp the SSA bias (together with the SSA fb) for
#  """, rc_name, """and choose the bias for which the peak-to-peak of the
#   V-pi curve is maximum.
###########################################################################
            """
        else:
            print """
###########################################################################
#2) The second step is to ramp the SA fb to measure the SA V-phi curve for
#  """, rc_name, """
###########################################################################
            """
    elif (quiet == 1):
        print __name__, ": starting for", rc_name

    # Set ramp_sa_file_name
    ctime = file_name.rjust(10,"0")
    logfile = ctime + "/" + ctime + ".log"

    exit_status = subprocess.call("ramp_sa_fb " + file_name + "_ssa " + rc +
            " " + ramp_bias + " >> " + directory + "/" + logfile, shell=True)

    if (exit_status != 0):
        if (quiet != 0):
            print __name__, ": error ", exit_status, " from ramp_sa_fb"
        else:
            print """

###############################################################
# ERROR! AN ERROR HAS OCCURED WHEN RUNNING THE RAMP_SA SCRIPT #
###############################################################

            """
        return 4
    return None
