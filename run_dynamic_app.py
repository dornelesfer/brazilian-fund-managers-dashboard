#!/usr/bin/env python3
"""
Launcher script for the dynamic Streamlit app
"""

import subprocess
import sys
import os

def check_requirements():
    """Check if required packages are installed"""
    try:
        import streamlit
        import pandas
        import plotly
        import requests
        return True
    except ImportError:
        return False

def install_requirements():
    """Install required packages"""
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def run_streamlit():
    """Run the Streamlit app"""
    print("Starting dynamic Streamlit app...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "streamlit_app_dynamic.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ])

def main():
    """Main function"""
    print("🚀 Brazilian Fund Managers - Dynamic Offshore Assets Dashboard")
    print("=" * 70)
    
    # Check if static data exists
    if not os.path.exists("registro_fundo.csv") or not os.path.exists("cad_adm_cart_pj.csv"):
        print("❌ Required static data files not found!")
        print("Please ensure the following files are available:")
        print("  - registro_fundo.csv")
        print("  - cad_adm_cart_pj.csv")
        print("\nYou can download them using:")
        print("  python3 update_analysis.py")
        return
    
    # Check requirements
    if not check_requirements():
        print("📦 Installing required packages...")
        install_requirements()
    
    # Run the app
    run_streamlit()

if __name__ == "__main__":
    main()
