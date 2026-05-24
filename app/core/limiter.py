# app/core/limiter.py — shared rate limiter instance
#
# Lives in its own file so both main.py and the routers can
# import it without creating a circular import.

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)