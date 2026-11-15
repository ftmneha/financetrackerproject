"""
Routes module for Personal Finance Tracker.
Provides routes when using a modular Blueprint architecture,
or references routes defined in app.
"""
from app import app

# All application routes are centrally managed and registered in app.py.
# This module is retained for modular extensibility and backward compatibility.
__all__ = ["app"]
