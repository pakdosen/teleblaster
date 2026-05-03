import asyncio
from functools import wraps


def async_retry(retries: int = 3, base_delay: float = 1.5):
    def deco(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    attempt += 1
                    if attempt > retries:
                        raise
                    await asyncio.sleep(base_delay * attempt)

        return wrapper

    return deco
