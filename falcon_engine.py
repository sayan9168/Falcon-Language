import base64
import re
import sys
import os

class FalconShieldCore:
    def __init__(self):
        self.memory = {}
        self.version = "1.0.2"

    def encrypt_data(self, data):
        encoded = base64.b64encode(str(data).encode()).decode()
        return f"FALCON_SECURE_{encoded}"

    def execute_code(self, code_text):
        lines = code_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("//"): 
                i += 1
                continue

            try:
                # --- 1. ASK Command (User Input) ---
                if line.startswith('ask '):
                    match = re.search(r'ask (\w+)\s*=\s*"(.*?)"', line)
                    if match:
                        var_name, prompt = match.group(1), match.group(2)
                        user_val = input(f"❓ {prompt} ")
                        self.memory[var_name] = user_val
                    i += 1
                    continue

                # --- 2. REPEAT Loop ---
                if line.startswith('repeat '):
                    times_match = re.search(r'repeat (\d+) times', line)
                    if times_match:
                        count = int(times_match.group(1))
                        loop_body = []
                        i += 1
                        while i < len(lines) and lines[i].strip() != "endloop":
                            loop_body.append(lines[i])
                            i += 1
                        for _ in range(count):
                            self.execute_code("\n".join(loop_body))
                    i += 1
                    continue

                # --- 3. IF Logic ---
                if line.startswith('if '):
                    condition = line[3:].strip()
                    if not eval(condition, {}, self.memory):
                        while i < len(lines) and lines[i].strip() != "endif":
                            i += 1
                    i += 1
                    continue

                # --- 4. SAY Command ---
                if line.startswith('say '):
                    content = re.findall(r'"(.*?)"', line)
                    if content:
                        print(f"🗣️ Output: {content[0]}")
                    else:
                        expr = line[4:].strip()
                        print(f"🗣️ Result: {eval(expr, {}, self.memory)}")

                # --- 5. Variable Assignment (LET) ---
                elif line.startswith('let '):
                    match = re.search(r'let (\w+)\s*=\s*(.*)', line)
                    if match:
                        name, expr = match.group(1), match.group(2).strip()
                        self.memory[name] = eval(expr, {}, self.memory) if '"' not in expr else expr.replace('"', '')

                # --- 6. SECURE LET ---
                elif line.startswith('secure let '):
                    match = re.search(r'secure let (\w+)\s*=\s*(.*)', line)
                    if match:
                        name, expr = match.group(1), match.group(2).strip()
                        val = eval(expr, {}, self.memory) if '"' not in expr else expr.replace('"', '')
                        self.memory[name] = self.encrypt_data(val)

            except Exception as e:
                print(f"🚨 Falcon Error at line {i+1}: {e}")
            
            i += 1

    def run_file(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                self.execute_code(file.read())
        else:
            print(f"❌ File '{file_path}' not found.")

if __name__ == "__main__":
    engine = FalconShieldCore()
    if len(sys.argv) > 1:
        engine.run_file(sys.argv[1])
    else:
        # Final Test Demo
        demo = """
        say "--- Welcome to Falcon v1.0.2 ---"
        ask name = "What is your name, pilot?"
        say "Hello, " + name
        let health = 100
        if health > 50
            say "Falcon Shield is strong!"
        endif
        """
        engine.execute_code(demo)
        
