import sys
import re
import requests

# --- TOKEN DEFINITIONS ---
TOKEN_TYPES = [
    ('COMMENT',    r'//.*'),
    ('SECURE_LET', r'secure let'),
    ('IF',         r'if'),
    ('ENDIF',      r'endif'),
    ('PRINT',      r'print'),
    ('NET_SEND',   r'network\.send'),
    ('FILE_IO',    r'file\.(write|read)'), # New Token for Standard Library
    ('ID',         r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('OP',         r'==|!=|>=|<=|>|<'),
    ('ASSIGN',     r'='),
    ('STRING',     r'".*?"'),
    ('NUMBER',     r'\d+'),
    ('LPAREN',     r'\('),
    ('RPAREN',     r'\)'),
    ('COMMA',      r','),
    ('NEWLINE',    r'\n'),
    ('SKIP',       r'[ \t]+'),
    ('MISMATCH',   r'.'),
]

class FalconEngine:
    def __init__(self):
        self.variables = {}
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
            if kind == 'NEWLINE':
                self.line_num += 1
            elif kind == 'SKIP' or kind == 'COMMENT':
                continue
            elif kind == 'MISMATCH':
                self.report_error(f"Unexpected character '{value}'", self.line_num)
            else:
                self.tokens.append((kind, value, self.line_num))

    def run(self, filename):
        try:
            with open(filename, 'r') as f:
                code = f.read()
            self.tokenize(code)
            self.execute()
        except FileNotFoundError:
            print(f"❌ [File Error] File '{filename}' not found.")

    def execute(self):
        idx = 0
        while idx < len(self.tokens):
            kind, value, line = self.tokens[idx]

            # 1. Variable Declaration
            if kind == 'SECURE_LET':
                name = self.tokens[idx+1][1]
                # Check if it's a file read assignment: secure let x = file.read(...)
                if self.tokens[idx+3][1] == 'file.read':
                    file_name = self.tokens[idx+5][1].strip('"')
                    try:
                        with open(file_name, 'r') as f:
                            self.variables[name] = f.read()
                        print(f"📖 [falcon.io] Loaded '{file_name}' into '{name}'")
                    except: self.report_error(f"Could not read file {file_name}", line)
                    idx += 7
                else:
                    val = self.tokens[idx+3][1].strip('"')
                    self.variables[name] = int(val) if val.isdigit() else val
                    print(f"🛡️ [Line {line}] Secured: {name}")
                    idx += 4

            # 2. File Writing (Standard Library)
            elif kind == 'FILE_IO' and value == 'file.write':
                try:
                    f_name = self.tokens[idx+2][1].strip('"')
                    f_content = self.tokens[idx+4][1].strip('"')
                    
                    final_name = self.variables.get(f_name, f_name)
                    final_content = self.variables.get(f_content, f_content)
                    
                    with open(final_name, 'w') as f:
                        f.write(str(final_content))
                    print(f"💾 [falcon.io] Written to '{final_name}'")
                    idx += 6
                except: self.report_error("File write failed", line)

            # 3. Print
            elif kind == 'PRINT':
                content = self.tokens[idx+2][1].strip('"')
                print(f"🦅 [Falcon]: {self.variables.get(content, content)}")
                idx += 4

            # 4. If Logic
            elif kind == 'IF':
                var = self.tokens[idx+1][1]
                op = self.tokens[idx+2][1]
                target = int(self.tokens[idx+3][1])
                check = eval(f"{self.variables.get(var, 0)} {op} {target}")
                if not check:
                    while idx < len(self.tokens) and self.tokens[idx][0] != 'ENDIF': idx += 1
                idx += 4

            # 5. Network
            elif kind == 'NET_SEND':
                msg = self.variables.get(self.tokens[idx+2][1].strip('"'), self.tokens[idx+2][1].strip('"'))
                try:
                    requests.post(self.bridge_url, json={"message": msg}, timeout=5)
                    print(f"📡 Transmitted: {msg}")
                except: print("❌ Network Fail")
                idx += 4

            else: idx += 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        FalconEngine().run(sys.argv[1])
    else:
        print("Falcon v3.2 - Usage: python falcon_engine.py <file.fcn>")
            
