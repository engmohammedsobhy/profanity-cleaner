import os
import json
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import streamlit_workflows as workflows

app = FastAPI(title="Profanity Cleaner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = os.path.join(tempfile.gettempdir(), "profanity_cleaner_api_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

class TextProcessRequest(BaseModel):
    raw_text: str
    options: dict

@app.post("/api/process_text")
async def process_text(request: TextProcessRequest):
    try:
        # progress_callback is None because we can't emit progress updates over basic HTTP requests
        result = workflows.process_text_content(request.raw_text, request.options, "", None)
        return JSONResponse(content={"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/api/process_media")
async def process_media(file: UploadFile = File(...), options: str = Form(...)):
    try:
        opts = json.loads(options)
        
        # Save uploaded file temporarily for processing
        suffix = os.path.splitext(file.filename)[1]
        fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=OUTPUT_DIR)
        with os.fdopen(fd, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        result = workflows.process_media_file(temp_path, opts, None, None)
        
        return JSONResponse(content={"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/api/download")
async def download_file(path: str):
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"status": "error", "message": "File not found"})
    return FileResponse(path, filename=os.path.basename(path))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
