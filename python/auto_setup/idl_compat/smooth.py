from __future__ import division
from past.utils import old_div
import numpy

def smooth(a, w):
  """Box-car smooth array a with a kernel of width w.

This is an implementation of IDL's SMOOTH function, except it does
something slightly less lame with the end points.
"""
  if (a.ndim != 1):
    raise ValueError("Input must be single dimensional")

  if (a.size < w):
    raise ValueError("Input must be longer than the smoothing kernel")

  # the trivial case
  if (w < 3):
    return a

  # ensure w is odd
  if (not w % 2):
    w=w+1

  # reflect the input on the edges
  s = numpy.r_[2 * a[0] - a[w:1:-1], a, 2 * a[-1]-a[-1:-w:-1]]

  # perform the convolution
  y = numpy.convolve(old_div(numpy.ones(w,'d'),w), s, mode='same')

  return y[w-1:-w+1]
