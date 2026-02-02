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
    ('ID',         r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('OP',         r'==|!=|>=|<=|>|<'),
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

            # 1. Variable Declaration Error Check
            if kind == 'SECURE_LET':
                try:
                    if self.tokens[idx+1][0] != 'ID':
                        self.report_error("Expected a variable name after 'secure let'", line)
                    var_name = self.tokens[idx+1][1]
                    
                    if self.tokens[idx+2][0] != 'ASSIGN':
                        self.report_error(f"Expected '=' after variable '{var_name}'", line)
                    
                    val_kind = self.tokens[idx+3][0]
                    if val_kind not in ['STRING', 'NUMBER', 'ID']:
                        self.report_error(f"Expected a value (string or number) for variable '{var_name}'", line)
                    
                    val = self.tokens[idx+3][1].strip('"')
                    self.variables[var_name] = int(val) if val.isdigit() else val
                    print(f"🛡️ [Line {line}] Shield-Core Secured: {var_name}")
                    idx += 4
                except IndexError:
                    self.report_error("Incomplete 'secure let' statement", line)

            # 2. Print Statement Error Check
            elif kind == 'PRINT':
                try:
                    if self.tokens[idx+1][0] != 'LPAREN' or self.tokens[idx+3][0] != 'RPAREN':
                        self.report_error("Syntax error in print statement. Use print(\"message\")", line)
                    content = self.tokens[idx+2][1].strip('"')
                    output = self.variables.get(content, content)
                    print(f"🦅 [Falcon Output]: {output}")
                    idx += 4
                except IndexError:
                    self.report_error("Incomplete print statement", line)

            # 3. IF Logic Error Check
            elif kind == 'IF':
                try:
                    var_name = self.tokens[idx+1][1]
                    op = self.tokens[idx+2][1]
                    target = int(self.tokens[idx+3][1])
                    current = self.variables.get(var_name, 0)
                    
                    check = eval(f"{current} {op} {target}")
                    print(f"⚖️ [Logic] Line {line}: Condition ({var_name} {op} {target}) is {check}")
                    
                    if not check:
                        while idx < len(self.tokens) and self.tokens[idx][0] != 'ENDIF':
                            idx += 1
                        if idx >= len(self.tokens):
                            self.report_error("Missing 'endif' for 'if' statement", line)
                    else:
                        idx += 4
                except (IndexError, ValueError):
                    self.report_error("Invalid if condition syntax", line)

            # 4. Networking Error Check
            elif kind == 'NET_SEND':
                try:
                    msg_var = self.tokens[idx+2][1].strip('"')
                    msg_val = self.variables.get(msg_var, msg_var)
                    print(f"📡 [Line {line}] Transmitting via Falcon Net: {msg_val}")
                    # ... Network request logic stays same ...
                    idx += 4
                except IndexError:
                    self.report_error("Incomplete network.send statement", line)

            elif kind == 'ENDIF':
                idx += 1
            else:
                idx += 1

if __name__ == "__main__":
    engine = FalconEngine()
    engine.run(sys.argv[1])
    
