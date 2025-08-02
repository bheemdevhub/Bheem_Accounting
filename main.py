# main.py
from fastapi import FastAPI
from app.modules.accounting.api.routes import router as module_router

app = FastAPI(title="Bheem accounting Module")
app.include_router(module_router, prefix="/api/accounting")
