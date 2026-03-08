from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bot_manager import BotManager

app = FastAPI(title="BotForge Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

manager = BotManager()

class BotRequest(BaseModel):
    bot_id: str
    token: str | None = None
    file_path: str | None = None
    file_name: str | None = None
    user_id: str

class LogsRequest(BaseModel):
    bot_id: str
    user_id: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/bots/start")
async def start_bot(req: BotRequest):
    result = await manager.start(req.bot_id, req.token, req.file_path, req.user_id)
    if not result["success"]:
        raise HTTPException(400, result["error"])
    return result

@app.post("/bots/stop")
async def stop_bot(req: BotRequest):
    result = await manager.stop(req.bot_id)
    return result

@app.post("/bots/restart")
async def restart_bot(req: BotRequest):
    await manager.stop(req.bot_id)
    result = await manager.start(req.bot_id, req.token, req.file_path, req.user_id)
    return result

@app.post("/bots/logs")
async def get_logs(req: LogsRequest):
    logs = manager.get_logs(req.bot_id)
    return {"logs": logs}
