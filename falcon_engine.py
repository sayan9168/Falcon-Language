import sys
import re
import os
import json
from google import genai

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
    ('CRYPTO_HASH',      r'crypto\.hash'),         # নতুন
    ('CRYPTO_ENCRYPT',   r'crypto\.encrypt'),      # নতুন
    ('CRYPTO_DECRYPT',   r'crypto\.decrypt'),      # নতুন
    ('LOG',              r'log'),                  # নতুন
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

            # 1. Module System
            if kind == 'IMPORT':
                module_name = self.tokens[idx+1][1].strip('"') + ".fcn"
                if os.path.exists(module_name):
                    sub_engine = FalconEngine()
                    sub_engine.variables = self.variables
                    sub_engine.constants = self.constants
                    sub_engine.run(module_name)
                    self.variables.update(sub_engine.variables)
                    self.constants.update(sub_engine.constants)
                else:
                    self.report_error("Import", f"Module '{module_name}' missing", line)
                idx += 2

            # 2. Secure Const
            elif kind == 'SECURE_CONST':
                target = self.tokens[idx+1][1]
                if target in self.variables or target in self.constants:
                    self.report_error("ConstError", f"Cannot redeclare constant '{target}'", line)

                val_token = self.tokens[idx+3]
                val = val_token[1].strip('"')

                if val.isdigit():
                    val = int(val)
                elif val_token[0] == 'STRING':
                    val = val.strip('"')
                else:
                    val = self.variables.get(val, val)

                self.variables[target] = val
                self.constants.add(target)
                idx += 4

            # 3. Secure Let (Variable / Dict / AI / List / Math / Crypto)
            elif kind == 'SECURE_LET':
                target = self.tokens[idx+1][1]

                if target in self.constants:
                    self.report_error("ConstError", f"Cannot reassign constant '{target}'", line)

                # List support
                if idx+3 < end and self.tokens[idx+3][0] == 'LBRACKET':
                    idx += 4
                    arr = []
                    while idx < end and self.tokens[idx][0] != 'RBRACKET':
                        item = self.tokens[idx][1].strip('"')
                        if item.isdigit(): item = int(item)
                        arr.append(item)
                        idx += 1
                        if idx < end and self.tokens[idx][0] == 'COMMA': idx += 1
                    self.variables[target] = arr
                    idx += 1

                # Dictionary support
                elif idx+3 < end and self.tokens[idx+3][0] == 'LBRACE':
                    idx += 4
                    obj = {}
                    while idx < end and self.tokens[idx][0] != 'RBRACE':
                        k = self.tokens[idx][1].strip('"')
                        idx += 2
                        v = self.tokens[idx][1].strip('"')
                        if v.isdigit(): v = int(v)
                        obj[k] = v
                        idx += 1
                        if idx < end and self.tokens[idx][0] == 'COMMA': idx += 1
                    self.variables[target] = obj
                    idx += 1

                # AI Features
                elif idx+3 < end and self.tokens[idx+3][0] in ('AI_CALL', 'AI_GENERATE_CODE', 'AI_EXPLAIN', 'AI_REFACTOR'):
                    ai_type = self.tokens[idx+3][0]
                    prompt_raw = self.tokens[idx+5][1].strip('"') if idx+5 < end else ""

                    if ai_type == 'AI_CALL':
                        full_prompt = prompt_raw
                    elif ai_type == 'AI_GENERATE_CODE':
                        full_prompt = (
                            "You are an expert Falcon Language programmer. "
                            "Generate clean, secure, and correct Falcon (.fcn) code ONLY. "
                            "No explanations, no markdown, no comments unless explicitly asked. "
                            "User request: " + prompt_raw
                        )
                    elif ai_type == 'AI_EXPLAIN':
                        full_prompt = (
                            "Explain the following code/text in clear, concise Bengali or English: "
                            + prompt_raw
                        )
                    elif ai_type == 'AI_REFACTOR':
                        full_prompt = (
                            "Refactor and improve the following code to make it more secure, readable, and efficient. "
                            "Return only the improved Falcon code. Instruction: " + prompt_raw
                        )

                    result = self._call_gemini(full_prompt, line)
                    self.variables[target] = result
                    idx += 7

                # Math Support
                elif idx + 4 < end and self.tokens[idx+4][0] == 'OP':
                    v1_str = self.tokens[idx+3][1]
                    v2_str = self.tokens[idx+5][1]
                    v1 = self.variables.get(v1_str, int(v1_str) if v1_str.isdigit() else v1_str)
                    v2 = self.variables.get(v2_str, int(v2_str) if v2_str.isdigit() else v2_str)
                    op = self.tokens[idx+4][1]
                    if op == '+':
                        res = v1 + v2 if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) else str(v1) + str(v2)
                    elif op == '-': res = v1 - v2
                    elif op == '*': res = v1 * v2
                    elif op == '/': res = v1 / v2 if v2 != 0 else "Division by zero"
                    self.variables[target] = res
                    idx += 6

                # Crypto Functions
                elif idx+3 < end and self.tokens[idx+3][0] in ('CRYPTO_HASH', 'CRYPTO_ENCRYPT', 'CRYPTO_DECRYPT'):
                    crypto_type = self.tokens[idx+3][0]

                    if crypto_type == 'CRYPTO_HASH':
                        if idx+5 >= end or self.tokens[idx+5][0] != 'STRING':
                            self.report_error("Syntax", "crypto.hash expects a string", line)
                        text = self.tokens[idx+5][1].strip('"')
                        import hashlib
                        hashed = hashlib.sha256(text.encode()).hexdigest()
                        self.variables[target] = hashed
                        idx += 6

                    elif crypto_type in ('CRYPTO_ENCRYPT', 'CRYPTO_DECRYPT'):
                        if idx+7 >= end or self.tokens[idx+5][0] != 'STRING' or self.tokens[idx+7][0] != 'STRING':
                            self.report_error("Syntax", "crypto.encrypt/decrypt expects text and key", line)

                        text = self.tokens[idx+5][1].strip('"')
                        key = self.tokens[idx+7][1].strip('"')

                        # Simple XOR for demo (replace with real crypto later)
                        def xor_encrypt_decrypt(data, key):
                            key = (key * (len(data) // len(key) + 1))[:len(data)]
                            return ''.join(chr(ord(c) ^ ord(k)) for c, k in zip(data, key))

                        if crypto_type == 'CRYPTO_ENCRYPT':
                            result = xor_encrypt_decrypt(text, key)
                        else:
                            result = xor_encrypt_decrypt(text, key)  # XOR is symmetric

                        self.variables[target] = result
                        idx += 8

                else:
                    val_to_store = self.tokens[idx+3][1].strip('"')
                    if val_to_store.isdigit(): val_to_store = int(val_to_store)
                    self.variables[target] = val_to_store
                    idx += 4

            # 4. Try-Catch Block
            elif kind == 'TRY':
                try_start = idx + 1
                catch_start = None
                endtry_pos = None
                depth = 1

                i = try_start
                while i < end and depth > 0:
                    if self.tokens[i][0] == 'TRY':
                        depth += 1
                    elif self.tokens[i][0] == 'ENDTRY':
                        depth -= 1
                        if depth == 0:
                            endtry_pos = i
                    elif self.tokens[i][0] == 'CATCH' and depth == 1:
                        catch_start = i
                    i += 1

                if endtry_pos is None:
                    self.report_error("Syntax", "Missing 'endtry'", line)

                try:
                    self.execute(try_start, catch_start if catch_start else endtry_pos)
                except Exception as e:
                    error_msg = str(e)
                    if catch_start is not None:
                        cond_idx = catch_start + 1
                        catch_condition = ""
                        if cond_idx < end and self.tokens[cond_idx][0] == 'STRING':
                            catch_condition = self.tokens[cond_idx][1].strip('"')
                            catch_body_start = cond_idx + 1
                        else:
                            catch_body_start = catch_start + 1

                        if not catch_condition or catch_condition in error_msg:
                            self.execute(catch_body_start, endtry_pos)

                idx = endtry_pos + 1

            # 5. Logging
            elif kind == 'LOG':
                if idx+2 >= end or self.tokens[idx+2][0] != 'STRING':
                    self.report_error("Syntax", "log expects a string message", line)

                message = self.tokens[idx+2][1].strip('"')
                level = "info"

                if idx+5 < end and self.tokens[idx+3][1] == 'level' and self.tokens[idx+4][1] == '=':
                    level_token = self.tokens[idx+5][1].strip('"').lower()
                    if level_token in ['info', 'warn', 'error', 'debug']:
                        level = level_token
                    idx += 6
                else:
                    idx += 3

                colors = {
                    'info': GREEN,
                    'warn': YELLOW,
                    'error': RED,
                    'debug': CYAN
                }
                color = colors.get(level, RESET)
                print(f"{color}[{level.upper()}] {message}{RESET}")

            # 6. Print Output
            elif kind == 'PRINT':
                content = self.tokens[idx+2][1].strip('"')
                data = self.variables.get(content, content)
                print(f"{GREEN}🦅 [Falcon]:{RESET} {data}")
                idx += 4

            # 7. Repeat Loops
            elif kind == 'REPEAT':
                times = int(self.tokens[idx+1][1])
                loop_start = idx + 2
                depth, loop_end = 1, loop_start
                while depth > 0 and loop_end < end:
                    if self.tokens[loop_end][0] == 'REPEAT': depth += 1
                    if self.tokens[loop_end][0] == 'ENDREPEAT': depth -= 1
                    loop_end += 1
                for _ in range(times):
                    self.execute(loop_start, loop_end - 1)
                idx = loop_end

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
        print(f"{CYAN}🦅 Falcon Engine v5.1 (Crypto + Logging) Active{RESET}")
        print(f"Usage: {GREEN}falcon <filename>{RESET} or {YELLOW}falcon --auth{RESET}")

if __name__ == "__main__":
    main()
