import sys
import re
import os
import json
from google import genai

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

TOKEN_TYPES = [
    ('COMMENT',          r'//.*'),
    ('IMPORT',           r'import'),
    ('SECURE_LET',       r'secure let'),
    ('SECURE_CONST',     r'secure const'),
    ('TRY',              r'try'),
    ('CATCH',            r'catch'),
    ('ENDTRY',           r'endtry'),
    ('IF',               r'if'),               # নতুন
    ('ELSEIF',           r'elseif'),           # নতুন
    ('ELSE',             r'else'),             # নতুন
    ('ENDIF',            r'endif'),            # নতুন
    ('REPEAT',           r'repeat'),
    ('ENDREPEAT',        r'endrepeat'),
    ('PRINT',            r'print'),
    ('FILE_IO',          r'file\.(write|read)'),
    ('AI_CALL',          r'ai\.ask'),
    ('AI_GENERATE_CODE', r'ai\.generate_code'),
    ('AI_EXPLAIN',       r'ai\.explain'),
    ('AI_REFACTOR',      r'ai\.refactor'),
    ('NET_SEND',         r'network\.send'),
    ('CRYPTO_HASH',      r'crypto\.hash'),
    ('CRYPTO_ENCRYPT',   r'crypto\.encrypt'),
    ('CRYPTO_DECRYPT',   r'crypto\.decrypt'),
    ('LOG',              r'log'),
    ('SECURE_INPUT',     r'secure input'),
    ('FN_DEF',           r'fn'),               # নতুন: function definition
    ('RETURN',           r'return'),           # নতুন
    ('BREAK',            r'break'),            # নতুন (repeat-এর জন্য)
    ('CONTINUE',         r'continue'),         # নতুন
    ('ID',               r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('OP',               r'==|!=|>=|<=|>|<|\+|\-|\*|\/'),
    ('ASSIGN',           r'='),
    ('STRING',           r'".*?"'),
    ('NUMBER',           r'\d+'),
    ('LPAREN',           r'\('),
    ('RPAREN',           r'\)'),
    ('LBRACE',           r'\{'),
    ('RBRACE',           r'\}'),
    ('LBRACKET',         r'\['),
    ('RBRACKET',         r'\]'),
    ('COLON',            r':'),
    ('COMMA',            r','),
    ('NEWLINE',          r'\n'),
    ('SKIP',             r'[ \t]+'),
    ('MISMATCH',         r'.'),
]

class FalconEngine:
    def __init__(self):
        self.variables = {}
        self.constants = set()
        self.functions = {}  # function name -> (params, body_start, body_end)
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
            else:
                self.tokens.append((kind, value, current_line))

    def _call_gemini(self, prompt, line):
        if not self.client:
            self.report_error("Auth", "AI Key not found. Run 'falcon --auth' first.", line)
        print(f"{CYAN}🧠 [Falcon AI] Querying Gemini...{RESET}")
        try:
            response = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return response.text.strip()
        except Exception as e:
            return f"AI Error: {str(e)}"

    def execute(self, start, end):
        idx = start
        while idx < end:
            kind, val, line = self.tokens[idx]

            # Function Definition
            if kind == 'FN_DEF':
                fn_name = self.tokens[idx+1][1]
                if idx+3 >= end or self.tokens[idx+2][0] != 'LPAREN':
                    self.report_error("Syntax", "Expected ( after fn name", line)

                params = []
                i = idx + 3
                while i < end and self.tokens[i][0] != 'RPAREN':
                    if self.tokens[i][0] == 'ID':
                        params.append(self.tokens[i][1])
                    i += 1
                    if i < end and self.tokens[i][0] == 'COMMA': i += 1
                i += 1  # skip )

                if i >= end or self.tokens[i][0] != 'LBRACE':
                    self.report_error("Syntax", "Expected { after parameters", line)

                body_start = i + 1
                depth = 1
                body_end = body_start
                while body_end < end and depth > 0:
                    if self.tokens[body_end][0] == 'LBRACE': depth += 1
                    if self.tokens[body_end][0] == 'RBRACE': depth -= 1
                    body_end += 1

                self.functions[fn_name] = (params, body_start, body_end - 1)
                idx = body_end

            # Return Statement
            elif kind == 'RETURN':
                if idx+1 >= end:
                    self.report_error("Syntax", "return expects a value", line)
                return_val = self.tokens[idx+1][1]
                if return_val in self.variables:
                    return_val = self.variables[return_val]
                elif return_val.isdigit():
                    return_val = int(return_val)
                else:
                    return_val = return_val.strip('"')
                return return_val  # ফাংশন থেকে রিটার্ন করবে

            # Function Call
            elif kind == 'ID' and idx+1 < end and self.tokens[idx+1][0] == 'LPAREN':
                fn_name = val
                if fn_name not in self.functions:
                    self.report_error("NameError", f"Function '{fn_name}' not defined", line)

                params, body_start, body_end = self.functions[fn_name]
                args = []
                i = idx + 2
                while i < end and self.tokens[i][0] != 'RPAREN':
                    arg_val = self.tokens[i][1]
                    if arg_val in self.variables:
                        args.append(self.variables[arg_val])
                    elif arg_val.isdigit():
                        args.append(int(arg_val))
                    else:
                        args.append(arg_val.strip('"'))
                    i += 1
                    if i < end and self.tokens[i][0] == 'COMMA': i += 1
                i += 1  # skip )

                if len(args) != len(params):
                    self.report_error("TypeError", f"Expected {len(params)} arguments, got {len(args)}", line)

                old_vars = self.variables.copy()
                for p, a in zip(params, args):
                    self.variables[p] = a

                result = self.execute(body_start, body_end + 1)
                self.variables = old_vars

                if 'target' in locals() and target:
                    self.variables[target] = result if result is not None else None

                idx = i

            # Secure Let (আগের সব + নতুন)
            elif kind == 'SECURE_LET':
                target = self.tokens[idx+1][1]
                if target in self.constants:
                    self.report_error("ConstError", f"Cannot reassign constant '{target}'", line)

                # secure array
                if idx+3 < end and self.tokens[idx+3][0] == 'LBRACKET':
                    idx += 4
                    arr = []
                    while idx < end and self.tokens[idx][0] != 'RBRACKET':
                        item = self.tokens[idx][1].strip('"')
                        if item.isdigit(): item = int(item)
                        arr.append(item)  # পরে এনক্রিপশন যোগ করা যাবে
                        idx += 1
                        if idx < end and self.tokens[idx][0] == 'COMMA': idx += 1
                    self.variables[target] = arr
                    idx += 1

                # secure input (আগের)
                elif idx+3 < end and self.tokens[idx+3][0] == 'SECURE_INPUT':
                    # ... আগের secure input কোড ...

                # ... অন্যান্য (AI, crypto, math) আগের মতো ...

                else:
                    val_to_store = self.tokens[idx+3][1].strip('"')
                    if val_to_store.isdigit(): val_to_store = int(val_to_store)
                    self.variables[target] = val_to_store
                    idx += 4

            # If / ElseIf / Else
            elif kind == 'IF':
                cond_start = idx + 1
                cond_end = idx + 1
                while cond_end < end and self.tokens[cond_end][0] != 'LBRACE':
                    cond_end += 1

                # সিম্পল কন্ডিশন চেক (উন্নত করা যাবে)
                left = self.tokens[cond_start][1]
                op = self.tokens[cond_start+1][1]
                right = self.tokens[cond_start+2][1]

                left_val = self.variables.get(left, left) if left in self.variables else (int(left) if left.isdigit() else left.strip('"'))
                right_val = self.variables.get(right, right) if right in self.variables else (int(right) if right.isdigit() else right.strip('"'))

                if op == '==': condition = left_val == right_val
                elif op == '!=': condition = left_val != right_val
                elif op == '>': condition = left_val > right_val
                elif op == '<': condition = left_val < right_val
                elif op == '>=': condition = left_val >= right_val
                elif op == '<=': condition = left_val <= right_val
                else:
                    self.report_error("Syntax", "Unsupported operator", line)

                body_start = cond_end + 1
                depth = 1
                body_end = body_start
                while body_end < end and depth > 0:
                    if self.tokens[body_end][0] == 'LBRACE': depth += 1
                    if self.tokens[body_end][0] == 'RBRACE': depth -= 1
                    body_end += 1

                if condition:
                    self.execute(body_start, body_end - 1)
                    # skip else/elseif
                    idx = body_end
                    while idx < end and self.tokens[idx][0] not in ('ELSEIF', 'ELSE', 'ENDIF'):
                        idx += 1
                    if idx < end and self.tokens[idx][0] in ('ELSEIF', 'ELSE'):
                        idx += 1
                        while idx < end and self.tokens[idx][0] != 'ENDIF':
                            idx += 1
                else:
                    idx = body_end
                    while idx < end and self.tokens[idx][0] not in ('ELSEIF', 'ELSE', 'ENDIF'):
                        idx += 1

                    if idx < end and self.tokens[idx][0] == 'ELSEIF':
                        # elseif হ্যান্ডেল (রিকার্সিভ কল)
                        idx += 1
                        # আবার if লজিক চালানো যাবে
                    elif idx < end and self.tokens[idx][0] == 'ELSE':
                        idx += 1
                        else_start = idx + 1  # { skip
                        depth = 1
                        else_end = else_start
                        while else_end < end and depth > 0:
                            if self.tokens[else_end][0] == 'LBRACE': depth += 1
                            if self.tokens[else_end][0] == 'RBRACE': depth -= 1
                            else_end += 1
                        self.execute(else_start, else_end - 1)
                        idx = else_end

            # অন্যান্য (print, repeat, log ইত্যাদি) আগের মতো...

            else:
                idx += 1

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
        print(f"{CYAN}🦅 Falcon Engine v5.3 (Functions + If + Secure Array) Active{RESET}")
        print(f"Usage: {GREEN}falcon <filename>{RESET} or {YELLOW}falcon --auth{RESET}")

if __name__ == "__main__":
    main()
