@echo off
rem Dipanggil oleh Windows Task Scheduler. Output dicatat ke hasil\jadwal.log
cd /d "%~dp0"
if not exist hasil mkdir hasil
"C:\Users\LOQ\AppData\Local\Programs\Python\Python310\python.exe" ambil_tweet.py --keyword "GANTI_KEYWORD_ANDA" --hari 3 --limit 500 --nama data_tweet >> hasil\jadwal.log 2>&1
