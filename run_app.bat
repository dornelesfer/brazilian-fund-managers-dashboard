@echo off
echo Starting Brazilian Fund Managers - Offshore Assets Dashboard
echo ============================================================

REM Check if data exists
if not exist "offshore_managers_analysis.csv" (
    echo ERROR: Data file not found!
    echo Please run 'python analyze_offshore_managers.py' first to generate the data.
    pause
    exit /b 1
)

REM Install requirements
echo Installing required packages...
pip install -r requirements.txt

REM Run the app
echo Starting Streamlit app...
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0

pause
