"""Shared rate limiter instance (slowapi).

In-memory storage is fine for a single process. For multiple instances behind a
load balancer, point slowapi at Redis via the `storage_uri` argument.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
