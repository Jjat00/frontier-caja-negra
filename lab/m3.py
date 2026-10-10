"""M3: conteo de cobertura de la especificación por sección y confianza.

La matriz M3 del diseño (comando × error × estado) quedó materializada como las filas de docs/especificacion.md:
cada fila es un comportamiento con su evidencia y su confianza. Este script las cuenta y reporta, por sección,
cuántas son confirmadas, probables y supuestos, y cuántas citan filas del log. Un supuesto nunca cuenta como
evidencia (diseño, sección 4). No llama al original ni al reemplazo.

Uso: uv run python -m lab.m3
"""

from __future__ import annotations

import re
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIANZAS = ("confirmado", "probable", "supuesto")
FILA = re.compile(r"^\| ([A-Z]+(?:-[A-Z]+)?-\d+) \|(.*)\| ([^|]*) \| ([a-z]+) \|\s*$")


def contar(texto: str) -> tuple[OrderedDict[str, Counter], list[str]]:
    secciones: OrderedDict[str, Counter] = OrderedDict()
    problemas = []
    seccion = "sin sección"
    for n, linea in enumerate(texto.splitlines(), 1):
        if linea.startswith("## "):
            seccion = linea[3:].strip()
            continue
        m = FILA.match(linea)
        if not m:
            continue
        ident, _, evidencia, confianza = m.groups()
        if confianza not in CONFIANZAS:
            problemas.append(f"línea {n} ({ident}): confianza desconocida «{confianza}»")
            continue
        c = secciones.setdefault(seccion, Counter())
        c[confianza] += 1
        if re.search(r"\d", evidencia):
            c["con_evidencia"] += 1
        elif confianza != "supuesto":
            problemas.append(f"línea {n} ({ident}): {confianza} sin filas del log citadas")
    return secciones, problemas


def main() -> None:
    secciones, problemas = contar((ROOT / "docs" / "especificacion.md").read_text(encoding="utf-8"))
    total: Counter = Counter()
    print(f"{'Sección':34} {'conf.':>6} {'prob.':>6} {'sup.':>6} {'total':>6}")
    for nombre, c in secciones.items():
        n = sum(c[k] for k in CONFIANZAS)
        print(f"{nombre[:34]:34} {c['confirmado']:6} {c['probable']:6} {c['supuesto']:6} {n:6}")
        total.update(c)
    n = sum(total[k] for k in CONFIANZAS)
    print(f"{'TOTAL':34} {total['confirmado']:6} {total['probable']:6} {total['supuesto']:6} {n:6}")
    print(f"\nconfirmadas: {100 * total['confirmado'] / n:.1f} % · con evidencia del log (confirmado o probable): "
          f"{100 * (total['confirmado'] + total['probable']) / n:.1f} % · supuestos: {total['supuesto']}")
    for p in problemas:
        print("AVISO", p)


if __name__ == "__main__":
    main()
