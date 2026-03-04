#!/usr/bin/env python3
"""
Setup script to install Playwright browsers
"""

import subprocess
import sys

def main():
    print("Installing Playwright browsers...")
    print("This will download Chromium browser for web scraping.")
    print("-" * 50)
    
    try:
        # Install playwright browsers
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ Playwright browsers installed successfully!")
            print("\nYou can now run web scraping tests.")
        else:
            print("✗ Installation failed:")
            print(result.stderr)
            
    except Exception as e:
        print(f"✗ Error during installation: {e}")
        print("\nMake sure you have installed the Python dependencies:")
        print("  pip install -r requirements.txt")

if __name__ == "__main__":
    main()