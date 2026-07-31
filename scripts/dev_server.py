import asyncio
import subprocess
import signal
import sys

API_PORT = 8000
UI_PORT = 8501


async def run_server(cmd: list[str], name: str):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
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
    ui = run_server(
        ["uv", "run", "streamlit", "run", "src/fluxwall/streamlit_app.py",
         "--server.port", str(UI_PORT), "--server.headless", "true"],
        "UI",
    )

    tasks = [asyncio.create_task(api), asyncio.create_task(ui)]

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
