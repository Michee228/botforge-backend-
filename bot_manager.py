import asyncio
import subprocess
import os
import tempfile
import httpx
from datetime import datetime
from collections import defaultdict

class BotManager:
    def __init__(self):
        self.processes: dict[str, subprocess.Popen] = {}
        self.logs: dict[str, list] = defaultdict(list)

    def _add_log(self, bot_id: str, message: str, log_type: str = "info"):
        self.logs[bot_id].append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "type": log_type,
        })
        # Keep last 200 logs
        if len(self.logs[bot_id]) > 200:
            self.logs[bot_id] = self.logs[bot_id][-200:]

    async def _download_file(self, file_path: str, user_id: str) -> str:
        """Download bot file from Supabase storage"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            raise Exception("Supabase not configured")

        url = f"{supabase_url}/storage/v1/object/bot-files/{file_path}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={
                "Authorization": f"Bearer {supabase_key}",
                "apikey": supabase_key,
            })
            if resp.status_code != 200:
                raise Exception(f"Failed to download file: {resp.status_code}")

        # Save to temp directory
        bot_dir = os.path.join(tempfile.gettempdir(), "botforge", user_id)
        os.makedirs(bot_dir, exist_ok=True)
        file_name = file_path.split("/")[-1]
        local_path = os.path.join(bot_dir, file_name)

        with open(local_path, "wb") as f:
            f.write(resp.content)

        return local_path

    async def start(self, bot_id: str, token: str, file_path: str, user_id: str):
        if bot_id in self.processes and self.processes[bot_id].poll() is None:
            return {"success": False, "error": "Bot already running"}

        try:
            self._add_log(bot_id, "Téléchargement du fichier...")
            local_path = await self._download_file(file_path, user_id)
            self._add_log(bot_id, f"Fichier téléchargé: {local_path}")

            # Install dependencies if requirements.txt exists
            req_path = os.path.join(os.path.dirname(local_path), "requirements.txt")
            if os.path.exists(req_path):
                self._add_log(bot_id, "Installation des dépendances...")
                subprocess.run(["pip", "install", "-r", req_path], capture_output=True)

            # Start the bot process
            env = os.environ.copy()
            env["TELEGRAM_BOT_TOKEN"] = token
            self._add_log(bot_id, "Démarrage du bot...")

            process = subprocess.Popen(
                ["python", local_path],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.processes[bot_id] = process
            self._add_log(bot_id, "Bot démarré avec succès ✅")

            # Start log reader in background
            asyncio.create_task(self._read_output(bot_id, process))

            return {"success": True, "pid": process.pid}

        except Exception as e:
            self._add_log(bot_id, f"Erreur: {str(e)}", "error")
            return {"success": False, "error": str(e)}

    async def _read_output(self, bot_id: str, process: subprocess.Popen):
        """Read stdout/stderr in background"""
        loop = asyncio.get_event_loop()
        
        async def read_stream(stream, log_type):
            while True:
                line = await loop.run_in_executor(None, stream.readline)
                if not line:
                    break
                self._add_log(bot_id, line.strip(), log_type)

        await asyncio.gather(
            read_stream(process.stdout, "info"),
            read_stream(process.stderr, "error"),
        )
        self._add_log(bot_id, "Processus terminé", "warning")

    async def stop(self, bot_id: str):
        if bot_id not in self.processes:
            return {"success": True, "message": "Bot not running"}

        process = self.processes[bot_id]
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        del self.processes[bot_id]
        self._add_log(bot_id, "Bot arrêté ⏹️")
        return {"success": True}

    def get_logs(self, bot_id: str):
        return self.logs.get(bot_id, [])
