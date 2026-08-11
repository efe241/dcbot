import sys
import os

# Add root directory to path so functions can import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from firebase_functions import https_fn
from backend.main import app
from mangum import Mangum

# Wrap FastAPI ASGI application with Mangum for AWS Lambda / Firebase Cloud Functions
handler = Mangum(app, lifespan="off")

@https_fn.on_request(min_instances=0, max_instances=10)
def api(req: https_fn.Request) -> https_fn.Response:
    return handler(req)
