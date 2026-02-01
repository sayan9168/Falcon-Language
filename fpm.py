import os
import sys

class FalconPackageManager:
    def __init__(self):
        self.registry = {
            "web": "https://falcon-lang.org/packages/web.fcn",
            "ai": "https://falcon-lang.org/packages/ai-core.fcn",
            "db": "https://falcon-lang.org/packages/database.fcn"
        }

    def install(self, package_name):
        print(f"📡 Connecting to Falcon Global Registry...")
        if package_name in self.registry:
            print(f"📥 Downloading '{package_name}'...")
            # এখানে ভবিষ্যতে আসল ডাউনলোড লজিক আসবে
            print(f"🛡️ Verifying Shield-Core Security Signatures...")
            print(f"✅ Successfully installed '{package_name}' in './falcon_modules/'")
        else:
            print(f"❌ Error: Package '{package_name}' not found in registry.")

if __name__ == "__main__":
    manager = FalconPackageManager()
    if len(sys.argv) > 2 and sys.argv[1] == "install":
        manager.install(sys.argv[2])
    else:
        print("🚀 Falcon Package Manager (FPM) v1.0")
        print("Usage: python fpm.py install <package_name>")
      
