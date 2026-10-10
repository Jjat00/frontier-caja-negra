"""e31: ¿HALT;1 es la confirmación de E520? Copia exacta del último test del set oculto (trazas de la corrida 3):
ALTA;Ana;50, HALT;1;19, PING;XX, __reset, PING;XX, CONSULTA;AC-0001;14, ALTA;Beto;11. El e25 nunca probó el argumento 1.
Uso: uv run python -m lab.exp.e31_halt_1
"""

from lab.probe import Lab

HIP = "e31: copia del test del set oculto con reset en medio; ¿HALT;1 detiene el servicio hasta el reset?"


def main() -> None:
    lab = Lab()
    for paso in ["RESET", "ALTA;Ana;50", "HALT;1;19", "PING;XX", "RESET", "PING;XX", "CONSULTA;AC-0001;14", "ALTA;Beto;11"]:
        if paso == "RESET":
            st = lab.reset("e31-halt-1", f"reset de {HIP}")
            print("RESET", st)
        else:
            f = lab.msg(paso, HIP)
            print(f["id"], paso, f["status"], f["response"])


if __name__ == "__main__":
    main()
