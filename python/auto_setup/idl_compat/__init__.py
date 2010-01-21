"""Compatibility routines.

These routines recreate IDL library routines where native Python or
NumPy/SciPy routines are inadequate.
"""

__all__ = ["deriv", "smooth"]

from deriv import deriv
from smooth import smooth
