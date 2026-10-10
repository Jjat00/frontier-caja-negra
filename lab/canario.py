"""M4: canario. Secuencia fija que toca cada regla conocida; se manda al original y se compara con el reemplazo local.

Como el reemplazo reproduce la versión mapeada, una divergencia indica que algo cambió: lo más probable es el
original (por ejemplo, el incidente de las 15:30 de la agenda), pero también puede ser el reemplazo o el entorno;
la causa se atribuye después, con experimentos. Queda en el log con seq canario-HHMM. Sale con 1 si hay divergencias.

Uso: uv run python -m lab.canario
"""

from __future__ import annotations

import os
import time
import warnings

warnings.filterwarnings("ignore", message=".*httpx.*")
os.environ.setdefault("PERFIL", "v_manana")

from lab.compare import comparar_paso, como_texto  # noqa: E402
from lab.control import firmar  # noqa: E402

B = firmar("TRANSFER;AC-0001;AC-0002;500000")
PASOS: list[tuple[str, dict]] = [
    ("PING;64", {}), ("PING;5X", {}), ("ALTA;Lucia;83", {}), (firmar("ALTA;Lucia"), {}), (firmar("ALTA;Mateo"), {}),
    ("ALTA;Lucia;082", {}), ("ALTA;Lucia;", {}), ("ALTA", {}), (firmar("CONSULTB;AC-0001"), {}),
    (firmar("HELP;AC-0001"), {}), (firmar("ALTA;a;b"), {}), (firmar("CONSULTA;AC-0001"), {}),
    (firmar("consulta;AC-0002"), {}), (firmar("CONSULTA;AC-0009"), {}),
    (firmar("DEPOSITO;AC-0001;250000"), {}), (firmar("DEPOSITO;AC-0001;007"), {}), (firmar("DEPOSITO;AC-0001;10000000000"), {}),
    (firmar("TRANSFER;AC-0001;AC-0002;40000"), {}), (firmar("TRANSFER;AC-0001;AC-0002;100000"), {}),
    (firmar("TRANSFER;AC-0001;AC-0002;100001"), {}), (firmar("TRANSFER;AC-0001;AC-0001;0"), {}),
    (firmar("TRANSFER;AC-0001;AC-0001;5"), {}), (firmar("TRANSFER;AC-0002;AC-0001;999999"), {}),
    (B, {}), (B, {}), (B, {}), (firmar("TRANSFER;AC-0001;AC-0002;10"), {}),
    (firmar("DEPOSITO;AC-0001;1"), {}), (firmar("TRANSFER;AC-0001;AC-0002;10"), {}),
    (firmar("ANULA;OP-0003"), {}), (firmar("ANULA;OP-0003"), {}), (firmar("ANULA;OP-0099"), {}),
    (firmar("CONSULTA;AC-0001"), {}), (firmar("CONSULTA;AC-0002"), {}), (firmar("HALT;AC-0001"), {}),
    ("", {"content": "[" * 21 + "0" + "]" * 21}), ("", {"content": "{"}), ("", {"content": '{"m":"' + "a" * 8200 + '"}'}),
    ("", {"ruta": "GET /noexiste"}), ("", {"ruta": "GET /health"}), ("PING;64", {"auth": "sin_token"}),
]


def main() -> None:
    from starlette.testclient import TestClient

    from app.main import CajaNegra
    from lab.probe import Lab

    lab = Lab()
    app = CajaNegra()
    tok = app.token = lab.token
    cli = TestClient(app)
    h = {"Authorization": f"Bearer {tok}"}
    seq = time.strftime("canario-%H%M")
    if lab.reset(seq, "canario M4: reset") != 200 or cli.post("/__reset", headers=h).status_code != 200:
        raise SystemExit("canario: un reset falló; no se compara")
    difs = 0
    for m, opt in PASOS:
        hip = f"canario M4: el original sigue igual que la versión mapeada ({m[:40] or opt})"
        if "ruta" in opt:
            metodo, ruta = opt["ruta"].split(" ", 1)
            fila = lab.send(None, hip, path=ruta, method=metodo)
            r = cli.request(metodo, ruta, headers=h)
        elif "content" in opt:
            fila = lab.send(None, hip, content=opt["content"], headers={"Content-Type": "application/json"})
            r = cli.post("/msg", content=opt["content"].encode(), headers={**h, "Content-Type": "application/json"})
        elif opt.get("auth") == "sin_token":
            fila = lab.send({"m": m}, hip, token=None, auth="sin_token")
            r = cli.post("/msg", json={"m": m})
        else:
            fila = lab.msg(m, hip)
            r = cli.post("/msg", json={"m": m}, headers=h)
        motivo = comparar_paso(fila["status"], como_texto(fila["response"]), r.status_code, r.text)
        if motivo:
            difs += 1
            print(f"DIVERGENCIA log {fila['id']} {m[:50] or opt}: {motivo}")
    print(f"canario {seq}: {len(PASOS) - difs}/{len(PASOS)} iguales" + ("" if difs else " (sin divergencias)"))
    raise SystemExit(1 if difs else 0)


if __name__ == "__main__":
    main()
