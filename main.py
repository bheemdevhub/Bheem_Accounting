# main.py

import sys
import os

# Ensure bheem_core can be found by Python - must be done BEFORE any other imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "env", "src")))

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Now import FastAPI and other modules
from fastapi import FastAPI

# Import the accounting module router
from app.modules.accounting.api.routes import router as module_router

# Create FastAPI app
app = FastAPI(title="Bheem Accounting Module")

# Include accounting router
app.include_router(module_router, prefix="/api/accounting")
