"""e13: tamaño máximo del cuerpo antes de 413 E101 (log 1662: 20001 bytes → E101; log 1184: ~5013 bytes → normal)."""
from lab.probe import Lab

lab = Lab()
lab.reset("e13-tamano")
def cuerpo(n):  # JSON válido de exactamente n bytes con PING
    base = '{"m":"PING;64","x":""}'
    return base[:-2] + "a" * (n - len(base)) + '"}'
lo, hi = 5013, 20001
while hi - lo > 1:
    mid = (lo + hi) // 2
    c = cuerpo(mid); assert len(c.encode()) == mid
    r = lab.send(None, f"tamaño del cuerpo: ¿{mid} bytes da E101? (pasa {lo}, E101 {hi})", content=c,
                 headers={"Content-Type": "application/json"})
    if r["status"] == 413: hi = mid
    else: lo = mid
lab.conclude(f"límite del cuerpo: {lo} bytes pasa, {hi} bytes da 413 E101")
print(lo, hi)
r = lab.send(None, f"confirmación: {hi} bytes otra vez", content=cuerpo(hi), headers={"Content-Type": "application/json"})
r = lab.send(None, f"cuerpo de {hi} bytes que NO es JSON: ¿E101 o E100 primero?", content="x" * hi, headers={"Content-Type": "application/json"})
r = lab.send(None, f"cuerpo de {hi} bytes sin token: ¿401 o 413?", content=cuerpo(hi), token=None, auth="sin_token", headers={"Content-Type": "application/json"})
r = lab.send(None, f"cuerpo de {hi} bytes a ruta inexistente: ¿404 o 413?", content=cuerpo(hi), path="/noexiste", headers={"Content-Type": "application/json"})
