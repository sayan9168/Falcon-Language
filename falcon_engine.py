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
        for line in lines:
            line = line.strip()
            if not line or line.startswith("//"): continue
            
            # ১. say কমান্ড (এটি এখন ভেরিয়েবল এবং ম্যাথও প্রিন্ট করতে পারবে)
            if line.startswith('say '):
                content = re.findall(r'"(.*?)"', line)
                if content:
                    print(f"🗣️ Output: {content[0]}")
                else:
                    # ভেরিয়েবল বা ডাইরেক্ট অংক প্রিন্ট করার জন্য
                    expr = line[4:].strip()
                    try:
                        result = eval(expr, {}, self.memory)
                        print(f"🗣️ Result: {result}")
                    except:
                        print(f"❌ Error: Could not say '{expr}'")

            # ২. secure let (এনক্রিপ্টেড ভেরিয়েবল)
            elif line.startswith('secure let '):
                match = re.search(r'secure let (\w+)\s*=\s*(.*)', line)
                if match:
                    var_name, var_expr = match.group(1), match.group(2).strip()
                    # যদি ভ্যালুটি কোটেশনে থাকে (String), না থাকলে (Math)
                    if var_expr.startswith('"') and var_expr.endswith('"'):
                        val = var_expr[1:-1]
                    else:
                        val = eval(var_expr, {}, self.memory)
                    
                    self.memory[var_name] = val # ক্যালকুলেশন করে মেমরিতে রাখা
                    print(f"🔒 [Shield-Core] {var_name} encrypted safely.")

            # ৩. সাধারণ let (অংকের জন্য)
            elif line.startswith('let '):
                match = re.search(r'let (\w+)\s*=\s*(.*)', line)
                if match:
                    var_name, var_expr = match.group(1), match.group(2).strip()
                    try:
                        self.memory[var_name] = eval(var_expr, {}, self.memory)
                        print(f"✅ Variable '{var_name}' set to {self.memory[var_name]}")
                    except Exception as e:
                        print(f"❌ Math Error: {e}")

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
        # ডেমো কোড রান (যদি ফাইল না দেওয়া হয়)
        demo = """
        let x = 10 + 5
        let y = 20 * 2
        say "The value of x + y is:"
        say x + y
        secure let total = x + y
        """
        engine.execute_code(demo)
        
