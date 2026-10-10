"""e20: sugerencia de E301 con caracteres no ASCII y según el número de argumentos. Filas 3502-3540.
Contrasta cuatro modelos de mayúsculas (Python upper, por carácter, bytes UTF-8, UTF-16); el del original es
mayúsculas solo ASCII. Las filas 3502-3503 son una corrida abortada por un error del script (modelo UTF-16).
Uso: uv run python -m lab.exp.e20_sugerencia_unicode
"""

from app.tuberia import _levenshtein
from app.perfiles import V_MANANA
from lab.control import firmar
from lab.probe import Lab
import json, sys
C = list(V_MANANA.comandos)
def sug(n, f):
    best = min(((_lev(f(n), f(c)), c) for c in C), key=lambda x: x[0])
    return best[1] if best[0] <= 2 else None
def _lev(a, b): return _levenshtein(a, b)
modelos = {
 "chars_upper": lambda s: s.upper(),
 "chars_upper_porchar": lambda s: "".join(ch.upper() if len(ch.upper())==1 else ch for ch in s),
 "bytes_upper_ascii": lambda s: "".join(chr(b) for b in s.encode()).upper() if False else "".join(chr(b) for b in "".join(ch.upper() if ch.isascii() else ch for ch in s).encode()),
 "utf16_upper": lambda s: (lambda b: "".join(chr(int.from_bytes(b[i:i+2],'little')) for i in range(0,len(b),2)))(s.upper().encode('utf-16-le')),
}
probes = ["AßNG","PÑÑG","PIÑG","ÁLTA","AÉÉA","HALTÉ","PIN😀","P😀NG","ßING","NOTAß","ﬁNG","PıNG","PİNG","ANULAÉ","ANUÉÉ"]
if sys.argv[1:] == ["local"]:
    for p in probes: print(p, {k: sug(p, f) for k, f in modelos.items()})
    sys.exit(0)  # «local» no manda nada al original: ni la parte 1 ni la 2
else:
    lab = Lab(); lab.reset("e20-sugerencia-unicode-b", "reset: distancia de la sugerencia con caracteres no ASCII")
    for p in probes:
        f = lab.msg(firmar(p+";AC-0001"), f"e20: sugerencia para «{p}»: ¿Levenshtein por bytes UTF-8, por caracteres o por UTF-16?")
        print(f["id"], p, f["response"].get("sugerencia"), {k: sug(p, g) for k, g in modelos.items()})

# Parte 2 (seq e20-sugerencia-aridad)
lab = Lab(); lab.reset("e20-sugerencia-aridad", "reset: ¿la sugerencia depende de la aridad o del estado?")
for m in ["AßNG", "AßNG;AC-0001", "AßNG", "PINX", "PINX;a", "PINX;a;b", "ALTX", "ALTX;a", "ALTX;a;b", "NOTX", "NOTX;a", "HALX", "HALX;a", "HALX;a;b", "CONSULTX", "CONSULTX;a;b", "PÑÑG", "PÑÑG;a", "ßING", "ßING;a"]:
    f = lab.msg(firmar(m), f"e20: sugerencia para «{m}» según el número de argumentos")
    print(f["id"], repr(firmar(m)), f["status"], f["response"].get("error"), f["response"].get("sugerencia"))
