#!/usr/bin/env python3
"""
REST API server for open-dsearch
Usage: uvicorn api_server:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import subprocess
import sys
from pathlib import Path
import json

app = FastAPI(
    title="Open Dsearch API",
    description="Deep research API - 80+ sources in 2.8s",
    version="0.1.0"
)

# CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    topic: str
    top: int = 5
    queries: int = 5
    mode: str = "md"  # md, json, vectors
    timeout: int = 300


class ResearchResponse(BaseModel):
    success: bool
    topic: str
    mode: str
    output: Optional[str] = None
    error: Optional[str] = None
    time_seconds: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    rust_binary: bool
    python_version: str


def get_rust_binary():
    """Get path to Rust binary"""
    script_dir = Path(__file__).parent
    binary = script_dir / "rust" / "target" / "release" / "research"
    return binary if binary.exists() else None


@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "name": "Open Dsearch API",
        "version": "0.1.0",
        "description": "Deep research API - 80+ sources in 2.8s",
        "endpoints": {
            "/research": "POST - Run research query",
            "/health": "GET - Health check",
            "/docs": "GET - API documentation"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    binary = get_rust_binary()
    return HealthResponse(
        status="healthy" if binary else "binary_not_found",
        rust_binary=binary is not None,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )


@app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    """
    Run deep research on a topic
    
    - **topic**: Research topic (required)
    - **top**: Number of sources to fetch (default: 5)
    - **queries**: Number of query variations (default: 5)
    - **mode**: Output format - md, json, or vectors (default: md)
    - **timeout**: Timeout in seconds (default: 300)
    """
    binary = get_rust_binary()
    if not binary:
        raise HTTPException(
            status_code=500,
            detail="Rust binary not found. Build with: cd scripts/rust && cargo build --release"
        )
    
    cmd = [
        str(binary),
        "--topic", request.topic,
        "--top", str(request.top),
        "--query", str(request.queries),
        "--timeout", str(request.timeout),
        "--mode", request.mode,
    ]
    
    try:
        import time
        start = time.time()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=request.timeout + 30
        )
        
        elapsed = time.time() - start
        
        if result.returncode == 0:
            return ResearchResponse(
                success=True,
                topic=request.topic,
                mode=request.mode,
                output=result.stdout,
                time_seconds=round(elapsed, 2)
            )
        else:
            return ResearchResponse(
                success=False,
                topic=request.topic,
                mode=request.mode,
                error=result.stderr,
                time_seconds=round(elapsed, 2)
            )
    
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail=f"Research timed out after {request.timeout} seconds"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Research failed: {str(e)}"
        )


@app.get("/research/sync")
async def research_sync(topic: str, top: int = 5, mode: str = "md"):
    """
    Synchronous research endpoint (GET for easy testing)
    
    - **topic**: Research topic (required)
    - **top**: Number of sources (default: 5)
    - **mode**: Output format (default: md)
    """
    request = ResearchRequest(topic=topic, top=top, mode=mode)
    return await research(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
