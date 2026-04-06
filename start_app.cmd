@echo off
chcp 65001 >nul
wsl.exe -d Ubuntu-22.04 -u root -- bash -lc "/opt/corporate-rag-mvp/scripts/start_stack.sh"
