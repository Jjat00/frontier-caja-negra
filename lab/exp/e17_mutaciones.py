"""e17: diferencial mutacional de un solo mensaje (entrada e integridad).

La corrida oficial 1 dio 83/100. Los logs HTTP de Railway (solo método, ruta y status) muestran que
~35 de los 100 tests ocultos son un único mensaje que responde 400: la capa de entrada e integridad
pesa mucho más que en M2, que muta campos enteros. Aquí se muta carácter a carácter mensajes válidos
(y, aparte, el cuerpo JSON, las rutas y la cabecera de auth), se manda cada caso al original y al
reemplazo local en el mismo orden y se compara paso a paso.

Bloques de B casos por reset (el estado casi no importa para estos errores; si diverge, se ve en
cascada dentro del bloque). Cada caso queda en experimentos.jsonl con seq e17-<semilla>-<bloque>.

Uso: uv run python -m lab.exp.e17_mutaciones SEMILLA [N=300] [--bloque 10]
"""

from __future__ import annotations

import json
import os
import random
import sys
import warnings

warnings.filterwarnings("ignore", message=".*httpx.*")
os.environ.setdefault("PERFIL", "v_tarde")  # versión vigente (2) desde las 16:00

from lab.compare import comparar_paso, como_texto  # noqa: E402
from lab.control import firmar  # noqa: E402

PREP = [firmar("ALTA;Lucia"), firmar("ALTA;Mateo"), firmar("DEPOSITO;AC-0001;5000")]
BASES = [
    "PING", "ALTA;Lucia", "ALTA;Ana Maria", "CONSULTA;AC-0001", "CONSULTA;AC-0002", "DEPOSITO;AC-0001;500",
    "DEPOSITO;AC-0002;12345", "TRANSFER;AC-0001;AC-0002;100", "TRANSFER;AC-0002;AC-0001;7", "ANULA;OP-0001",
    "HALT;AC-0001",
]
CHARS = [" ", "  ", "\t", "\n", "\r", ";", ";;", "-", "_", ".", ",", "0", "9", "a", "z", "A", "Z", "é", "Ñ",
         "ß", "€", "😀", " ", "​", "\\", '"', "/", "|", ":", "=", "+", "#", "%", "１", "٣", "İ", "ﬁ",
         "\x00", "'", "*", "?"]


def mutar(r: random.Random, s: str) -> str:
    k = r.randint(0, 9)
    i = r.randint(0, len(s))
    if k <= 2:
        return s[:i] + r.choice(CHARS) + s[i:]
    if k == 3 and s:
        i = r.randrange(len(s))
        return s[:i] + s[i + 1:]
    if k == 4 and s:
        i = r.randrange(len(s))
        return s[:i] + r.choice(CHARS) + s[i + 1:]
    if k == 5 and s:
        i = r.randrange(len(s))
        return s[:i] + s[i].swapcase() + s[i + 1:]
    seg = s.split(";")
    if k == 6:
        j = r.randrange(len(seg))
        seg[j] = r.choice([" ", "\t", ""]) + seg[j] + r.choice([" ", "\t", "", "\n"])
    elif k == 7:
        j = r.randrange(len(seg))
        seg.insert(j, seg[j])
    elif k == 8 and len(seg) > 1:
        a, b = r.sample(range(len(seg)), 2)
        seg[a], seg[b] = seg[b], seg[a]
    else:
        j = r.randrange(len(seg))
        seg[j] = seg[j].lower() if r.random() < 0.5 else seg[j].upper()
    return ";".join(seg)


def caso_mensaje(r: random.Random) -> dict:
    base = r.choice(BASES)
    m = base
    for _ in range(r.choice([1, 1, 1, 2])):
        m = mutar(r, m)
    modo = r.random()
    if modo < 0.6:
        m = firmar(m)  # control correcto del texto mutado: llega a las etapas de después
        hip = f"mutación de «{base}» con control recalculado"
    elif modo < 0.8:
        m = firmar(base)
        m = mutar(r, m)
        hip = f"mutación de «{base}» ya firmado (puede tocar el control)"
    else:
        m = m + ";" + r.choice(["00", "0", "99", "98", "1", "x", ""])
        hip = f"mutación de «{base}» con control arbitrario"
    return {"request": {"m": m}, "hip": f"e17 entrada: {hip}"}


CUERPOS = [
    lambda m: json.dumps({"m": m, "extra": 1}),
    lambda m: json.dumps({"extra": 1, "m": m}),
    lambda m: '{"m":"PING;1","m":' + json.dumps(m) + "}",
    lambda m: '{"m":' + json.dumps(m) + ',"m":"PING;1"}',
    lambda m: "  " + json.dumps({"m": m}) + "\n",
    lambda m: "﻿" + json.dumps({"m": m}),
    lambda m: json.dumps({"m": m}, ensure_ascii=True).replace("A", "\\u0041", 1),
    lambda m: '{"m":' + json.dumps(m) + ",}",
    lambda m: "{'m':'" + m + "'}",
    lambda m: json.dumps({"m": [m]}),
    lambda m: json.dumps({"m": {"m": m}}),
    lambda m: json.dumps({"m": m + "\u0000"}),
    lambda m: '{"m":"\\ud800' + m + '"}',
    lambda m: json.dumps({"m": m, "n": float("nan")}) if False else '{"m":' + json.dumps(m) + ',"n":NaN}',
    lambda m: "",
    lambda m: "null",
    lambda m: "[]",
    lambda m: json.dumps(m),
    lambda m: json.dumps({"M": m, "m": m}),
    lambda m: json.dumps({"m ": m}),
    lambda m: json.dumps({"m": " " + m}),
    lambda m: json.dumps({"m": m + " "}),
]
CONTENT_TYPES = ["application/json", "text/plain", None, "application/x-www-form-urlencoded", "application/json; charset=latin-1"]


def caso_cuerpo(r: random.Random) -> dict:
    i = r.randrange(len(CUERPOS))
    m = firmar(r.choice(BASES))
    ct = r.choice(CONTENT_TYPES) if r.random() < 0.35 else "application/json"
    h = {"Content-Type": ct} if ct else {}
    return {"content": CUERPOS[i](m).encode("utf-8", "surrogatepass"), "headers": h,
            "hip": f"e17 cuerpo: variante {i} sobre «{m}» con Content-Type {ct}"}


RUTAS = [("POST", "/msg/"), ("POST", "/MSG"), ("POST", "//msg"), ("POST", "/msg?x=1"), ("GET", "/health/"),
         ("HEAD", "/health"), ("OPTIONS", "/msg"), ("PUT", "/msg"), ("DELETE", "/__reset"), ("GET", "/__reset"),
         ("POST", "/health"), ("PATCH", "/msg"), ("POST", "/msg#x"), ("GET", "/health?x=1"), ("POST", "/__reset/"),
         ("POST", "/api/msg"), ("GET", "/Health"), ("POST", "/msg%20")]
AUTHS = ["bearer {t}", "Bearer  {t}", "BEARER {t}", "Token {t}", "{t}", "Bearer",
         "Basic {t}", "Bearer {t}x"]


def caso_borde(r: random.Random) -> dict:
    if r.random() < 0.5:
        metodo, ruta = r.choice(RUTAS)
        body = {"m": firmar("ALTA;Lucia")} if metodo in ("POST", "PUT", "PATCH") else None
        return {"metodo": metodo, "ruta": ruta, "request": body, "hip": f"e17 ruta: {metodo} {ruta}"}
    a = r.choice(AUTHS)
    return {"auth": a, "request": {"m": firmar("ALTA;Lucia")}, "hip": f"e17 auth: Authorization «{a}»",
            "ruta": r.choice(["/msg", "/health", "/__reset"])}


def generar(semilla: int, n: int) -> list[dict]:
    r = random.Random(semilla)
    out = []
    for _ in range(n):
        x = r.random()
        out.append(caso_mensaje(r) if x < 0.75 else caso_cuerpo(r) if x < 0.92 else caso_borde(r))
    return out


def preparar(c: dict, token: str) -> tuple[str, str, dict, bytes | None]:
    """(método, ruta, headers, cuerpo en bytes) idénticos para original y reemplazo."""
    metodo = c.get("metodo", "POST")
    ruta = c.get("ruta", "/msg")
    if "auth" in c:
        metodo = "GET" if ruta == "/health" else "POST"
    h = dict(c.get("headers", {}))
    if "auth" in c:
        h["Authorization"] = c["auth"].format(t=token)
    else:
        h["Authorization"] = f"Bearer {token}"
    if "content" in c:
        cuerpo = c["content"]
    elif c.get("request") is not None and metodo != "GET":
        cuerpo = json.dumps(c["request"], ensure_ascii=False).encode()
        h.setdefault("Content-Type", "application/json")
    else:
        cuerpo = None
    return metodo, ruta, h, cuerpo


def main() -> None:
    import argparse

    from starlette.testclient import TestClient

    from app.main import CajaNegra
    from lab.probe import Lab, TOKEN

    ap = argparse.ArgumentParser()
    ap.add_argument("semilla", type=int)
    ap.add_argument("n", type=int, nargs="?", default=300)
    ap.add_argument("--bloque", type=int, default=10)
    a = ap.parse_args()
    casos = generar(a.semilla, a.n)
    lab = Lab()
    cli = TestClient(CajaNegra())
    auth = {"Authorization": f"Bearer {TOKEN}"}
    difs = 0
    for b in range(0, len(casos), a.bloque):
        seq = f"e17-{a.semilla}-{b // a.bloque}"
        if lab.reset(seq, "reset del diferencial e17") != 200:
            raise SystemExit("reset del original falló")
        cli.post("/__reset", headers=auth)
        pasos = [{"request": {"m": m}, "hip": "e17 preparación: dos cuentas y un depósito"} for m in PREP] + casos[b:b + a.bloque]
        for c in pasos:
            metodo, ruta, h, cuerpo = preparar(c, TOKEN)
            if any(v != v.strip() for v in h.values()):
                continue  # httpx no manda valores de cabecera con espacios en los bordes
            hdr = {k: v for k, v in h.items() if k != "Authorization"}
            if "auth" in c:
                fila = lab.send(None, c["hip"], path=ruta, method=metodo, content=cuerpo, auth=f"variante: {c['auth']}",
                                token=None, headers=h)
            elif cuerpo is None:
                fila = lab.send(None, c["hip"], path=ruta, method=metodo, headers=hdr or None)
            elif "content" in c:
                fila = lab.send(None, c["hip"], path=ruta, method=metodo, content=cuerpo, headers=hdr)
            else:
                fila = lab.send(c["request"], c["hip"], path=ruta, method=metodo)
            r = cli.request(metodo, ruta, headers=h, content=cuerpo)
            motivo = comparar_paso(fila["status"], como_texto(fila["response"]), r.status_code, r.text)
            if motivo:
                difs += 1
                print(f"DIF log {fila['id']} [{seq}] {metodo} {ruta} {cuerpo!r}: {motivo}")
    print(f"\ne17 semilla {a.semilla}: {len(casos)} casos, {difs} pasos distintos")
    sys.exit(1 if difs else 0)


if __name__ == "__main__":
    main()
