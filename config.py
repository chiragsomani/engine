from datetime import datetime
from zoneinfo import ZoneInfo
import os

IST = ZoneInfo('Asia/Kolkata')
OPENALGO_BASE_URL = os.getenv("OPENALGO_BASE_URL", "http://127.0.0.1:5000")
API_KEY = os.getenv("API_KEY")
STRATEGY = os.getenv("STRATEGY")

if not API_KEY:
    raise ValueError("API_KEY is not set in environment variables!")
if not STRATEGY:
    raise ValueError("STRATEGY name is not set in environment variables!")