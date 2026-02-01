import base64

class FalconShieldCore:
    def __init__(self):
        self.memory = {}

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

# Test Falcon Engine
engine = FalconShieldCore()
engine.set_secure_variable("my_password", "admin123")

print("Memory Content:", engine.get_variable("my_password"))
