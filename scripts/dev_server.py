import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

API_PORT = 8000
WEBAPP_DIR = Path(__file__).resolve().parents[1] / "webapp"


async def run_server(cmd: list[str], name: str, *, cwd: str | None = None, env: dict[str, str] | None = None):
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        env=full_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(f"[{name}] Started PID {proc.pid}: {' '.join(cmd)}")

    async for line in proc.stdout:
        print(f"[{name}] {line.decode().rstrip()}")

    await proc.wait()
    if proc.returncode != 0:
        print(f"[{name}] Exited with code {proc.returncode}")


async def main():
    api = run_server(
        ["uv", "run", "uvicorn", "fluxwall.main:app", "--host", "0.0.0.0", "--port", str(API_PORT), "--reload"],
        "API",
    )
    web = run_server(
        ["npm", "run", "dev"],
        "WEBAPP",
        cwd=str(WEBAPP_DIR),
        env={"VITE_API_BASE": f"http://localhost:{API_PORT}"},
    )

    tasks = [asyncio.create_task(api), asyncio.create_task(web)]

    def shutdown():
        for t in tasks:
            t.cancel()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())