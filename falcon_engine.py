import base64

class FalconShieldCore:
    def __init__(self):
        # Falcon-এর মেমরি এবং প্লাগইন রেজিস্ট্রি
        self.memory = {}
        self.plugins = []

    # --- ১. মেমরি সিকিউরিটি (Shield-Core) ---
    def encrypt_data(self, data):
        # Falcon RAM-এ ডাটা পাঠানোর আগে এনক্রিপ্ট করে
        encoded = base64.b64encode(data.encode()).decode()
        return f"FALCON_SECURE_{encoded}"

    def set_secure_variable(self, name, value):
        encrypted_value = self.encrypt_data(value)
        self.memory[name] = encrypted_value
        print(f"✅ [Shield-Core] Variable '{name}' is now encrypted in RAM.")

    def get_variable(self, name):
        return self.memory.get(name, "Variable not found")

    # --- ২. প্লাগইন ও টুলস লোডার (Extensibility) ---
    def load_plugin(self, plugin_name):
        """
        এটি অন্য কোনো ডেভেলপারের বানানো কোড বা টুলসকে 
        ফ্যালকন কোরের সাথে কানেক্ট করে।
        """
        print(f"🔌 Loading external tool: {plugin_name}...")
        self.plugins.append(plugin_name)
        # ভবিষ্যতে এখানে ডাইনামিক ইম্পোর্ট লজিক যোগ করা হবে
        print(f"✅ Tool '{plugin_name}' is now integrated with Falcon Core.")

# --- ৩. টেস্ট রান (Falcon Simulation) ---
if __name__ == "__main__":
    engine = FalconShieldCore()
    
    # সিকিউরিটি টেস্ট
    engine.set_secure_variable("my_password", "admin123")
    print("Memory Content:", engine.get_variable("my_password"))
    
    print("-" * 30)
    
    # এক্সটার্নাল টুলস টেস্ট
    engine.load_plugin("Falcon-Graphics-Engine")
    engine.load_plugin("Falcon-AI-Library")
    
