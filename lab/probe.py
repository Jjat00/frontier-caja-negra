"""Experimentos contra el servicio original.

Cada request al original queda en experimentos.jsonl con el formato del README
(id, seq, x_req, hipotesis, request, status, response, conclusion).

Uso como librería:
    from lab.probe import Lab
    lab = Lab()
    lab.reset("s3")                       # nueva secuencia (reset del token)
    lab.msg("PING;64", "PING responde sin estado")
    lab.conclude("responde pong")         # conclusión del último experimento

Uso por consola:
    uv run python -m lab.probe reset s3
    uv run python -m lab.probe msg s3 "PING;64" "hipótesis"
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

BASE = os.getenv("ORIGINAL_URL", "https://caja-negra-production-c64f.up.railway.app")
TOKEN = os.environ.get("TOKEN", "")
LOG = ROOT / "experimentos.jsonl"
MIN_INTERVAL = 0.11  # límite de 10 requests por segundo por token

_lock = threading.Lock()


class Lab:
    def __init__(self, token: str = TOKEN, log: Path = LOG):
        self.client = httpx.Client(base_url=BASE, timeout=10)
        self.token = token
        self.log = log
        self.seq = "s0"
        self._last = 0.0
        self._last_id: int | None = None

    def _next_id(self) -> int:
        if not self.log.exists():
            return 1
        lines = [l for l in self.log.read_text().splitlines() if l.strip()]
        return json.loads(lines[-1])["id"] + 1 if lines else 1

    def _throttle(self) -> None:
        wait = self._last + MIN_INTERVAL - time.time()
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def raw(self, method: str, path: str, *, body=None, content=None, token: str | None = "default",
            headers: dict | None = None) -> httpx.Response:
        """Request sin registrar (para explorar rutas, métodos y headers)."""
        self._throttle()
        h = dict(headers or {})
        tok = self.token if token == "default" else token
        if tok is not None:
            h["Authorization"] = f"Bearer {tok}"
        resp = self.client.request(method, path, json=body, content=content, headers=h)
        if resp.headers.get("X-Frontier-Infra") == "rate-limit":
            time.sleep(1)
            return self.raw(method, path, body=body, content=content, token=token, headers=headers)
        return resp

    def reset(self, seq: str) -> int:
        self.seq = seq
        return self.raw("POST", "/__reset").status_code

    def send(self, request, hipotesis: str, *, path: str = "/msg", method: str = "POST", **kw) -> dict:
        """Manda un request y lo registra en el log. `request` es el cuerpo JSON."""
        resp = self.raw(method, path, body=request, **kw)
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        with _lock:
            row = {
                "id": self._next_id(),
                "seq": self.seq,
                "x_req": resp.headers.get("X-Req"),
                "hipotesis": hipotesis,
                "request": request,
                "status": resp.status_code,
                "response": body,
            }
            if path != "/msg" or method != "POST":
                row["ruta"] = f"{method} {path}"
            with self.log.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            self._last_id = row["id"]
        return row

    def msg(self, m: str, hipotesis: str) -> dict:
        return self.send({"m": m}, hipotesis)

    def conclude(self, conclusion: str, ids: list[int] | None = None) -> None:
        """Agrega la conclusión a uno o varios experimentos (por defecto, el último)."""
        targets = set(ids or [self._last_id])
        rows = [json.loads(l) for l in self.log.read_text().splitlines() if l.strip()]
        for r in rows:
            if r["id"] in targets:
                r["conclusion"] = conclusion
        self.log.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def main() -> None:
    lab = Lab()
    cmd, *args = sys.argv[1:]
    if cmd == "reset":
        print(lab.reset(args[0]))
    elif cmd == "msg":
        lab.seq = args[0]
        print(json.dumps(lab.msg(args[1], args[2]), ensure_ascii=False))


if __name__ == "__main__":
    main()
