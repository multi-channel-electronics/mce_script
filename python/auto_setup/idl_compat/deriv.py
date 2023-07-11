from __future__ import division
from past.utils import old_div
import numpy

def deriv(x, y=None):
  """Perform numerical differentiation on an array.

This is an implementation of IDL's DERIV function; it performs
numerical differentiation using 3-point Lagrangian interpolation.  It
returns an array of the same length as its input.
"""
  if (x is None and y is None):
    raise TypeError("No data.")
  if (y is None):
    y = x
    x = numpy.arange(y.size)
  elif (x is None):
    x = numpy.arange(y.size)

  n = x.size
  if (n != y.size):
    raise TypeError("x and y must be the same size")

  #floatify
  xx = x.astype("float")

  # conveniences
  x12 = xx - numpy.roll(xx,-1)
  x01 = numpy.roll(xx,1) - xx
  x02 = numpy.roll(xx,1) - numpy.roll(xx,-1)

  d = numpy.empty([n], dtype="float")
  # middle points
  d = numpy.roll(y,1) * (old_div(x12, (x01 * x02))) + y * (old_div(1., x12) - old_div(1., x01)) \
      - numpy.roll(y,-1) * (old_div(x01, (x02 * x12)))

  # formulae for the first and last points:
  d[0] = y[0] * (x01[1] + x02[1]) / (x01[1] * x02[1]) - y[1] * x02[1] \
      / (x01[1] * x12[1]) + y[2] * x01[1] / (x02[1] * x12[1])

  n2 = n - 2
  d[n - 1] = -y[n - 3] * x12[n2] / (x01[n2] * x02[n2]) \
      + y[n2] * x02[n2] / (x01[n2] * x12[n2]) \
      - y[n - 1] * (x02[n2] + x12[n2]) / (x02[n2] * x12[n2])

  return d
