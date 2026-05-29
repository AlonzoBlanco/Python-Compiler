# =============================================================================
# codegen.py  —  Etapa 6: Generación de Pseudoensamblador
# vm.py integrado en el mismo archivo por comodidad — Etapa 7: Máquina Virtual
#
# El "pseudoensamblador" es una arquitectura de pila simple sin registros:
#
#   PUSH  <val>        empuja una constante entera
#   LOAD  <name>       empuja el valor de una variable / temporal
#   STORE <name>       saca (pop) → variable / temporal
#   ADD / SUB / MUL / DIV / NEG
#   LT / GT / LEQ / GEQ / EQ / NEQ   → empuja 0 o 1
#   AND / OR / NOT
#   JMP   <label>      salto incondicional
#   JZ    <label>      salta si el tope == 0 (hace pop)
#   JNZ   <label>      salta si el tope != 0 (hace pop)
#   CALL  <name>       llama a función, empuja valor de retorno
#   PARAM <n>          indica que n args están en la pila (visto antes de CALL)
#   RETURN             retorna (deja el valor en la pila para el llamador)
#   PRINT              saca de la pila e imprime
#   READ               empuja el valor leído desde stdin
#   LABEL <name>
#   FUNC  <name>       marca la entrada a una función
#   ENDFUNC <name>     marca la salida de una función
# =============================================================================

from ir_gen import Instruction


# ─── Generación de Código ─────────────────────────────────────────────────────

def generate_pseudoasm(ir: list[Instruction]) -> list[str]:
    """Traduce la representación intermedia (IR) de tres direcciones a líneas de pseudoensamblador."""
    asm = []

    for instr in ir:
        op, dest, arg1, arg2 = instr.op, instr.dest, instr.arg1, instr.arg2

        if op == 'FUNC_BEGIN':
            asm.append(f"FUNC {dest}")

        elif op == 'FUNC_PARAM':
            # Saca (pop) el argumento del llamador de la pila hacia la ranura del parámetro nombrado
            asm.append(f"STORE {dest}")

        elif op == 'FUNC_END':
            asm.append(f"ENDFUNC {dest}")

        elif op == 'LABEL':
            asm.append(f"LABEL {dest}")

        elif op == 'ASSIGN':
            _push_value(asm, arg1)
            asm.append(f"STORE {dest}")

        elif op in ('ADD','SUB','MUL','DIV',
                    'LT','GT','LEQ','GEQ','EQ','NEQ','AND','OR'):
            _push_value(asm, arg1)
            _push_value(asm, arg2)
            asm.append(op)
            asm.append(f"STORE {dest}")

        elif op == 'NEG':
            _push_value(asm, arg1)
            asm.append('NEG')
            asm.append(f"STORE {dest}")

        elif op == 'NOT':
            _push_value(asm, arg1)
            asm.append('NOT')
            asm.append(f"STORE {dest}")

        elif op == 'GOTO':
            asm.append(f"JMP {dest}")

        elif op == 'IF_TRUE':
            _push_value(asm, arg1)
            asm.append(f"JNZ {arg2}")

        elif op == 'IF_FALSE':
            _push_value(asm, arg1)
            asm.append(f"JZ {arg2}")

        elif op == 'PRINT':
            _push_value(asm, arg1)
            asm.append('PRINT')

        elif op == 'READ':
            asm.append('READ')
            asm.append(f"STORE {dest}")

        elif op == 'PARAM':
            _push_value(asm, arg1)

        elif op == 'CALL':
            # arg2 = número de argumentos (ya en la pila vía PARAM)
            asm.append(f"CALL {arg1}")
            asm.append(f"STORE {dest}")

        elif op == 'RETURN':
            if arg1 is not None:
                _push_value(asm, arg1)
            asm.append('RETURN')

    return asm


def _push_value(asm: list, v):
    """Emite un PUSH (para constantes) o LOAD (para nombres)."""
    if v is None:
        return
    s = str(v)
    try:
        int(s)
        asm.append(f"PUSH {s}")
    except ValueError:
        asm.append(f"LOAD {s}")


def format_asm(lines: list[str]) -> str:
    out = []
    for line in lines:
        if line.startswith(('FUNC ', 'LABEL ', 'ENDFUNC ')):
            out.append(line)
        else:
            out.append("  " + line)
    return "\n".join(out)


# ─── Máquina Virtual ──────────────────────────────────────────────────────────

class VMError(Exception):
    pass


class VM:
    """Máquina virtual basada en pila que ejecuta el pseudoensamblador."""

    def __init__(self, asm_lines: list[str], input_values: list = None):
        self.lines       = asm_lines
        self.stack:  list          = []
        self.memory: dict          = {}    # memoria global / temporal
        self.output: list[str]     = []
        self._input_queue          = list(reversed(input_values or []))

        # Construir mapas etiqueta → índice de línea y función → índice de línea
        self.label_map: dict[str, int] = {}
        self.func_map:  dict[str, int] = {}
        for i, line in enumerate(asm_lines):
            if line.startswith('LABEL '):
                self.label_map[line[6:].strip()] = i
            elif line.startswith('FUNC '):
                self.func_map[line[5:].strip()] = i

        # Pila de llamadas: lista de (return_pc, captura local_memory)
        self.call_stack: list = []

    def run(self):
        pc = 0
        # Iniciar la ejecución en 'main' si existe
        if 'main' in self.func_map:
            pc = self.func_map['main']
        
        frame_memory = self.memory   # variables del marco de llamada actual (frame)

        while pc < len(self.lines):
            line = self.lines[pc].strip()
            pc  += 1

            if not line or line.startswith(';'):
                continue

            parts = line.split(None, 1)
            cmd   = parts[0]
            arg   = parts[1].strip() if len(parts) > 1 else None

            # ── Operaciones de pila ───────────────────────────────────────────
            if cmd == 'PUSH':
                self.stack.append(int(arg))

            elif cmd == 'LOAD':
                if arg not in frame_memory:
                    raise VMError(f"Variable no definida '{arg}'")
                self.stack.append(frame_memory[arg])

            elif cmd == 'STORE':
                frame_memory[arg] = self.stack.pop()

            # ── Aritmética ────────────────────────────────────────────────────
            elif cmd == 'ADD': b=self.stack.pop(); a=self.stack.pop(); self.stack.append(a+b)
            elif cmd == 'SUB': b=self.stack.pop(); a=self.stack.pop(); self.stack.append(a-b)
            elif cmd == 'MUL': b=self.stack.pop(); a=self.stack.pop(); self.stack.append(a*b)
            elif cmd == 'DIV':
                b=self.stack.pop(); a=self.stack.pop()
                if b == 0: raise VMError("División por cero")
                self.stack.append(a // b)
            elif cmd == 'NEG': self.stack.append(-self.stack.pop())

            # ── Lógica ────────────────────────────────────────────────────────
            elif cmd == 'NOT': self.stack.append(int(not bool(self.stack.pop())))
            elif cmd == 'AND': b=self.stack.pop(); a=self.stack.pop(); self.stack.append(int(bool(a) and bool(b)))
            elif cmd == 'OR':  b=self.stack.pop(); a=self.stack.pop(); self.stack.append(int(bool(a) or  bool(b)))

            # ── Relacional ────────────────────────────────────────────────────
            elif cmd == 'LT':  b=self.stack.pop(); a=self.stack.pop(); self.stack.append(int(a <  b))
            elif cmd == 'GT':  b=self.stack.pop(); a=self.stack.pop(); self.stack.append(int(a >  b))
            elif cmd == 'LEQ': b=self.stack.pop(); a=self.stack.pop(); self.stack.append(int(a <= b))
            elif cmd == 'GEQ': b=self.stack.pop(); a=self.stack.pop(); self.stack.append(int(a >= b))
            elif cmd == 'EQ':  b=self.stack.pop(); a=self.stack.pop(); self.stack.append(int(a == b))
            elif cmd == 'NEQ': b=self.stack.pop(); a=self.stack.pop(); self.stack.append(int(a != b))

            # ── Flujo de control ──────────────────────────────────────────────
            elif cmd == 'JMP':
                pc = self.label_map[arg] + 1

            elif cmd == 'JZ':
                if not bool(self.stack.pop()):
                    pc = self.label_map[arg] + 1

            elif cmd == 'JNZ':
                if bool(self.stack.pop()):
                    pc = self.label_map[arg] + 1

            # ── Funciones ─────────────────────────────────────────────────────
            elif cmd == 'CALL':
                # Guardar el estado y saltar a la función
                self.call_stack.append((pc, frame_memory))
                frame_memory = {}
                pc = self.func_map[arg] + 1   # saltar la línea FUNC

            elif cmd == 'RETURN':
                if not self.call_stack:
                    break   # main retornó
                pc, frame_memory = self.call_stack.pop()

            elif cmd in ('FUNC', 'ENDFUNC', 'LABEL'):
                pass   # solo marcadores

            # ── I/O (Entrada/Salida) ──────────────────────────────────────────
            elif cmd == 'PRINT':
                val = self.stack.pop()
                # Mostrar booleanos como true/false para legibilidad
                text = str(val)
                self.output.append(text)
                print(text)

            elif cmd == 'READ':
                if self._input_queue:
                    val = self._input_queue.pop()
                else:
                    val = int(input("leer> "))
                self.stack.append(val)

            # ── Param: el argumento ya está en la pila (empujado por PARAM) ───
            elif cmd == 'PARAM':
                pass   # manejado en el sitio de llamada

            else:
                raise VMError(f"Instrucción desconocida: {line!r}")

        return self.output