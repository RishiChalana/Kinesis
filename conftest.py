"""Make the project root importable so `ml.*` / `backend.*` resolve under pytest."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
