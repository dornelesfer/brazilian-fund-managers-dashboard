#!/usr/bin/env python3
"""
Launcher script for the Streamlit app
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
        return True
    except ImportError:
        return False

def install_requirements():
    """Install required packages"""
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def run_streamlit():
    """Run the Streamlit app"""
    print("Starting Streamlit app...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ])

def main():
    """Main function"""
    print("🚀 Brazilian Fund Managers - Offshore Assets Dashboard")
    print("=" * 60)
    
    # Check if data exists
    if not os.path.exists("offshore_managers_analysis.csv"):
        print("❌ Data file not found!")
        print("Please run 'python3 analyze_offshore_managers.py' first to generate the data.")
        return
    
    # Check requirements
    if not check_requirements():
        print("📦 Installing required packages...")
        install_requirements()
    
    # Run the app
    run_streamlit()

if __name__ == "__main__":
    main()
