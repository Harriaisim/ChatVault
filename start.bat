@echo off
title ChatVault Server
echo ===================================================
echo   ✦ ChatVault is starting...
echo   Please keep this black window open while using the app.
echo   Closing this window will shut down ChatVault.
echo ===================================================
python -m streamlit run src\app.py
pause
