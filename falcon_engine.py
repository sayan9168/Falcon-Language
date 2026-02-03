import sys
import re
import os
import json
import requests
from google import genai

# টার্মিনাল কালার কোড
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

# --- TOKEN DEFINITIONS ---
TOKEN_TYPES = [
    ('COMMENT',    r'//.*'),
    ('IMPORT',     r'import'),       
    ('SECURE_LET', r'secure let'),
    ('IF',         r'if'),
    ('ENDIF',      r'endif'),
    ('REPEAT',     r'repeat'),
    ('ENDREPEAT',  r'endrepeat'),
    ('PRINT',      r'print'),
    ('FILE_IO',    r'file\.(write|read)'),
    ('AI_CALL',    r'ai\.ask'), 
    ('NET_SEND',   r'network\.send'),
    ('ID',         r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('OP',         r'==|!=|>=|<=|>|<|\+|\-|\*|\/'),
    ('ASSIGN',     r'='),
    ('STRING',     r'".*?"'),
    ('NUMBER',     r'\d+'),
    ('LPAREN',     r'\('),
    ('RPAREN',     r'\)'),
    ('LBRACE',     r'\{'),           
    ('RBRACE',     r'\}'),
    ('LBRACKET',   r'\['), # নতুন: লিস্টের জন্য           
    ('RBRACKET',   r'\]'), # নতুন: লিস্টের জন্য
    ('COLON',      r':'),
    ('COMMA',      r','),
    ('NEWLINE',    r'\n'),
    ('SKIP',       r'[ \t]+'),
    ('MISMATCH',   r'.'),
]

class FalconEngine:
    def __init__(self):
        self.variables = {}
        self.tokens = []
        self.base_dir = os.getcwd()
        self.config_path = os.path.expanduser("~/.falcon_config")
        self.load_auth()

    def load_auth(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                key = config.get("api_key")
                self.client = genai.Client(api_key=key) if key else None
        else:
            self.client = None

    def save_auth(self, key):
        with open(self.config_path, 'w') as f:
            json.dump({"api_key": key}, f)
        print(f"{GREEN}✅ Authentication Successful! Falcon AI is now active.{RESET}")

    def report_error(self, error_type, message, line):
        print(f"\n{RED}🔥 [Falcon {error_type} Error]{RESET}")
        print(f"{YELLOW}👉 Message:{RESET} {message}")
        print(f"{CYAN}📍 Location:{RESET} Line {line}")
        print(f"{RED}{'-' * 35}{RESET}")
        sys.exit(1)

    def is_path_allowed(self, path):
        return os.path.abspath(path).startswith(os.path.abspath(self.base_dir))

    def tokenize(self, code):
        tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in TOKEN_TYPES)
        self.tokens = []
        for mo in re.finditer(tok_regex, code):
            kind = mo.lastgroup
            value = mo.group()
            current_line = code[:mo.start()].count('\n') + 1
            if kind == 'SKIP' or kind == 'COMMENT': continue
            elif kind == 'MISMATCH': 
                self.report_error("Syntax", f"Unknown character '{value}'", current_line)
            else: self.tokens.append((kind, value, current_line))

    def run(self, filename):
        if not os.path.exists(filename):
            print(f"{RED}❌ File '{filename}' not found.{RESET}")
            return
        with open(filename, 'r') as f:
            code = f.read()
        self.tokenize(code)
        self.execute(0, len(self.tokens))

    def execute(self, start, end):
        idx = start
        while idx < end:
            kind, val, line = self.tokens[idx]

            # 1. Module System
            if kind == 'IMPORT':
                module_name = self.tokens[idx+1][1].strip('"') + ".fcn"
                if os.path.exists(module_name):
                    sub_engine = FalconEngine()
                    sub_engine.variables = self.variables
                    sub_engine.run(module_name)
                    self.variables.update(sub_engine.variables)
                else:
                    self.report_error("Import", f"Module '{module_name}' missing", line)
                idx += 2

            # 2. Secure Let (Variable/Dict/AI/List/Math)
            elif kind == 'SECURE_LET':
                target = self.tokens[idx+1][1]
                
                # --- List Support ---
                if self.tokens[idx+3][0] == 'LBRACKET':
                    idx += 4
                    arr = []
                    while self.tokens[idx][0] != 'RBRACKET':
                        item = self.tokens[idx][1].strip('"')
                        if item.isdigit(): item = int(item)
                        arr.append(item)
                        idx += 1
                        if self.tokens[idx][0] == 'COMMA': idx += 1
                    self.variables[target] = arr
                    idx += 1

                # --- Dictionary Support ---
                elif self.tokens[idx+3][0] == 'LBRACE':
                    idx += 4
                    obj = {}
                    while self.tokens[idx][0] != 'RBRACE':
                        k = self.tokens[idx][1].strip('"')
                        v = self.tokens[idx+2][1].strip('"')
                        if v.isdigit(): v = int(v)
                        obj[k] = v
                        idx += 3
                        if self.tokens[idx][0] == 'COMMA': idx += 1
                    self.variables[target] = obj
                    idx += 1
                
                # --- AI Support ---
                elif self.tokens[idx+3][1] == 'ai.ask':
                    if not self.client:
                        self.report_error("Auth", "AI Key not found. Run 'falcon --auth' first.", line)
                    prompt = self.tokens[idx+5][1].strip('"')
                    print(f"{CYAN}🧠 [Falcon AI] Querying Gemini...{RESET}")
                    try:
                        response = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                        self.variables[target] = response.text
                    except Exception as e:
                        self.variables[target] = f"AI Error: {str(e)}"
                    idx += 7

                # --- Math Support ---
                elif idx + 4 < end and self.tokens[idx+4][0] == 'OP':
                    v1 = self.variables.get(self.tokens[idx+3][1], int(self.tokens[idx+3][1]) if self.tokens[idx+3][1].isdigit() else self.tokens[idx+3][1])
                    v2 = self.variables.get(self.tokens[idx+5][1], int(self.tokens[idx+5][1]) if self.tokens[idx+5][1].isdigit() else self.tokens[idx+5][1])
                    op = self.tokens[idx+4][1]
                    if op == '+': res = v1 + v2
                    elif op == '-': res = v1 - v2
                    elif op == '*': res = v1 * v2
                    elif op == '/': res = v1 / v2
                    self.variables[target] = res
                    idx += 6
                else:
                    val_to_store = self.tokens[idx+3][1].strip('"')
                    if val_to_store.isdigit(): val_to_store = int(val_to_store)
                    self.variables[target] = val_to_store
                    idx += 4

            # 3. Print Output
            elif kind == 'PRINT':
                content = self.tokens[idx+2][1].strip('"')
                data = self.variables.get(content, content)
                print(f"{GREEN}🦅 [Falcon]:{RESET} {data}")
                idx += 4
            
            # 4. Repeat Loops
            elif kind == 'REPEAT':
                times = int(self.tokens[idx+1][1])
                loop_start = idx + 2
                depth, loop_end = 1, loop_start
                while depth > 0:
                    if self.tokens[loop_end][0] == 'REPEAT': depth += 1
                    if self.tokens[loop_end][0] == 'ENDREPEAT': depth -= 1
                    loop_end += 1
                for _ in range(times): self.execute(loop_start, loop_end - 1)
                idx = loop_end
            
            else: idx += 1

def main():
    engine = FalconEngine()
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--auth":
            key = input("🔑 Enter Gemini API Key: ").strip()
            engine.save_auth(key)
        else:
            engine.run(arg)
    else:
        print(f"{CYAN}🦅 Falcon Engine v4.8 (Arrays & Pro) Active{RESET}")
        print(f"Usage: {GREEN}falcon <filename>{RESET} or {YELLOW}falcon --auth{RESET}")

if __name__ == "__main__":
    main()
        
