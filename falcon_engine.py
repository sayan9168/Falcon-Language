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
    ('ELSEIF',           r'elseif'),
    ('ELSE',             r'else'),
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
    ('FN_DEF',           r'fn'),
    ('RETURN',           r'return'),
    ('BREAK',            r'break'),
    ('CONTINUE',         r'continue'),
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

class ReturnException(Exception):
    def __init__(self, value=None):
        self.value = value

class FalconEngine:
    def __init__(self):
        self.variables = {}
        self.constants = set()
        self.functions = {}  # {fn_name: (params_list, body_start_idx, body_end_idx)}
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

    def evaluate_condition(self, left, op, right):
        if op == '==': return left == right
        if op == '!=': return left != right
        if op == '>':  return left > right
        if op == '<':  return left < right
        if op == '>=': return left >= right
        if op == '<=': return left <= right
        return False

    def execute(self, start, end):
        idx = start
        while idx < end:
            kind, val, line = self.tokens[idx]

            # Function Definition
            if kind == 'FN_DEF':
                fn_name = self.tokens[idx+1][1]
                if fn_name in self.functions:
                    self.report_error("FuncError", f"Function '{fn_name}' already defined", line)

                params = []
                param_idx = idx + 3
                while self.tokens[param_idx][0] != 'RPAREN':
                    if self.tokens[param_idx][0] == 'ID':
                        params.append(self.tokens[param_idx][1])
                    param_idx += 1
                    if self.tokens[param_idx][0] == 'COMMA':
                        param_idx += 1

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
                ret_val = None
                if idx + 1 < end:
                    ret_token = self.tokens[idx+1]
                    if ret_token[0] == 'STRING':
                        ret_val = ret_token[1].strip('"')
                    elif ret_token[0] == 'NUMBER':
                        ret_val = int(ret_token[1])
                    elif ret_token[0] == 'ID':
                        ret_val = self.variables.get(ret_token[1])
                    else:
                        # simple expression support can be added later
                        ret_val = None
                raise ReturnException(ret_val)

            # If / Elseif / Else
            elif kind in ('IF', 'ELSEIF'):
                # Evaluate condition (simple left op right)
                left_token = self.tokens[idx+1]
                op_token = self.tokens[idx+2]
                right_token = self.tokens[idx+3]

                left = self.variables.get(left_token[1], left_token[1]) if left_token[0] == 'ID' else (
                    int(left_token[1]) if left_token[0] == 'NUMBER' else left_token[1].strip('"')
                )
                op = op_token[1]
                right = self.variables.get(right_token[1], right_token[1]) if right_token[0] == 'ID' else (
                    int(right_token[1]) if right_token[0] == 'NUMBER' else right_token[1].strip('"')
                )

                condition = self.evaluate_condition(left, op, right)

                idx += 5  # skip if/elseif condition

                if condition:
                    body_start = idx + 1  # skip {
                    depth = 1
                    body_end = body_start
                    while body_end < end and depth > 0:
                        if self.tokens[body_end][0] == 'LBRACE': depth += 1
                        if self.tokens[body_end][0] == 'RBRACE': depth -= 1
                        body_end += 1
                    self.execute(body_start, body_end)
                    # Skip to endif
                    depth = 1
                    while depth > 0:
                        idx += 1
                        if self.tokens[idx][0] in ('IF', 'ELSEIF'): depth += 1
                        if self.tokens[idx][0] == 'ENDIF': depth -= 1
                    idx += 1
                else:
                    # Skip this block
                    depth = 1
                    while depth > 0:
                        idx += 1
                        if self.tokens[idx][0] in ('IF', 'ELSEIF'): depth += 1
                        if self.tokens[idx][0] == 'RBRACE': depth -= 1
                    idx += 1  # skip }

            elif kind == 'ELSE':
                # Execute else block
                body_start = idx + 1
                depth = 1
                body_end = body_start
                while body_end < end and depth > 0:
                    if self.tokens[body_end][0] == 'LBRACE': depth += 1
                    if self.tokens[body_end][0] == 'RBRACE': depth -= 1
                    body_end += 1
                self.execute(body_start, body_end)
                idx = body_end + 1

            # Secure Let with array support
            elif kind == 'SECURE_LET':
                target = self.tokens[idx+1][1]

                if target in self.constants:
                    self.report_error("ConstError", f"Cannot reassign constant '{target}'", line)

                # Secure array support
                if idx+3 < end and self.tokens[idx+3][0] == 'LBRACKET':
                    idx += 4
                    arr = []
                    while idx < end and self.tokens[idx][0] != 'RBRACKET':
                        item_token = self.tokens[idx]
                        item = item_token[1].strip('"') if item_token[0] == 'STRING' else (
                            int(item_token[1]) if item_token[0] == 'NUMBER' else self.variables.get(item_token[1])
                        )
                        arr.append(item)
                        idx += 1
                        if self.tokens[idx][0] == 'COMMA': idx += 1
                    self.variables[target] = arr
                    idx += 1  # skip ]

                # Array access: arr[0]
                elif idx+3 < end and self.tokens[idx+3][0] == 'LBRACKET' and self.tokens[idx+5][0] == 'RBRACKET':
                    arr_name = target
                    index = int(self.tokens[idx+4][1])
                    if arr_name not in self.variables or not isinstance(self.variables[arr_name], list):
                        self.report_error("TypeError", f"'{arr_name}' is not an array", line)
                    self.variables[target] = self.variables[arr_name][index]
                    idx += 6

                # Secure Input
                elif idx+3 < end and self.tokens[idx+3][0] == 'SECURE_INPUT':
                    prompt = self.tokens[idx+5][1].strip('"')
                    input_type = "text"
                    if idx+8 < end and self.tokens[idx+6][1] == 'type' and self.tokens[idx+7][1] == '=':
                        input_type = self.tokens[idx+8][1].strip('"').lower()
                        idx += 9
                    else:
                        idx += 6

                    print(prompt, end=' ', flush=True)
                    if input_type == 'password':
                        value = getpass.getpass(prompt="")
                    else:
                        value = input()
                    self.variables[target] = value

                # ... (AI, math, crypto, default assignment code remains the same)
                # For brevity, assuming you have those blocks already

            # Function Call
            elif kind == 'ID' and idx+1 < end and self.tokens[idx+1][0] == 'LPAREN':
                fn_name = val
                if fn_name not in self.functions:
                    self.report_error("FuncError", f"Function '{fn_name}' not defined", line)

                params, body_start, body_end = self.functions[fn_name]

                # Parse arguments
                args = []
                arg_idx = idx + 2
                while arg_idx < end and self.tokens[arg_idx][0] != 'RPAREN':
                    arg_token = self.tokens[arg_idx]
                    arg_val = arg_token[1].strip('"') if arg_token[0] == 'STRING' else (
                        int(arg_token[1]) if arg_token[0] == 'NUMBER' else self.variables.get(arg_token[1])
                    )
                    args.append(arg_val)
                    arg_idx += 1
                    if self.tokens[arg_idx][0] == 'COMMA': arg_idx += 1

                # Local scope
                local_scope = dict(zip(params, args))
                old_vars = self.variables.copy()
                self.variables.update(local_scope)

                try:
                    self.execute(body_start, body_end + 1)
                except ReturnException as ret:
                    self.variables = old_vars
                    if target:  # if assigned like let x = fn()
                        self.variables[target] = ret.value
                idx = arg_idx + 1  # skip )

            # ... (rest of your code: try-catch, log, print, repeat, etc.)

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
        print(f"{CYAN}🦅 Falcon Engine v5.4 (First 4 Features Complete) Active{RESET}")
        print(f"Usage: {GREEN}falcon <filename>{RESET} or {YELLOW}falcon --auth{RESET}")

if __name__ == "__main__":
    main()
