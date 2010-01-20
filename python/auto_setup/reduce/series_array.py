"""MCE auto setup script.

This programme doesn't work!
"""

# This is a semitranslation of the IDL auto_setup_squids program.  The
# intent is to separate that program into three broad parts:
#
#  1) Data acquisition
#  2) Data Reduction and Tuning Calculations
#  3) Reporting (ie. Plots &c.)
#
# Because necessary data is stored after each of the above steps, it is 
# possible to run only part of the procedure, if the location of the output
# of previous step(s) is provided.

# -- Handy ruler ------------------------------------------------------|

import subprocess
import pylab
import mce_data
import numpy
import auto_setup.idl_compat as idl_compat
import auto_setup.util as util

def series_array(directory, file_name, rc, numrows = 33, acq_id = 0,
    ramp_bias = 0, quiet = 0, interactive = 0, poster = 0, slope = 1):

  full_name = directory + file_name + "_ssa"

  rf = mce_data.MCERunfile(full_name + ".run")

  n_frames = rf.Item("FRAMEACQ", "DATA_FRAMECOUNT", "int");

  reg_status = util.register(acq_id, "tune_ramp", full_name, n_frames)

  # If we're not ramping, we need the default sa bias:
  sa_bias_runfile = rf.Item("HEADER", "RB sa bias", "int");
  sa_bias_rc = sa_bias_runfile[(rc - 1) * 8 : (rc * 8) - 1]

  nsum = 48

  # Setting up factors and captions for engineering and AD units.

  # Default is A/D units.
  v_factor = 1./1000.
  v_units = " (AD Units/1000)"
  i_factor = 1./1000.
  i_units = " (AD Units/1000)"

  # converting SA_bias to current
  vmax =  2500. # mV
  RL   = 15000. # Ohms
  ful_scale = 65535. # Digital fs = 2^16 - 1
  ma2uA     = 1000.  # convert to microamperes

  sa_bias = 0 * vmas * ma2uA / (RL * full_scale)

  # Reading the 2-dim data aray from the file:
  readin=read_2d_ramp(full_name, rf, numrows=numrows)
  mcefile=readin["data"]

  #Read labels, loop sizes, etc.
  horiz_label = readin["label"][2]
  vert_label = readin["label"][1]
  card = readin["label"][0]

  n_bias = readin["spec"][0]
  bias_start = readin["spec"][1]
  bias_step = readin["spec"][2]

  n_fb = readin["spec"][3]
  fb_start = readin["spec"][4]
  fb_step = readin["spec"][5]

  #Now, make data arrays of the necessary sizes.
  av_vol  = numpy.empty([n_bias,n_fb,8],dtype="float")
  dev_vol = numpy.empty([n_bias,n_fb,8],dtype="float")

  # calculate mean and stdev of the mean for the reading column of data for
  # each bias value and repeat for all channels.

  for j in range(9):
    for m in range(n_bias):
      for i in range(n_fb):
        av_vol[m,i,j]  = r["data"][...,j,m,i].mean()
        dev_vol[m,i,j] = r["data"][...,j,m,i].std() / sqrt(nsum)

  av_vol *= v_factor
  dev_vol *= v_factor

  # Set up feedback current:
  i_fb = i_factor * ( fb_start + numpy.arange(n_fb) * fb_step)

  # Automatically find the bias, target and corresponding fb
  # we use peak-to-peak merit function

  deriv_av_vol  = numpy.empty([n_bias,n_fb,8],dtype="float")
  mean_av_vol = numpy.empty([n_fb], dtype="float")
  flag=numpy.zero([n_bias,8])
  num_zeros = flag
  estim_range = numpy.empty([n_bias,8], dtype="float")
  ind = numpy.empty([8])
  final_sa_bias_ch_by_ch= numpy.empty([8], dtype="int64")
  target_min_slope_ch_by_ch = numpy.empty([8], dtype="int64")
  fb_min_slope_ch_by_ch = numpy.empty([8], dtype="int64")
  target_half_point_ch_by_ch = numpy.empty([8], dtype="int64")
  fb_half_point_ch_by_ch = numpy.empty([8], dtype="int64")
  SA_target = numpy.empty([8], dtype="int64")
  SA_fb_init = numpy.empty([8], dtype="int64")
  sa_middle = numpy.empty([n_bias,8], dtype="float")

  # calculate the derivatives of the V-phi plots
  for bsa in range(n_bias):
    for chan in range(8):
      deriv_av_vol[bsa, ..., chan] = idl_compat.deriv(i_fb,
          av_vol[bsa, ..., chan])

  # Merit function calculated from the peak-to-peak values
  for bsa in range(n_bias):
    for chan in range(8):
      estim_range[bsa,chan] = av_vol[bsa, ..., chan].max() - \
          av_vol[bsa, ..., chan].min()
      sa_middle[bsa,chan] = (av_vol[bas, ..., chan].max() + \
          av_vol[bsa, ..., chan].min()) / 2.

  if ramp_bias:
    # Make an n_bias + 1 pages set of plots.

    plot_file = directory + "analysis/" + file_name + "_ssa.ps"

    for m in range(n_bias):
      sa_bias = numpy.zeros(8) + bias_start + m * bias_step
      page_label = "%s = %i" % (vert_label, sa_bias)
      for j in range(8):
        # Plot error bars if keyword set.  Error bars are value +- stdev.
        if (errors):
          numpy.errorbar(i_fb, av_vol[m, ..., j], yerr=dev_vol[i, ...])
        else:
          numpy.plot(i_fb, av_vol[m, ..., j])
        numpy.xlabel(horiz_label + i_units)
        numpy.figtext(0,0.5,"Output Voltage" + v_units, rotation='vertical',
            ha='center', va='center') # IDL's ytitle
        numpy.suptitle("RC%i SA Ch %i   peak-to-peak=%g" % (card, j,
          estim_range[m,j]))

      numpy.figtext(0, 1, full_name) # Print filename as title
      numpy.figtext(0.6, 1, page_label) # Print SA_BIAS on title line

    # Merit function calculated from the peak-to-peak values
    for chan in range(8):
      numpy.plot((bias_start + arange(n_bias) * bias_step) / 1000.,
          estim_range[...,chan])
      numpy.xtitle('sa_bias (/1000)')
      numpy.ytitle('peak-to-peak')
      numpy.suptitle('Series Array Channel %i   Card %i' % (chan, card))

    numpy.figtext(0, 1, full_name)
    numpy.figtext(0.6, 1, 'Merit function: peak-to-peak')

  for chan in range(8):
    ind[chan] = estim_range[...,chan].argmax() # method: peak-to-peak

  if (not quiet):
    print """
###########################################################################
SA bias and target (adc_offset) channel by channel:
###########################################################################
 Channel Bias@step (index) Target@half  sa_fb@half 
---------------------------------------------------
    """

  for chan in range(8):
    # MFH - This effective scale is inherited from the original 400 code.
    scale = 5 * n_fb / 400.;
    if scale < 1:
      scale = 1

    deriv_av_vol = idl_compat.deriv(i_fb,
        idl_compat.smooth(av_vol[ind[chan], ..., chan], scale))
    final_sa_bias_ch_by_ch[chan] = round(bias_start + ind[chan] * bias_step)

    # Find position of an SA minimum.  Search range depends on desired
    # locking slope because we will eventually need to find an SA max.
    if (slope > 0):
      min_start = scale * 4
      min_stop = n_fb * 5 / 8
    else:
      min_start = n_fb * 3 / 8
      min_stop = n_fb - scale * 4

    ind_min = av_vol[ind[chan],min_start:min_stop,chan].argmin() + min_start
    min_point = av_vol[ind[chan],ind_min,chan]

    # Now track to the side, waiting for the slope to change.
    if (slope > 0):
      start = ind_min + scale * 2
      stop = n_fb
      step = 1
    else:
      start = ind_min - 2 * scale
      stop = -1
      step = -1
     
    idx = start + step * numpy.arange((stop - start) * step)
    slope_change = numpy.argwhere(deriv_av_vol[idx] * slope < 0)

    if (slope_change.size == 1):
      ind_max = stop - step
    else:
      ind_max = idx[slope_change.min()]

    # Lock on half-way point between minimum and maximum
    ind_half_point = round(0.5 * (ind_min + ind_max))
    target_half_point_ch_by_ch[chan] = round(1000. * av_vol[ind[chan],
      ind_half_point,chan])
    fb_half_point_ch_by_ch[chan] = round(1000. * i_fb[ind_half_point])

    if (not quiet):
      print "%4i %11i %8i %12i %12i" % (chan, final_sa_bias_ch_by_ch[chan],
          ind[chan], target_half_point_ch_by_ch[chan],
          fb_half_point_ch_by_ch[chan])

  SA_target = target_half_point_ch_by_ch
  SA_fb_init = fb_half_point_ch_by_ch

  if (ramp_bias):
    for chan in range(8):
      if ((final_sa_bias_ch_by_ch[chan] > 65535) or
          (final_sa_bias_ch_by_ch[chan] <= 0)):
        if (not quiet):
          print """
###########################################################################

WARNING: SA bias of channel """, chan, """ has been set to zero bacause
         the program found a non valid value

###########################################################################
          """
        else:
          print "%s: SA bias of channel %i is invalid (%i), setting to 0" % \
              (__name__, chan, final_sa_bias_ch_by_ch[chan])
        final_sa_bias_ch_by_ch[chan] = 0
        ind[chan] = 0
      if ((SA_fb_init[chan] > 65536) or (SA_fb_init[chan] <= 0)):
        if (not quiet):
          print """
###########################################################################

WARNING: SA fb of channel """, chan, """ found on the SA V-phi curve has
         been set to 32000 bacause the program found a non valid value

###########################################################################
          """
        else:
          print "%s: SA fb of channel %i is invalid (%i), setting to 0" % \
              (__name__, chan, SA_fb_init[chan])
        SA_fb_init[chan] = 32000

def read_2d_ramp(full_name, rf, numrows=33):
  line=""
  roc=int(rf.Item("FRAMEACQ", "RC")[0])
  loops=rf.Item("par_ramp", "loop_list")
  pars=rf.Item("par_ramp", "par_list " + loops[0])
  first=rf.Item("par_ramp", "par_title " + loops[0] + " " + pars[0])[0]
  steps=rf.Item("par_ramp", "par_step " + loops[0] + " " + pars[0])
  start_1st = int(steps[0])
  step_1st = int(steps[1])
  n_1st = int(steps[2])

  pars=rf.Item("par_ramp", "par_list " + loops[1])
  second=rf.Item("par_ramp", "par_title " + loops[1] + " " + pars[0])[0]
  steps=rf.Item("par_ramp", "par_step " + loops[1] + " " + pars[0])
  start_2nd = int(steps[0])
  step_2nd = int(steps[1])
  n_2nd = int(steps[2])

  label_array = [roc, first, second]

  spec_array = [n_1st, start_1st, step_1st, n_2nd, start_2nd, step_2nd]

  file = mce_data.MCEFile(full_name)

  return {"label": label_array, "spec" : spec_array,
      "data" : file.Read().data.reshape(numrows,8,n_1st,n_2nd)}
