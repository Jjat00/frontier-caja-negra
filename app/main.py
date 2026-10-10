"""App ASGI del reemplazo: una sola ruta comodín para todos los métodos (diseño D2).

No se usa el router de FastAPI/Starlette: generaría sus propios 404/405/422 y redirecciones
de barra final, que el original no tiene. Orden: router primero, luego auth (log 141, 142).

Atomicidad (diseño 2.6): el cuerpo se lee completo y después validación, transición y respuesta
corren sin ningún await. Con un solo worker, dos requests nunca intercalan cambios de estado.
"""

from __future__ import annotations

import json
import os
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
        await respuesta(scope, receive, send)

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
