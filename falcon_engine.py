import sys
import re
import os
import json
from google import genai
import getpass
import hashlib

# টার্মিনাল কালার কোড
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

# --- TOKEN DEFINITIONS ---
TOKEN_TYPES = [
    ('COMMENT',          r'//.*'),
    ('IMPORT',           r'import'),
    ('SECURE_LET',       r'secure let'),
    ('SECURE_CONST',     r'secure const'),
    ('TRY',              r'try'),
    ('CATCH',            r'catch'),
    ('ENDTRY',           r'endtry'),
    ('IF',               r'if'),
    ('ELSEIF',           r'elseif'),           # নতুন
    ('ELSE',             r'else'),             # নতুন
    ('ENDIF',            r'endif'),
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
    ('FN_DEF',           r'fn'),               # নতুন - function definition
    ('RETURN',           r'return'),           # নতুন
    ('BREAK',            r'break'),            # নতুন
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
        self.functions = {}  # নতুন: ফাংশন স্টোর করার জন্য {name: (params, start_idx, end_idx)}
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
            else:
                self.tokens.append((kind, value, current_line))

    def _call_gemini(self, prompt, line):
        if not self.client:
            self.report_error("Auth", "AI Key not found. Run 'falcon --auth' first.", line)

        print(f"{CYAN}🧠 [Falcon AI] Querying Gemini...{RESET}")
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
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
                if fn_name in self.functions:
                    self.report_error("FuncError", f"Function '{fn_name}' already defined", line)
                
                # Parse parameters
                params = []
                param_idx = idx + 3  # after fn name (
                while self.tokens[param_idx][0] != 'RPAREN':
                    if self.tokens[param_idx][0] == 'ID':
                        params.append(self.tokens[param_idx][1])
                    param_idx += 1
                    if self.tokens[param_idx][0] == 'COMMA': param_idx += 1
                
                # Find body { ... }
                body_start = param_idx + 2  # skip ) {
                depth = 1
                body_end = body_start
                while body_end < end and depth > 0:
                    if self.tokens[body_end][0] == 'LBRACE': depth += 1
                    if self.tokens[body_end][0] == 'RBRACE': depth -= 1
                    body_end += 1
                
                self.functions[fn_name] = (params, body_start, body_end - 1)
                idx = body_end + 1
                continue

            # Return statement
            elif kind == 'RETURN':
                # Find value
                if idx + 1 < end:
                    ret_val_token = self.tokens[idx+1]
                    if ret_val_token[0] == 'STRING':
                        ret_val = ret_val_token[1].strip('"')
                    elif ret_val_token[0] == 'NUMBER':
                        ret_val = int(ret_val_token[1])
                    elif ret_val_token[0] == 'ID':
                        ret_val = self.variables.get(ret_val_token[1], ret_val_token[1])
                    else:
                        ret_val = None
                    # Raise exception to return value (simple way)
                    raise ReturnException(ret_val)
                idx += 2
                continue

            # If / Elseif / Else
            elif kind == 'IF':
                condition = True  # Simple placeholder - add real comparison later
                if not condition:
                    # Skip to else/elseif or endif
                    depth = 1
                    while depth > 0:
                        idx += 1
                        if self.tokens[idx][0] in ('IF', 'ELSEIF'): depth += 1
                        if self.tokens[idx][0] == 'ENDIF': depth -= 1
                    idx += 1
                    continue
                
                idx += 1  # skip if
                body_start = idx
                depth = 1
                body_end = body_start
                while depth > 0 and body_end < end:
                    if self.tokens[body_end][0] == 'LBRACE': depth += 1
                    if self.tokens[body_end][0] == 'RBRACE': depth -= 1
                    body_end += 1
                self.execute(body_start, body_end)
                idx = body_end + 1

            # Secure Input (already there, kept for completeness)
            elif kind == 'SECURE_LET':
                target = self.tokens[idx+1][1]

                if target in self.constants:
                    self.report_error("ConstError", f"Cannot reassign constant '{target}'", line)

                # ... (list, dict, AI, math, crypto code remains the same)

                # Secure Input
                elif idx+3 < end and self.tokens[idx+3][0] == 'SECURE_INPUT':
                    if idx+5 >= end or self.tokens[idx+5][0] != 'STRING':
                        self.report_error("Syntax", "secure input expects a prompt string", line)

                    prompt = self.tokens[idx+5][1].strip('"')
                    input_type = "text"

                    if idx+8 < end and self.tokens[idx+6][1] == 'type' and self.tokens[idx+7][1] == '=':
                        type_token = self.tokens[idx+8][1].strip('"').lower()
                        if type_token in ['text', 'password']:
                            input_type = type_token
                        idx += 9
                    else:
                        idx += 6

                    print(prompt, end=' ', flush=True)

                    if input_type == 'password':
                        value = getpass.getpass(prompt="")
                    else:
                        value = input()

                    self.variables[target] = value

                else:
                    # Default assignment
                    val_to_store = self.tokens[idx+3][1].strip('"')
                    if val_to_store.isdigit(): val_to_store = int(val_to_store)
                    self.variables[target] = val_to_store
                    idx += 4

            # Function Call
            elif kind == 'ID' and idx+1 < end and self.tokens[idx+1][0] == 'LPAREN':
                fn_name = val
                if fn_name not in self.functions:
                    self.report_error("FuncError", f"Function '{fn_name}' not defined", line)
                
                params, body_start, body_end = self.functions[fn_name]
                
                # Parse arguments
                args = []
                arg_idx = idx + 2
                while self.tokens[arg_idx][0] != 'RPAREN':
                    if self.tokens[arg_idx][0] == 'STRING':
                        args.append(self.tokens[arg_idx][1].strip('"'))
                    elif self.tokens[arg_idx][0] == 'NUMBER':
                        args.append(int(self.tokens[arg_idx][1]))
                    elif self.tokens[arg_idx][0] == 'ID':
                        args.append(self.variables.get(self.tokens[arg_idx][1]))
                    arg_idx += 1
                    if self.tokens[arg_idx][0] == 'COMMA': arg_idx += 1
                
                # Execute function body with local scope
                local_vars = {}
                for param, arg in zip(params, args):
                    local_vars[param] = arg
                
                old_vars = self.variables.copy()
                self.variables.update(local_vars)
                
                try:
                    self.execute(body_start, body_end + 1)
                except ReturnException as e:
                    self.variables = old_vars
                    self.variables[target] = e.value if target else e.value
                idx = arg_idx + 1  # skip )

            # ... (other blocks like try-catch, log, print, repeat remain the same)

            else:
                idx += 1

class ReturnException(Exception):
    def __init__(self, value=None):
        self.value = value

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
