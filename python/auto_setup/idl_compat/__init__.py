"""Compatibility routines.

These routines recreate IDL library routines where native Python or
NumPy/SciPy routines are inadequate.
"""
from __future__ import absolute_import

__all__ = ["deriv", "smooth"]

from .deriv import deriv
from .smooth import smooth
