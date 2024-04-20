@echo off
git pull
pip install python-dotenv
pip install requests
python edit_url.py
python main.py
pause