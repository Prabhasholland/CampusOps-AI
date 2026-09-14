"""Compatibility shim for app/calle_client.py pointing to app.calle modules."""

from .calle.client import CalleClient
from .calle.results import CallResult, parse_call_response

__all__ = ["CalleClient", "CallResult", "parse_call_response"]
