@echo off
chcp 65001 > nul
set PYTHONPATH=
cd /d "C:\workspace\llm_wiki"
echo ========================================================
echo  Starting: llm_wiki
echo  Command:  wiki.bat
echo  Working:  C:\workspace\llm_wiki
echo ========================================================
wiki.bat
echo.
echo ========================================================
echo Process finished. Window will stay open for inspection.
pause
