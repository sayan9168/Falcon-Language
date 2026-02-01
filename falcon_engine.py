import base64
import re
import sys
import os

class FalconShieldCore:
    def __init__(self):
        self.memory = {}

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

            # --- ১. REPEAT LOOP ---
            if line.startswith('repeat '):
                # কতবার লুপ চলবে তা বের করা (যেমন: repeat 5 times)
                times_match = re.search(r'repeat (\d+) times', line)
                if times_match:
                    count = int(times_match.group(1))
                    # লুপের ভেতরে কোন কোডগুলো আছে তা খুঁজে বের করা
                    loop_body = []
                    i += 1
                    while i < len(lines) and lines[i].strip() != "endloop":
                        loop_body.append(lines[i])
                        i += 1
                    
                    # নির্দিষ্ট সংখ্যক বার রান করা
                    for _ in range(count):
                        self.execute_code("\n".join(loop_body))
                i += 1
                continue

            # --- ২. IF Logic ---
            if line.startswith('if '):
                condition = line[3:].strip()
                try:
                    if not eval(condition, {}, self.memory):
                        # endif না পাওয়া পর্যন্ত লাইন স্কিপ করা
                        while i < len(lines) and lines[i].strip() != "endif":
                            i += 1
                except:
                    print(f"❌ Logic Error: {condition}")
                i += 1
                continue

            # --- ৩. say কমান্ড ---
            if line.startswith('say '):
                content = re.findall(r'"(.*?)"', line)
                if content:
                    print(f"🗣️ Output: {content[0]}")
                else:
                    expr = line[4:].strip()
                    try:
                        result = eval(expr, {}, self.memory)
                        print(f"🗣️ Result: {result}")
                    except:
                        print(f"❌ Error: {expr}")

            # --- ৪. let & secure let ---
            elif line.startswith('let '):
                match = re.search(r'let (\w+)\s*=\s*(.*)', line)
                if match:
                    name, expr = match.group(1), match.group(2).strip()
                    self.memory[name] = eval(expr, {}, self.memory) if '"' not in expr else expr.replace('"', '')

            elif line.startswith('secure let '):
                match = re.search(r'secure let (\w+)\s*=\s*(.*)', line)
                if match:
                    name, expr = match.group(1), match.group(2).strip()
                    val = eval(expr, {}, self.memory) if '"' not in expr else expr.replace('"', '')
                    self.memory[name] = self.encrypt_data(val)
            
            i += 1

    def run_file(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                self.execute_code(file.read())

if __name__ == "__main__":
    engine = FalconShieldCore()
    if len(sys.argv) > 1:
        engine.run_file(sys.argv[1])
    else:
        # ডেমো লুপ কোড
        demo = """
        say "Starting loop..."
        repeat 3 times
            say "Falcon is flying!"
        endloop
        say "Loop finished."
        """
        engine.execute_code(demo)
                        
