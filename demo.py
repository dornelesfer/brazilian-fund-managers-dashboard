#!/usr/bin/env python3
"""
Demo script to show the Streamlit app features
"""

import subprocess
import sys
import webbrowser
import time
import threading

def open_browser():
    """Open browser after a short delay"""
    time.sleep(3)
    webbrowser.open('http://localhost:8501')

def main():
    print("🇧🇷 Brazilian Fund Managers - Offshore Assets Dashboard")
    print("=" * 60)
    print()
    print("🚀 Starting the interactive dashboard...")
    print("📊 Features available:")
    print("   • Filter by state, city, and date")
    print("   • Interactive charts and visualizations")
    print("   • Sortable tables with detailed information")
    print("   • Geographic distribution analysis")
    print("   • Export filtered data to CSV")
    print()
    print("🌐 The dashboard will open in your browser at: http://localhost:8501")
    print("⏹️  Press Ctrl+C to stop the server")
    print()
    
    # Start browser opening in background
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        # Run Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ])
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped. Thank you!")

if __name__ == "__main__":
    main()
