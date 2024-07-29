@echo off
git reset --hard HEAD
git pull
pip install python-dotenv
pip install requests
python main.py
pause
