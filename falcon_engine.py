import sys
import re
import os
import requests
from google import genai  # New Google AI SDK

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
        self.line_num = 1
        self.bridge_url = "https://f13080e7d994051c-152-59-162-148.serveousercontent.com/send"
        
        # New AI Config for 2026
        self.api_key = "YOUR_GEMINI_API_KEY"
        if self.api_key != "YOUR_GEMINI_API_KEY":
            self.client = genai.Client(api_key=self.api_key)
        
        self.base_dir = os.getcwd()

    def report_error(self, error_type, message, line):
        print(f"\n🔥 [Falcon {error_type} Error]")
        print(f"👉 {message}")
        print(f"📍 Location: Line {line}")
        print("-" * 30)
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
            print(f"❌ File '{filename}' not found.")
            return
        with open(filename, 'r') as f:
            code = f.read()
        self.tokenize(code)
        self.execute(0, len(self.tokens))

    def execute(self, start, end):
        idx = start
        while idx < end:
            kind, val, line = self.tokens[idx]

            # 1. Module System (Import)
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

            # 2. Secure Let (Variables, AI, Dict, Math)
            elif kind == 'SECURE_LET':
                target = self.tokens[idx+1][1]
                
                # Dictionary Support
                if self.tokens[idx+3][0] == 'LBRACE':
                    idx += 4
                    obj = {}
                    while self.tokens[idx][0] != 'RBRACE':
                        k = self.tokens[idx][1].strip('"')
                        v = self.tokens[idx+2][1].strip('"')
                        obj[k] = v
                        idx += 3
                        if self.tokens[idx][0] == 'COMMA': idx += 1
                    self.variables[target] = obj
                    idx += 1
                
                # AI Support (Updated for Gemini 2.0)
                elif self.tokens[idx+3][1] == 'ai.ask':
                    prompt = self.tokens[idx+5][1].strip('"')
                    print(f"🧠 [Falcon AI] Querying Gemini 2.0...")
                    try:
                        response = self.client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=prompt
                        )
                        self.variables[target] = response.text
                    except Exception as e:
                        self.variables[target] = f"AI Error: {str(e)}"
                    idx += 7
                
                # Math Logic
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
                    self.variables[target] = self.tokens[idx+3][1].strip('"')
                    idx += 4

            # 3. Print Output
            elif kind == 'PRINT':
                content = self.tokens[idx+2][1].strip('"')
                print(f"🦅 [Falcon]: {self.variables.get(content, content)}")
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

            # 5. Shield-Core File IO
            elif kind == 'FILE_IO' and val == 'file.write':
                f_name = self.tokens[idx+2][1].strip('"')
                f_data = self.variables.get(self.tokens[idx+4][1], self.tokens[idx+4][1].strip('"'))
                if self.is_path_allowed(f_name):
                    with open(f_name, 'w') as f: f.write(str(f_data))
                    print(f"💾 [IO] Saved to {f_name}")
                else: self.report_error("Security", "Access denied", line)
                idx += 6
            
            else: idx += 1

def main():
    if len(sys.argv) > 1: FalconEngine().run(sys.argv[1])
    else: print("🦅 Falcon Engine v4.6 (Future-Ready) Active")

if __name__ == "__main__":
    main()
        
