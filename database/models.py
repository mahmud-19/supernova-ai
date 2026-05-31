import sys
import os

# Ensure backend folder is in sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(_HERE), "backend"))

from app.models import RetrainingLog
