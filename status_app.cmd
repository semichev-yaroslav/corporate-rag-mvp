@echo off
chcp 65001 >nul
wsl.exe -d Ubuntu-22.04 -u root -- bash -lc "/opt/corporate-rag-mvp/scripts/status_stack.sh"
