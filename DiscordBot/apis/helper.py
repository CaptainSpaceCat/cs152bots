import os

from dotenv import dotenv_values, find_dotenv

_CONFIG = None
def get_config():
    global _CONFIG
    if not _CONFIG:
        _CONFIG = {
            **os.environ,
            **dotenv_values(find_dotenv(".env"))
        }
    return _CONFIG

MISINFO = "Misinformation"
NOT_MISINFO = "Not-misinformation"
UNCLEAR = "Unclear"
