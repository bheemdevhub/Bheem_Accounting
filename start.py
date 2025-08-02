#!/usr/bin/env python3
"""
Startup script that handles both local development and production deployment
"""
import sys
import os
from pathlib import Path

def setup_environment():
    """Setup environment based on deployment context"""
    
    # Check if we're in a container/production environment
    is_production = os.getenv('ENVIRONMENT') == 'production' or Path('/app').exists()
    
    if is_production:
        # Production environment - use mock bheem_core
        print("Production environment detected - using mock bheem_core")
        sys.path.insert(0, '/app/bheem_core_mock')
        sys.path.insert(0, '/app')
    else:
        # Local development environment
        print("Local development environment detected")
        # Add local development paths
        base_path = Path(__file__).parent
        env_src_path = base_path / "env" / "src"
        
        if env_src_path.exists():
            # Add bheem-core path
            bheem_core_path = env_src_path / "bheem-core"
            if bheem_core_path.exists():
                sys.path.insert(0, str(bheem_core_path))
                print(f"Added bheem-core path: {bheem_core_path}")
        
        # Add current directory to path
        sys.path.insert(0, str(base_path))

if __name__ == "__main__":
    setup_environment()
    
    # Now import and run the FastAPI app
    try:
        from main import app
        import uvicorn
        print("Starting FastAPI application...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except ImportError as e:
        print(f"Import error: {e}")
        print("Python path:", sys.path)
        sys.exit(1)
