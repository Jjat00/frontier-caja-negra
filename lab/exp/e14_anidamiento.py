"""e14: profundidad máxima de JSON antes de E100 (log 1663: 1001 niveles → E100)."""
from lab.probe import Lab

lab = Lab()
lab.reset("e14-anidamiento")
def cuerpo(d):  # array anidado d niveles como cuerpo: si se parsea, no es objeto → E102
    return "[" * d + "0" + "]" * d
lo, hi = 1, 1001
while hi - lo > 1:
    mid = (lo + hi) // 2
    r = lab.send(None, f"anidamiento: ¿{mid} niveles de array dan E100? (E102 en {lo}, E100 en {hi})", content=cuerpo(mid),
                 headers={"Content-Type": "application/json"})
    if r["response"].get("error") == "E100": hi = mid
    else: lo = mid
lab.conclude(f"anidamiento: {lo} niveles se parsean (E102), {hi} niveles dan E100")
print(lo, hi)
lab.send(None, f"objeto de {lo} niveles", content='{"a":' * (lo - 1) + '{"m":"PING;64"}' + "}" * (lo - 1), headers={"Content-Type": "application/json"})
lab.send(None, f"objeto de {hi} niveles", content='{"a":' * (hi - 1) + '{"m":"PING;64"}' + "}" * (hi - 1), headers={"Content-Type": "application/json"})
