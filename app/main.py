"""App ASGI del reemplazo: una sola ruta comodín para todos los métodos (diseño D2).

No se usa el router de FastAPI/Starlette: generaría sus propios 404/405/422 y redirecciones
de barra final, que el original no tiene. Orden: router primero, luego auth (log 141, 142).

Atomicidad (diseño 2.6): el cuerpo se lee completo y después validación, transición y respuesta
corren sin ningún await. Con un solo worker, dos requests nunca intercalan cambios de estado.
"""

from __future__ import annotations

import json
import os
import queue
import re
import sys
import threading
from urllib.parse import quote
from pathlib import Path

from dotenv import load_dotenv
from starlette.requests import Request
from starlette.responses import Response

from app import catalogo as cat
from app import perfiles, tuberia
from app.comandos import Estado

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Rutas conocidas: (método, ruta). Cualquier otra combinación da E404 con o sin token
# (log 7, 8, 9 «GET /msg», 141, 142, 144-148 «/openapi.json», «/docs», «/»).
RUTAS = {("GET", "/health"): "health", ("POST", "/__reset"): "reset", ("POST", "/msg"): "msg"}


TRAZA_MAX_CUERPO = 9000  # bytes del cuerpo que se registran (el servicio rechaza más de 8192)
_TRAZAS: queue.Queue[str] = queue.Queue(maxsize=10000)
# «Bearer» seguido de separadores reales, escapados en JSON (\t, \n, \r) o codificados en URL (%XX, +), y el valor.
_BEARER = re.compile(r"(?i)bearer(?:\s|\\[tnr]|%[0-9A-Fa-f]{2}|\+)+[A-Za-z0-9._~+/=%-]+")


def _redactar(texto: str, token: str) -> str:
    """Redacta un campo de texto antes de serializar la línea (los números no se tocan)."""
    if token:
        for forma in {token, json.dumps(token)[1:-1], quote(token, safe="")}:
            texto = texto.replace(forma, "<TOKEN>")
    return _BEARER.sub("Bearer <REDACTADO>", texto)


def _escritor() -> None:
    while True:
        linea = _TRAZAS.get()
        try:
            sys.stdout.write(linea + "\n")
            sys.stdout.flush()
        except Exception:
            pass


threading.Thread(target=_escritor, name="traza", daemon=True).start()


def serializar(status: int, cuerpo: dict, headers: dict | None = None) -> Response:
    # ensure_ascii=False («límite», «inválido») y separadores compactos.
    datos = json.dumps(cuerpo, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return Response(datos, status_code=status, media_type="application/json", headers=headers)


class CajaNegra:
    def __init__(self) -> None:
        self.perfil = perfiles.activo()
        self.token = os.environ.get("TOKEN", "")
        self.estado = Estado()
        # X-Req cuenta los POST /msg autenticados, incluidos los errores de validación (log 10-12, 128-133) y los
        # 404 de negocio E401/E402 (log 181, 835). No se reinicia con __reset (log 134-135, 143-150) y no sale en
        # E001 de auth (log 1, 4, 5) ni en E404 de ruta (log 7, 131). No se evalúa.
        self.x_req = 0

    def autorizado(self, request: Request) -> bool:
        return bool(self.token) and request.headers.get("authorization") == f"Bearer {self.token}"

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            while (await receive())["type"] != "lifespan.shutdown":
                await send({"type": "lifespan.startup.complete"})
            await send({"type": "lifespan.shutdown.complete"})
            return
        if scope["type"] != "http":
            return
        request = Request(scope, receive)
        cuerpo = await request.body()  # único await antes de la sección atómica
        respuesta = self.despachar(request, cuerpo)
        self.trazar(request, cuerpo, respuesta)
        await respuesta(scope, receive, send)

    def trazar(self, request: Request, cuerpo: bytes, respuesta: Response) -> None:
        """Una línea JSON por request en stdout (logs de Railway) para estudiar el set oculto después de una corrida.
        El token configurado y cualquier «Bearer <valor>» se redactan en todos los campos; del header Authorization solo
        se registra si faltaba, si era el token esperado o si era otro. La escritura va a una cola acotada que vacía un
        hilo aparte: si se llena, la línea se descarta y el request no espera nunca a stdout."""
        try:
            auth = request.headers.get("authorization")
            r = lambda texto: _redactar(texto, self.token)  # noqa: E731
            linea = json.dumps({
                "traza": 1,
                "metodo": r(request.method),
                "ruta": r(request.scope.get("raw_path", b"").decode("latin-1") or request.scope["path"]),
                "query": r(request.scope.get("query_string", b"").decode("latin-1")),
                "auth": "ninguno" if auth is None else ("propio" if self.autorizado(request) else "otro"),
                "cuerpo": r(cuerpo[:TRAZA_MAX_CUERPO].decode("utf-8", "backslashreplace")),
                "bytes": len(cuerpo),
                "status": respuesta.status_code,
                "respuesta": r(respuesta.body.decode("utf-8", "replace")),
            }, ensure_ascii=False)
            _TRAZAS.put_nowait(linea)
        except Exception:
            pass  # cola llena o error de la traza: nunca cambia la respuesta

    def despachar(self, request: Request, cuerpo: bytes) -> Response:
        ruta = RUTAS.get((request.method, request.url.path))
        if ruta is None:
            return serializar(*cat.error("E404"))
        if not self.autorizado(request):
            return serializar(*cat.error("E001"))  # log 1, 2, 4, 5, 6
        if ruta == "health":
            return serializar(*cat.ok())  # log 3
        if ruta == "reset":
            self.estado = Estado()  # log 134, 139
            return serializar(*cat.ok())
        self.x_req += 1
        status, body, self.estado = tuberia.procesar(cuerpo, self.perfil, self.estado)
        return serializar(status, body, {"X-Req": str(self.x_req)})


app = CajaNegra()
