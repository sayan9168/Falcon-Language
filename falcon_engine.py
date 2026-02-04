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

class BreakException(Exception):
    pass

class ContinueException(Exception):
    pass

class FalconEngine:
    def __init__(self):
        self.variables = {}
        self.constants = set()
        self.functions = {}  # {fn_name: (params, body_start, body_end)}
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

    def evaluate_expression(self, left_token, op_token, right_token):
        left = self.get_value(left_token)
        right = self.get_value(right_token)
        op = op_token[1]

        if op == '==': return left == right
        if op == '!=': return left != right
        if op == '>':  return left > right
        if op == '<':  return left < right
        if op == '>=': return left >= right
        if op == '<=': return left <= right
        return False

    def get_value(self, token):
        kind, value = token[0], token[1]
        if kind == 'STRING': return value.strip('"')
        if kind == 'NUMBER': return int(value)
        if kind == 'ID': return self.variables.get(value, None)
        return value

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
                p_idx = idx + 3  # after fn name (
                while self.tokens[p_idx][0] != 'RPAREN':
                    if self.tokens[p_idx][0] == 'ID':
                        params.append(self.tokens[p_idx][1])
                    p_idx += 1
                    if self.tokens[p_idx][0] == 'COMMA': p_idx += 1

                body_start = p_idx + 2  # skip ) {
                depth = 1
                body_end = body_start
                while body_end < end and depth > 0:
                    if self.tokens[body_end][0] == 'LBRACE': depth += 1
                    if self.tokens[body_end][0] == 'RBRACE': depth -= 1
                    body_end += 1

                self.functions[fn_name] = (params, body_start, body_end - 1)
                idx = body_end + 1
                continue

            # Return
            elif kind == 'RETURN':
                ret_val = self.get_value(self.tokens[idx+1]) if idx+1 < end else None
                raise ReturnException(ret_val)

            # Break / Continue
            elif kind == 'BREAK':
                raise BreakException()
            elif kind == 'CONTINUE':
                raise ContinueException()

            # If / Elseif / Else
            elif kind in ('IF', 'ELSEIF'):
                left_t = self.tokens[idx+1]
                op_t = self.tokens[idx+2]
                right_t = self.tokens[idx+3]

                condition = self.evaluate_expression(left_t, op_t, right_t)

                idx += 5  # skip if/elseif condition

                if condition:
                    body_start = idx + 1
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
                        if self.tokens[idx][0] in ('IF', 'ELSEIF', 'ELSE'): depth += 1
                        if self.tokens[idx][0] == 'ENDIF': depth -= 1
                    idx += 1
                else:
                    depth = 1
                    while depth > 0:
                        idx += 1
                        if self.tokens[idx][0] in ('IF', 'ELSEIF'): depth += 1
                        if self.tokens[idx][0] == 'RBRACE': depth -= 1
                    idx += 1

            elif kind == 'ELSE':
                body_start = idx + 1
                depth = 1
                body_end = body_start
                while body_end < end and depth > 0:
                    if self.tokens[body_end][0] == 'LBRACE': depth += 1
                    if self.tokens[body_end][0] == 'RBRACE': depth -= 1
                    body_end += 1
                self.execute(body_start, body_end)
                idx = body_end + 1

            # Secure Let (with array)
            elif kind == 'SECURE_LET':
                target = self.tokens[idx+1][1]

                if target in self.constants:
                    self.report_error("ConstError", f"Cannot reassign constant '{target}'", line)

                # Secure array
                if idx+3 < end and self.tokens[idx+3][0] == 'LBRACKET':
                    idx += 4
                    arr = []
                    while idx < end and self.tokens[idx][0] != 'RBRACKET':
                        item_t = self.tokens[idx]
                        item = self.get_value(item_t)
                        arr.append(item)
                        idx += 1
                        if self.tokens[idx][0] == 'COMMA': idx += 1
                    self.variables[target] = arr
                    idx += 1
                else:
                    # Default
                    val_to_store = self.get_value(self.tokens[idx+3])
                    self.variables[target] = val_to_store
                    idx += 4

            # Array access
            elif kind == 'ID' and idx+1 < end and self.tokens[idx+1][0] == 'LBRACKET':
                arr_name = val
                index = int(self.tokens[idx+2][1])
                if arr_name not in self.variables or not isinstance(self.variables[arr_name], list):
                    self.report_error("TypeError", f"'{arr_name}' is not an array", line)
                self.variables[target] = self.variables[arr_name][index]
                idx += 4  # skip ]

            # ... (আগের AI, crypto, input, log, print, repeat ব্লকগুলো এখানে রাখো)

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
        print(f"{CYAN}🦅 Falcon Engine v5.4 (All First 4 Features Complete) Active{RESET}")
        print(f"Usage: {GREEN}falcon <filename>{RESET} or {YELLOW}falcon --auth{RESET}")

if __name__ == "__main__":
    main()
