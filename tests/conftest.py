"""
Pytest configuration and environment shims.
"""

import pkgutil

# Python 3.13 compatibility shim for torch/triton legacy pkg_resources
if not hasattr(pkgutil, "ImpImporter"):
    class _MockImpImporter:
        pass
    pkgutil.ImpImporter = _MockImpImporter

