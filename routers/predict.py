import sys
import os

# Ensure backend folder is in sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(_HERE), "backend"))

from app.ml.inference import get_models

class Ensemble:
    def reload(self):
        import app.ml.inference
        app.ml.inference._MODELS_CACHE = {}
        try:
            get_models()
        except Exception as e:
            print(f"Failed to pre-warm ensemble cache: {e}")

ensemble = Ensemble()
