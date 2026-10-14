"""
Clinivara: Privacy-First Clinical Document Processing Backend.

Enforces the strict processing invariant:
Original report -> Secure intake -> Extraction -> Normalization ->
Sensitive entity detection -> De-identification -> Independent validation -> Approved output.
"""

__version__ = "1.0.0"
