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
        # আপনার সেই Serveo লিঙ্ক
        self.bridge_url = "https://f13080e7d994051c-152-59-162-148.serveousercontent.com/send"

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
                print(f"❌ [Falcon Error] Unexpected character '{value}' at line {self.line_num}")
                sys.exit(1)
            else:
                self.tokens.append((kind, value, self.line_num))

    def run(self, filename):
        try:
            with open(filename, 'r') as f:
                code = f.read()
            self.tokenize(code)
            self.execute()
        except FileNotFoundError:
            print(f"❌ Error: File '{filename}' not found.")

    def execute(self):
        idx = 0
        while idx < len(self.tokens):
            kind, value, line = self.tokens[idx]

            # ১. Variable Declaration (secure let)
            if kind == 'SECURE_LET':
                var_name = self.tokens[idx+1][1]
                # `=` এবং মান চেক করা
                val = self.tokens[idx+3][1].strip('"')
                self.variables[var_name] = int(val) if val.isdigit() else val
                print(f"🛡️ [Line {line}] Shield-Core Secured: {var_name}")
                idx += 4

            # ২. Output (print)
            elif kind == 'PRINT':
                content = self.tokens[idx+2][1].strip('"')
                output = self.variables.get(content, content)
                print(f"🦅 [Falcon Output]: {output}")
                idx += 4

            # ৩. Logic (if ... endif)
            elif kind == 'IF':
                var_name = self.tokens[idx+1][1]
                op = self.tokens[idx+2][1]
                target = int(self.tokens[idx+3][1])
                current = self.variables.get(var_name, 0)
                
                check = eval(f"{current} {op} {target}")
                print(f"⚖️ [Logic] Line {line}: Condition ({var_name} {op} {target}) is {check}")
                
                if not check:
                    # endif না পাওয়া পর্যন্ত সব স্কিপ করবে
                    while idx < len(self.tokens) and self.tokens[idx][0] != 'ENDIF':
                        idx += 1
                else:
                    idx += 4

            # ৪. Networking (network.send)
            elif kind == 'NET_SEND':
                msg_var = self.tokens[idx+2][1].strip('"')
                msg_val = self.variables.get(msg_var, msg_var)
                
                print(f"📡 [Line {line}] Transmitting via Falcon Net: {msg_val}")
                
                try:
                    response = requests.post(self.bridge_url, json={"message": msg_val, "sender": "Falcon_User"}, timeout=5)
                    if response.status_code == 200:
                        print("✅ Status: Delivered via Satellite Link!")
                    else:
                        print(f"⚠️ Status: Server Error ({response.status_code})")
                except:
                    print("❌ Error: Transmission Failed. Is the tunnel active?")
                idx += 4

            elif kind == 'ENDIF':
                idx += 1
            
            else:
                idx += 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Falcon Programming Language v3.0")
        print("Usage: python falcon_engine.py <file.fcn>")
    else:
        engine = FalconEngine()
        engine.run(sys.argv[1])
        
