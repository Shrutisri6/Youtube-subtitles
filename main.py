import os
import re
import subprocess
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class AskRequest(BaseModel):
    video_url: str
    topic: str

class AskResponse(BaseModel):
    timestamp: str
    video_url: str
    topic: str


@app.get("/")
def health():
    return {"status": "running"}


def download_subtitles(video_url: str, file_id: str):
    command = [
        "yt-dlp",
        "--write-auto-sub",
        "--skip-download",
        "--sub-lang", "en",
        "--sub-format", "vtt",
        "-o", f"{file_id}.%(ext)s",
        video_url
    ]
    subprocess.run(command, check=True)


def find_timestamp(topic: str, file_id: str) -> str:
    vtt_file = f"{file_id}.en.vtt"

    if not os.path.exists(vtt_file):
        raise Exception("Subtitles not available")

    with open(vtt_file, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.split("\n\n")

    for block in blocks:
        if topic.lower() in block.lower():
            match = re.search(r"\d{2}:\d{2}:\d{2}", block)
            if match:
                return match.group(0)

    return "00:00:00"


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):

    file_id = str(uuid.uuid4())

    try:
        download_subtitles(req.video_url, file_id)
        timestamp = find_timestamp(req.topic, file_id)

        # Cleanup
        for file in os.listdir():
            if file.startswith(file_id):
                os.remove(file)

        return {
            "timestamp": timestamp,
            "video_url": req.video_url,
            "topic": req.topic
        }

    except subprocess.CalledProcessError:
        raise HTTPException(status_code=400, detail="Failed to download subtitles")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
