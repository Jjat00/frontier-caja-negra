"""e23: el original no acepta el token del equipo (ftr_). Fila 4467. Uso: uv run python -m lab.exp.e23_token_equipo
"""

import json
from dotenv import dotenv_values
from lab.probe import Lab
tt = dotenv_values(".env")["TEAM_TOKEN"]
lab = Lab()
lab.seq = "e23-token-equipo"
f = lab.send(None, "e23: ¿el original acepta el token del equipo (ftr_) en GET /health?", path="/health", method="GET",
             auth="token_equipo", token=tt)
print(f["id"], f["status"], json.dumps(f["response"], ensure_ascii=False))
