# app/__init__.py
import sys
import os

# Ensure bheem_core can be found by adding the path
bheem_core_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "env", "src"))
if bheem_core_path not in sys.path:
    sys.path.insert(0, bheem_core_path)