import sys
import re
import os
import requests
import google.generativeai as genai

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
        self.functions = {}
        self.tokens = []
        self.line_num = 1
        self.bridge_url = "https://f13080e7d994051c-152-59-162-148.serveousercontent.com/send"
        
        # AI Config
        self.api_key = "YOUR_GEMINI_API_KEY"
        if self.api_key != "YOUR_GEMINI_API_KEY":
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        
        # Shield-Core Sandbox
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
                    with open(module_name, 'r') as f:
                        m_code = f.read()
                    # Recursive tokenization for module
                    sub_engine = FalconEngine()
                    sub_engine.variables = self.variables # Share memory
                    sub_engine.run(module_name)
                    self.variables.update(sub_engine.variables)
                else:
                    self.report_error("Import", f"Module '{module_name}' missing", line)
                idx += 2

            # 2. Secure Let (Variables, Math, AI, Dict)
            elif kind == 'SECURE_LET':
                target = self.tokens[idx+1][1]
                
                # Dictionary / Data Structure
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
                
                # AI Integration
                elif self.tokens[idx+3][1] == 'ai.ask':
                    prompt = self.tokens[idx+5][1].strip('"')
                    print(f"🧠 [Falcon AI] Thinking: {prompt}...")
                    try:
                        response = self.model.generate_content(prompt)
                        self.variables[target] = response.text
                    except:
                        self.variables[target] = "AI Error: Key/Network issue"
                    idx += 7
                
                # Math Operations
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

            # 3. Loops (Repeat)
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

            # 4. If Logic
            elif kind == 'IF':
                var = self.variables.get(self.tokens[idx+1][1], 0)
                op, target_val = self.tokens[idx+2][1], int(self.tokens[idx+3][1])
                if not eval(f"{var} {op} {target_val}"):
                    while idx < end and self.tokens[idx][0] != 'ENDIF': idx += 1
                idx += 4

            # 5. IO & Network
            elif kind == 'PRINT':
                content = self.tokens[idx+2][1].strip('"')
                print(f"🦅 [Falcon]: {self.variables.get(content, content)}")
                idx += 4
            elif kind == 'FILE_IO' and val == 'file.write':
                f_name = self.tokens[idx+2][1].strip('"')
                f_data = self.variables.get(self.tokens[idx+4][1], self.tokens[idx+4][1].strip('"'))
                if self.is_path_allowed(f_name):
                    with open(f_name, 'w') as f: f.write(str(f_data))
                    print(f"💾 [IO] Saved to {f_name}")
                else: self.report_error("Security", "Access to system files denied", line)
                idx += 6
            elif kind == 'NET_SEND':
                msg = self.variables.get(self.tokens[idx+2][1].strip('"'), self.tokens[idx+2][1].strip('"'))
                try: requests.post(self.bridge_url, json={"message": msg}, timeout=5)
                except: pass
                idx += 4
            
            else: idx += 1

if __name__ == "__main__":
    if len(sys.argv) > 1: FalconEngine().run(sys.argv[1])
    else: print("Falcon Engine v4.5 Unified Active")
        # ... (আগের সব কোড এখানে থাকবে) ...

def main():
    engine = FalconEngine()
    if len(sys.argv) > 1:
        # 'falcon run filename.fcn' support করার জন্য
        if sys.argv[1] == "run" and len(sys.argv) > 2:
            engine.run(sys.argv[2])
        else:
            engine.run(sys.argv[1])
    else:
        print("🦅 Falcon Engine v4.5 Active. Use 'falcon <filename>' to run.")

if __name__ == "__main__":
    main()
    
