import sys
import re
import requests

# --- TOKEN DEFINITIONS ---
TOKEN_TYPES = [
    ('COMMENT',    r'//.*'),
    ('FUNC_DEF',   r'func'),     # New: Function definition
    ('ENDFUNC',    r'endfunc'),  # New: Function end
    ('SECURE_LET', r'secure let'),
    ('IF',         r'if'),
    ('ENDIF',      r'endif'),
    ('REPEAT',     r'repeat'),
    ('ENDREPEAT',  r'endrepeat'),
    ('PRINT',      r'print'),
    ('NET_SEND',   r'network\.send'),
    ('FILE_IO',    r'file\.(write|read)'),
    ('ID',         r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('OP',         r'==|!=|>=|<=|>|<|\+|\-|\*|\/'),
    ('ASSIGN',     r'='),
    ('STRING',     r'".*?"'),
    ('NUMBER',     r'\d+'),
    ('LPAREN',     r'\('),
    ('RPAREN',     r'\)'),
    ('NEWLINE',    r'\n'),
    ('SKIP',       r'[ \t]+'),
    ('MISMATCH',   r'.'),
]

class FalconEngine:
    def __init__(self):
        self.variables = {}
        self.functions = {} # To store function code blocks
        self.tokens = []
        self.line_num = 1
        self.bridge_url = "https://f13080e7d994051c-152-59-162-148.serveousercontent.com/send"

    def report_error(self, message, line):
        print(f"\n❌ [Falcon Error] {message}")
        print(f"📍 Location: Line {line}\n")
        sys.exit(1)

    def tokenize(self, code):
        tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in TOKEN_TYPES)
        for mo in re.finditer(tok_regex, code):
            kind = mo.lastgroup
            value = mo.group()
            if kind == 'NEWLINE': self.line_num += 1
            elif kind == 'SKIP' or kind == 'COMMENT': continue
            elif kind == 'MISMATCH': self.report_error(f"Unexpected character '{value}'", self.line_num)
            else: self.tokens.append((kind, value, self.line_num))

    def run(self, filename):
        try:
            with open(filename, 'r') as f:
                code = f.read()
            self.tokenize(code)
            self.execute(0, len(self.tokens))
        except FileNotFoundError:
            print(f"❌ [File Error] File '{filename}' not found.")

    def execute(self, start_idx, end_idx):
        idx = start_idx
        while idx < end_idx:
            kind, value, line = self.tokens[idx]

            # 1. Function Definition
            if kind == 'FUNC_DEF':
                func_name = self.tokens[idx+1][1]
                idx += 2
                func_start = idx
                depth = 1
                while depth > 0 and idx < end_idx:
                    if self.tokens[idx][0] == 'FUNC_DEF': depth += 1
                    if self.tokens[idx][0] == 'ENDFUNC': depth -= 1
                    idx += 1
                self.functions[func_name] = (func_start, idx - 1)
                continue

            # 2. Variable Declaration & Math
            elif kind == 'SECURE_LET':
                try:
                    target_var = self.tokens[idx+1][1]
                    if idx + 4 < end_idx and self.tokens[idx+4][0] == 'OP' and self.tokens[idx+4][1] in '+-*/':
                        v1 = self.variables.get(self.tokens[idx+3][1], int(self.tokens[idx+3][1]) if self.tokens[idx+3][1].isdigit() else self.tokens[idx+3][1])
                        v2 = self.variables.get(self.tokens[idx+5][1], int(self.tokens[idx+5][1]) if self.tokens[idx+5][1].isdigit() else self.tokens[idx+5][1])
                        op = self.tokens[idx+4][1]
                        if op == '+': res = v1 + v2
                        elif op == '-': res = v1 - v2
                        elif op == '*': res = v1 * v2
                        elif op == '/': res = v1 / v2
                        self.variables[target_var] = res
                        print(f"🧬 [Math] {target_var} = {res}")
                        idx += 6
                    elif self.tokens[idx+3][1] == 'file.read':
                        f_name = self.tokens[idx+5][1].strip('"')
                        with open(f_name, 'r') as f: self.variables[target_var] = f.read()
                        print(f"📖 [IO] Loaded '{f_name}'")
                        idx += 7
                    else:
                        val = self.tokens[idx+3][1].strip('"')
                        self.variables[target_var] = int(val) if val.isdigit() else val
                        print(f"🛡️ [Line {line}] Secured: {target_var}")
                        idx += 4
                except: self.report_error("Invalid declaration", line)

            # 3. Loop (Repeat)
            elif kind == 'REPEAT':
                times = int(self.tokens[idx+1][1])
                loop_start = idx + 2
                depth, loop_end = 1, loop_start
                while depth > 0 and loop_end < end_idx:
                    if self.tokens[loop_end][0] == 'REPEAT': depth += 1
                    if self.tokens[loop_end][0] == 'ENDREPEAT': depth -= 1
                    loop_end += 1
                for _ in range(times): self.execute(loop_start, loop_end - 1)
                idx = loop_end

            # 4. If Logic
            elif kind == 'IF':
                var = self.variables.get(self.tokens[idx+1][1], 0)
                op, target = self.tokens[idx+2][1], int(self.tokens[idx+3][1])
                if not eval(f"{var} {op} {target}"):
                    while idx < end_idx and self.tokens[idx][0] != 'ENDIF': idx += 1
                idx += 4

            # 5. Function Call
            elif kind == 'ID' and value in self.functions:
                f_start, f_end = self.functions[value]
                self.execute(f_start, f_end)
                idx += 1

            # 6. Commands (Print, IO, Network)
            elif kind == 'PRINT':
                print(f"🦅 [Falcon]: {self.variables.get(self.tokens[idx+2][1].strip('\"'), self.tokens[idx+2][1].strip('\"'))}")
                idx += 4
            elif kind == 'FILE_IO' and value == 'file.write':
                f_name = self.variables.get(self.tokens[idx+2][1].strip('"'), self.tokens[idx+2][1].strip('"'))
                f_data = self.variables.get(self.tokens[idx+4][1].strip('"'), self.tokens[idx+4][1].strip('"'))
                with open(f_name, 'w') as f: f.write(str(f_data))
                print(f"💾 [IO] Written to '{f_name}'"); idx += 6
            elif kind == 'NET_SEND':
                msg = self.variables.get(self.tokens[idx+2][1].strip('"'), self.tokens[idx+2][1].strip('"'))
                try: requests.post(self.bridge_url, json={"message": msg}, timeout=5); print(f"📡 Transmitted: {msg}")
                except: print("❌ Network Fail"); idx += 4
            
            else: idx += 1

if __name__ == "__main__":
    if len(sys.argv) > 1: FalconEngine().run(sys.argv[1])
    else: print("Falcon v3.5 - Usage: python falcon_engine.py <file.fcn>")
                        
