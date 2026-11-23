import sys
from pathlib import Path

from mangum import Mangum

backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend))

from app.main import app

handler = Mangum(app)
