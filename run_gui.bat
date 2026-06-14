@echo off
call conda activate controller-map
set PYTHONPATH=src
python -m controller_mapper gui
if %errorlevel% neq 0 pause
