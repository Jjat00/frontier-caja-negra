"""M2: fuzzer diferencial. Secuencias inéditas con la mezcla del set oficial contra original y reemplazo.

Genera `n` tests (40 % de 1 paso, 45 % de 2 a 5 y 15 % de 6 a 12) con una semilla guardada.
Cada test empieza con reset. Corre primero contra el original (queda en experimentos.jsonl con
seq fz<semilla>-<i>) y después contra el reemplazo local (TestClient) o desplegado (--url).
Reporta la tasa de tests completos que coinciden y, para cada fallo, el primer paso que difiere.

Uso: uv run python -m lab.fuzz SEMILLA [N=100] [--solo-reemplazo] [--url URL]
  --solo-reemplazo vuelve a correr una semilla ya registrada sin gastar requests del original;
  valida que el log tenga exactamente los N tests de esa semilla, completos y en una sola corrida.
Sale con código 1 si algún test difiere o si la evidencia está incompleta.
"""

from __future__ import annotations

import json
import os
import random
import sys
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore", message=".*httpx.*")
os.environ.setdefault("PERFIL", "v_tarde")  # versión vigente (2) desde las 16:00

from lab.compare import comparar_paso, como_texto  # noqa: E402
from lab.control import control, firmar  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
COMANDOS = ["PING", "ALTA", "CONSULTA", "DEPOSITO", "TRANSFER", "ANULA"]
CASI = ["CONSULTB", "DEPOSIT", "TRANSFR", "ANULAR", "ALT", "PIN", "SALDOS", "FOO", "HELP", "RETIRO", "consulta",
        "Deposito", "HALT"]
MONTOS_OK = [1, 5, 50, 700, 999, 1500, 25000, 40000, 99999, 100000, 250000, 1000000, 9999999999]
# Desde la semilla 3 (versión 2) se suman los bordes del límite nuevo; las semillas 1 y 2 conservan su generador
# para que --solo-reemplazo reproduzca exactamente lo registrado.
MONTOS_OK_V2 = sorted(MONTOS_OK + [49999, 50000, 50001])
MONTOS_FEOS = ["0", "-5", "5.5", "007", "abc", "100001", "120000", "10000000000", "1e3", " 5", "+5"]
NOMBRES = ["Lucia", "Mateo", "Ana Maria", "José", "123", "x", "a-b", "Ñandú", " "]


class Gen:
    """Generador de pasos que sigue un modelo aproximado del estado para que haya cuentas y operaciones reales."""

    def __init__(self, rnd: random.Random, montos: list[int] = MONTOS_OK):
        self.r = rnd
        self.montos = montos
        self.cuentas = 0
        self.ops = 0

    def cuenta(self) -> str:
        r = self.r.random()
        if self.cuentas and r < 0.8:
            return f"AC-{self.r.randint(1, self.cuentas):04d}"
        return self.r.choice(["AC-0009", "AC-0000", "ac-0001", "AC-1", "XYZ", f"AC-{self.cuentas + 1:04d}"])

    def op(self) -> str:
        if self.ops and self.r.random() < 0.8:
            return f"OP-{self.r.randint(1, self.ops):04d}"
        return self.r.choice(["OP-0009", "op-0001", "OP-1", "AC-0001"])

    def monto(self, feo: float) -> str:
        if self.r.random() < feo:
            return self.r.choice(MONTOS_FEOS)
        return str(self.r.choice(self.montos))

    def valido(self) -> str:
        cmd = self.r.choices(COMANDOS, weights=[1, 3, 3, 3, 4, 2])[0]
        if cmd == "PING":
            return f"PING;{self.r.randint(0, 99)}", "PING con control arbitrario responde pong (no valida el control)"
        if cmd == "ALTA":
            self.cuentas += 1
            return firmar(f"ALTA;{self.r.choice(NOMBRES)}"), "ALTA válida crea la siguiente cuenta AC- secuencial"
        if cmd == "CONSULTA":
            return firmar(f"CONSULTA;{self.cuenta()}"), "CONSULTA devuelve el saldo acumulado o E401 si la cuenta no existe"
        if cmd == "DEPOSITO":
            self.ops += 1
            return (firmar(f"DEPOSITO;{self.cuenta()};{self.monto(0.1)}"),
                    "DEPOSITO suma al saldo y numera OP-, o E303/E401 según monto y cuenta; desbloquea la cuenta")
        if cmd == "TRANSFER":
            self.ops += 1
            a, b = self.cuenta(), self.cuenta()
            return (firmar(f"TRANSFER;{a};{b};{self.monto(0.15)}"),
                    "TRANSFER mueve saldo o rechaza en orden E303, E304, E401, E510, E506, E507")
        return firmar(f"ANULA;{self.op()}"), "ANULA revierte la operación una vez (ok:false si se repite) o E402"

    def falla_entrada(self) -> str:
        base, _ = self.valido()
        cuerpo, c = base.rsplit(";", 1)
        k = self.r.randint(0, 9)
        if k == 0:
            return f"{cuerpo};{(int(control(cuerpo)) % 97) + 1}", "control con valor incorrecto: E202 (salvo PING)"
        if k == 1:
            return (f"{cuerpo};{self.r.choice(['5X', '082', ' 8', '-1', '8.0', 'ab'])}",
                    "control mal formado: E201 antes que comando y aridad (salvo PING)")
        if k == 2:
            return cuerpo.split(";")[0], "mensaje sin ';': E103 falta control"
        if k == 3:
            return firmar(f"{self.r.choice(CASI)};{self.cuenta()}"), "comando desconocido o cercano: E301 con sugerencia si Levenshtein <= 2 (HALT es aridad 1)"
        if k == 4:
            return firmar(cuerpo + ";extra"), "un argumento de más: E302 tras validar el control"
        if k == 5:
            return firmar(";".join(cuerpo.split(";")[:-1]) or "ALTA"), "un argumento de menos: E302 (o E103 si queda un solo campo)"
        if k == 6:
            return cuerpo + ";", "control vacío tras ';': E104 segmento vacío"
        if k == 7:
            return (f"{cuerpo};0{c}" if len(c) == 1 else f"{cuerpo};{c}",
                    "control con cero a la izquierda: E202 (comparación de texto)" if len(c) == 1 else "control correcto de dos dígitos")
        if k == 8:
            return (firmar(cuerpo.split(";", 1)[0].lower() + (";" + cuerpo.split(";", 1)[1] if ";" in cuerpo else "")),
                    "comando en minúsculas se acepta igual que en mayúsculas")
        return firmar(f"HALT;{self.cuenta()}"), "HALT con un argumento: 409 E520 sin cambiar el estado (nunca se confirma)"

    def negocio(self) -> str:
        k = self.r.randint(0, 4)
        if k == 0:
            return (firmar(f"TRANSFER;{self.cuenta()};{self.cuenta()};{self.r.choice([100001, 500000, 120000])}"),
                    "TRANSFER sobre el límite: E506 y cuenta para el bloqueo tras 3 rechazos")
        if k == 1:
            a = self.cuenta()
            return firmar(f"TRANSFER;{a};{a};{self.monto(0.2)}"), "TRANSFER a la misma cuenta: E304 (E303 si el monto es inválido)"
        if k == 2:
            return firmar(f"ANULA;{self.op()}"), "ANULA de operación existente o no: revierte saldo, ok:false o E402"
        if k == 3:
            return (firmar(f"CONSULTA;{self.r.choice(['AC-0009', 'AC-0042', 'OP-0001'])}"),
                    "CONSULTA de cuenta inexistente o id de otro tipo: E401")
        return (firmar(f"TRANSFER;{self.cuenta()};{self.cuenta()};{self.r.choice([99999, 100000, 250000])}"),
                "TRANSFER en el borde del límite (100000 pasa) o con saldo insuficiente: E507")

    def paso(self) -> dict:
        r = self.r.random()
        if r < 0.03:
            ruta = self.r.choice(["GET /health", "GET /noexiste", "GET /msg"])
            return {"ruta": ruta, "request": None, "hip": f"{ruta}: health 200 con token, cualquier otra ruta o método 404 E404"}
        if r < 0.5:
            m, hip = self.valido()
        elif r < 0.75:
            m, hip = self.falla_entrada()
        else:
            m, hip = self.negocio()
        return {"request": {"m": m}, "hip": hip}


def generar(semilla: int, n: int) -> list[list[dict]]:
    rnd = random.Random(semilla)
    tests = []
    for i in range(n):
        f = i / n
        largo = 1 if f < 0.4 else rnd.randint(2, 5) if f < 0.85 else rnd.randint(6, 12)
        g = Gen(rnd, MONTOS_OK if semilla < 3 else MONTOS_OK_V2)
        pasos = []
        # en secuencias largas se arranca con cuentas y saldo para que el negocio tenga sustancia
        if largo >= 3 and rnd.random() < 0.7:
            prep = "preparación: "
            pasos.append({"request": {"m": firmar(f"ALTA;{rnd.choice(NOMBRES)}")}, "hip": prep + "ALTA crea AC-0001"}); g.cuentas += 1
            pasos.append({"request": {"m": firmar(f"ALTA;{rnd.choice(NOMBRES)}")}, "hip": prep + "ALTA crea AC-0002"}); g.cuentas += 1
            pasos.append({"request": {"m": firmar(f"DEPOSITO;AC-0001;{rnd.choice([250000, 150000, 90000])}")},
                          "hip": prep + "DEPOSITO da saldo a AC-0001 (OP-0001)"}); g.ops += 1
        while len(pasos) < largo:
            pasos.append(g.paso())
        tests.append(pasos[:largo])
    return tests


def hipotesis(semilla: int, i: int, j: int, paso: dict) -> str:
    return f"fuzzer M2 (semilla {semilla}, test {i}, paso {j}): {paso['hip']}"


def correr_original(semilla: int, tests: list[list[dict]]) -> list[list[dict]]:
    from lab.probe import Lab

    if any(s.startswith(f"fz{semilla}-") for s in _seqs_del_log()):
        raise SystemExit(f"la semilla {semilla} ya está en el log: usa otra o --solo-reemplazo")
    lab = Lab()
    filas = []
    for i, pasos in enumerate(tests):
        if lab.reset(f"fz{semilla}-{i}", "reset del fuzzer M2: cada test empieza en el estado inicial") != 200:
            raise SystemExit(f"fz{semilla}-{i}: el reset del original falló; se aborta antes del primer paso")
        fs = []
        for j, p in enumerate(pasos):
            h = hipotesis(semilla, i, j, p)
            if p.get("ruta"):
                metodo, ruta = p["ruta"].split(" ", 1)
                fs.append(lab.send(None, h, path=ruta, method=metodo))
            else:
                fs.append(lab.send(p["request"], h))
        filas.append(fs)
    return filas


def _seqs_del_log() -> list[str]:
    with open(ROOT / "experimentos.jsonl", encoding="utf-8") as f:
        return [json.loads(l)["seq"] for l in f if l.strip()]


def cargar_original(semilla: int, tests: list[list[dict]]) -> list[list[dict]]:
    """Filas del original para exactamente esos tests; falla si falta uno, si está incompleto o si hay dos corridas."""
    por_seq: dict[str, list[dict]] = {}
    resets: Counter = Counter()
    with open(ROOT / "experimentos.jsonl", encoding="utf-8") as f:
        for linea in f:
            fila = json.loads(linea)
            if not fila["seq"].startswith(f"fz{semilla}-") or "infra" in fila:
                continue
            if fila.get("ruta") == "POST /__reset":
                if fila["status"] != 200:
                    raise SystemExit(f"{fila['seq']}: el reset registrado (log {fila['id']}) no fue 200")
                resets[fila["seq"]] += 1
            else:
                por_seq.setdefault(fila["seq"], []).append(fila)
    if not por_seq:
        raise SystemExit(f"la semilla {semilla} no está en el log")
    salida = []
    for i, pasos in enumerate(tests):
        seq = f"fz{semilla}-{i}"
        filas = por_seq.get(seq, [])
        if resets[seq] != 1:
            raise SystemExit(f"{seq}: {resets[seq]} resets en el log (se esperaba 1 corrida)")
        esperados = [(p.get("ruta") or "POST /msg", p.get("request")) for p in pasos]
        if [(f.get("ruta") or "POST /msg", f.get("request")) for f in filas] != esperados:
            raise SystemExit(f"{seq}: el log no coincide con la generación de la semilla ({len(filas)} de {len(pasos)} pasos)")
        salida.append(filas)
    sobran = set(por_seq) - {f"fz{semilla}-{i}" for i in range(len(tests))}
    if sobran:
        raise SystemExit(f"el log tiene tests de la semilla {semilla} fuera de N={len(tests)}: {sorted(sobran)[:3]}…")
    return salida


def cliente_reemplazo(url: str | None):
    if url:
        import httpx

        return httpx.Client(base_url=url, timeout=10)
    from starlette.testclient import TestClient

    from app.main import CajaNegra

    return TestClient(CajaNegra())


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="M2: fuzzer diferencial")
    ap.add_argument("semilla", type=int)
    ap.add_argument("n", type=int, nargs="?", default=100)
    ap.add_argument("--solo-reemplazo", action="store_true")
    ap.add_argument("--url")
    a = ap.parse_args()
    if a.n <= 0:
        ap.error("N debe ser positivo")
    tests = generar(a.semilla, a.n)
    originales = cargar_original(a.semilla, tests) if a.solo_reemplazo else correr_original(a.semilla, tests)
    token = os.environ.get("TOKEN") or __import__("dotenv").dotenv_values(ROOT / ".env").get("TOKEN")
    h = {"Authorization": f"Bearer {token}"}
    if a.solo_reemplazo and not a.url:
        # una semilla registrada con la versión 1 (antes de la fila 6040) se repite con v_manana
        os.environ["PERFIL"] = "v_manana" if originales[0][0]["id"] < 6040 else "v_tarde"
    cli = cliente_reemplazo(a.url)
    ok = 0
    fallos_cmd: Counter = Counter()
    for i, filas in enumerate(originales):
        if cli.post("/__reset", headers=h).status_code != 200:
            raise SystemExit(f"test {i}: el reset del reemplazo falló")
        primer = None
        for fila in filas:
            metodo, ruta = fila.get("ruta", "POST /msg").split(" ", 1)
            body = fila.get("request")
            r = cli.request(metodo, ruta, headers=h, content=json.dumps(body, ensure_ascii=False).encode() if body else None)
            motivo = comparar_paso(fila["status"], como_texto(fila["response"]), r.status_code, r.text)
            if motivo and primer is None:
                primer = (fila, motivo)
                cmd = body.get("m", "").split(";")[0].upper() if isinstance(body, dict) else ruta
                fallos_cmd[cmd] += 1
        if primer is None:
            ok += 1
        else:
            fila, motivo = primer
            print(f"FALLA test {i} (log {fila['id']}) {fila.get('request')}: {motivo}")
    print(f"\nM2 semilla {a.semilla}: {ok}/{len(originales)} tests completos iguales ({100 * ok / len(originales):.1f} %)")
    if fallos_cmd:
        print("primer fallo por comando:", dict(fallos_cmd))
    sys.exit(0 if ok == len(originales) else 1)


if __name__ == "__main__":
    main()
