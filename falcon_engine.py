import base64
import re
import sys
import os

class FalconShieldCore:
    def __init__(self):
        self.memory = {}

    def encrypt_data(self, data):
        encoded = base64.b64encode(data.encode()).decode()
        return f"FALCON_SECURE_{encoded}"

    def execute_code(self, code_text):
        lines = code_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith("//"): continue # স্কিপ খালি লাইন বা কমেন্ট
            
            # say কমান্ড
            if line.startswith('say '):
                content = re.findall(r'"(.*?)"', line)
                if content: print(f"🗣️ Output: {content[0]}")

            # secure let কমান্ড
            elif line.startswith('secure let '):
                match = re.search(r'secure let (\w+)\s*=\s*"(.*?)"', line)
                if match:
                    var_name, var_value = match.group(1), match.group(2)
                    self.memory[var_name] = self.encrypt_data(var_value)
                    print(f"🔒 [Shield-Core] Encrypted '{var_name}' in RAM.")

    # ফাইল পড়ার নতুন ফাংশন
    def run_file(self, file_path):
        if not file_path.endswith('.fcn'):
            print("❌ Error: Falcon can only fly with .fcn files!")
            return

        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                code = file.read()
                self.execute_code(code)
        else:
            print(f"❌ Error: File '{file_path}' not found.")

# --- CLI ইন্টিগ্রেশন ---
if __name__ == "__main__":
    engine = FalconShieldCore()
    
    # যদি কমান্ড লাইন থেকে ফাইল দেওয়া হয় (যেমন: python falcon_engine.py test.fcn)
    if len(sys.argv) > 1:
        engine.run_file(sys.argv[1])
    else:
        # কোনো ফাইল না দিলে ইন্টারঅ্যাক্টিভ মোড
        print("🦅 Falcon Engine v1.0 Ready. No file provided.")
                    
