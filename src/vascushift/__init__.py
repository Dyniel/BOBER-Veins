"""
BOBER Veins / VascuShift-GPINN:
Physics-Informed Venous Hemodynamics and Optical rPPG under Altered Gravity.
Targeted for the International Space Science and Scientific Payload Competition (ISSSP) 2026.
"""

import sys
import pkgutil

# Python 3.13 compatibility shim for legacy setuptools/pkg_resources imported by torch/triton
if not hasattr(pkgutil, "ImpImporter"):
    class _MockImpImporter:
        pass
    pkgutil.ImpImporter = _MockImpImporter

__version__ = "0.1.0"
__author__ = "Daniel Cieślak"

