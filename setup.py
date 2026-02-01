import os
import sys

def install_falcon():
    # Eta terminal-e 'falcon' command-ti set korar ekti simple simulation
    print("🚀 Installing Falcon CLI on your system...")
    
    # Path setup (Simulation)
    current_dir = os.getcwd()
    engine_path = os.path.join(current_dir, "falcon_engine.py")
    
    if os.path.exists(engine_path):
        print(f"✅ Found Falcon Engine at: {engine_path}")
        print("🔗 Linking 'falcon' command to FalconShieldCore...")
        print("\n🎉 Success! You can now run Falcon using: 'falcon run <filename>'")
    else:
        print("❌ Error: falcon_engine.py not found. Please run this in the root directory.")

if __name__ == "__main__":
    install_falcon()
