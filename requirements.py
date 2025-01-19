import subprocess
import sys

def install_requirements():
    requirements = [
        'customtkinter',
        'yt-dlp',
        'pygame',
        'pystray',
        'Pillow',
        'urllib3'
    ]
    
    print("Installing requirements...")
    for package in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"Successfully installed {package}")
        except subprocess.CalledProcessError:
            print(f"Failed to install {package}")
            
    print("\nAll requirements installed!")

if __name__ == "__main__":
    install_requirements()