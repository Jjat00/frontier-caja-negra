"""e11: comando oculto HALT (revelado por la sugerencia de HELP, log 1125) y más nombres por el oráculo de sugerencias."""
from lab.control import firmar
from lab.probe import Lab

lab = Lab()
lab.reset("e11-oraculo")
for c in ["SET", "GET", "DEL", "ADD", "SUM", "LOCK", "UNLOCK", "FREEZE", "CLOSE", "OPEN", "DUMP", "DEBUG", "ADMIN",
          "ROOT", "SYNC", "TEST", "NOOP", "QUIT", "EXIT", "STOP", "KILL", "BOOT", "WAIT", "SLEEP", "HALTS", "ALL",
          "LIST", "SHOW", "VER", "CLEAR", "FLUSH", "PURGE", "UNDO", "REDO", "SAVE", "LOAD", "STAT", "PAY", "SEND"]:
    lab.msg(firmar(f"{c};AC-0001"), f"oráculo de sugerencias: ¿hay un comando a distancia ≤2 de {c}?")
lab.reset("e11-halt")
pasos = [("ALTA;Ana", "preparar AC-0001"), ("DEPOSITO;AC-0001;5000", "preparar OP-0001"),
         ("HALT", "HALT sin argumentos"), ("HALT;AC-0001", "HALT con 1 argumento"), ("HALT;AC-0001;5", "HALT con 2"),
         ("HALT;AC-0001;5;5", "HALT con 3")]
for m, h in pasos:
    lab.msg(firmar(m), h)
lab.msg("HALT;0", "HALT con control incorrecto: ¿valida el control como PING o no?")
lab.msg("HALT;5X", "HALT con control mal formado")
lab.msg(firmar("CONSULTA;AC-0001"), "¿el estado sigue igual tras HALT?")
lab.msg(firmar("PING"), "PING tras HALT")
