from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bot_manager import BotManager

app = FastAPI()
manager = BotManager()


class BotRequest(BaseModel):
    bot_id: str
    token: str | None = None
    file_path: str | None = None
    file_name: str | None = None
    file_content: str | None = None
    user_id: str


@app.post("/bots/start")
async def start_bot(req: BotRequest):
    try:
        result = manager.start(
            bot_id=req.bot_id,
            token=req.token,
            file_content=req.file_content,
            file_name=req.file_name,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bots/stop")
async def stop_bot(req: BotRequest):
    try:
        result = manager.stop(bot_id=req.bot_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bots/restart")
async def restart_bot(req: BotRequest):
    try:
        manager.stop(bot_id=req.bot_id)
        result = manager.start(
            bot_id=req.bot_id,
            token=req.token,
            file_content=req.file_content,
            file_name=req.file_name,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bots/status/{bot_id}")
async def bot_status(bot_id: str):
    return manager.status(bot_id)


@app.get("/bots/logs/{bot_id}")
async def bot_logs(bot_id: str):
    return manager.get_logs(bot_id)


@app.get("/health")
async def health():
    return {"status": "ok"}
