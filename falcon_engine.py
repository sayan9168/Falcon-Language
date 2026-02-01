import base64
import re

class FalconShieldCore:
    def __init__(self):
        self.memory = {}
        self.plugins = []

    # --- ১. মেমরি এনক্রিপশন লজিক ---
    def encrypt_data(self, data):
        encoded = base64.b64encode(data.encode()).decode()
        return f"FALCON_SECURE_{encoded}"

    # --- ২. দ্য পার্সার (The Parser) ---
    def execute_code(self, code_text):
        print("🚀 Falcon Engine: Executing...")
        
        # প্রতি লাইন ধরে কোড পড়া
        lines = code_text.split('\n')
        for line in lines:
            line = line.strip()
            
            # ১. say কমান্ড হ্যান্ডেল করা
            if line.startswith('say '):
                # ইনভার্টেড কমার ভেতরের টেক্সট বের করা
                content = re.findall(r'"(.*?)"', line)
                if content:
                    print(f"🗣️ Output: {content[0]}")

            # ২. secure let কমান্ড হ্যান্ডেল করা
            elif line.startswith('secure let '):
                # ভেরিয়েবল নাম এবং ভ্যালু আলাদা করা
                match = re.search(r'secure let (\w+)\s*=\s*"(.*?)"', line)
                if match:
                    var_name = match.group(1)
                    var_value = match.group(2)
                    encrypted = self.encrypt_data(var_value)
                    self.memory[var_name] = encrypted
                    print(f"🔒 [Shield-Core] Encrypted '{var_name}' in RAM.")

    def load_plugin(self, plugin_name):
        print(f"🔌 Loading tool: {plugin_name}...")
        self.plugins.append(plugin_name)
        print(f"✅ {plugin_name} is ready.")

# --- ৩. রিয়েল টাইম টেস্ট ---
if __name__ == "__main__":
    engine = FalconShieldCore()
    
    # এটি একটি ডেমো ফ্যালকন কোড যা আপনার ইঞ্জিন এখন পড়তে পারবে
    falcon_code = """
    secure let vault = "FALCON_SECRET_2026"
    say "Hello from the new Parser!"
    say "Data is now being protected by Shield-Core."
    """
    
    engine.execute_code(falcon_code)
    
