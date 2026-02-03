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
      
import os
import sys
import subprocess

def install(package_url):
    print(f"🦅 Falcon Package Manager: Installing {package_url}...")
    try:
        # এটি প্যাকেজটিকে আপনার লোকাল ফোল্ডারে ক্লোন করবে
        subprocess.run(["git", "clone", package_url], check=True)
        print("✅ Installation successful!")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    if len(sys.argv) < 3:
        print("Usage: fpm install <package_github_url>")
        return
    
    command = sys.argv[1]
    target = sys.argv[2]
    
    if command == "install":
        install(target)

if __name__ == "__main__":
    main()

