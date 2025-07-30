#!/bin/zsh
cd /Users/ayshafidha/Documents/Safety-route-AI-Project
git add .
git commit -m "Auto-upload: $(date '+%Y-%m-%d %H:%M:%S')" || exit 0
git push origin main