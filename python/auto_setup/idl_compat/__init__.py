"""Compatibility routines.

These routines recreate IDL library routines where native Python or
NumPy/SciPy routines are inadequate.
"""

__all__ = ["deriv", "sign", "smooth"]

from deriv import deriv
from sign import sign
from smooth import smooth
