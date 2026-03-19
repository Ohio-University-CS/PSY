# PSY
Repository for the Precariously Studious Individuals

# canBet – Productivity Lootbox System
canBet is a gamified productivity platform that integrates with Canvas LMS.  
Students earn Bits by completing assignments, quizzes, and discussion boards.  
Bits are spent on crates and shop items, which contribute to leaderboard rankings.

---

# Vision / Problem Statement
Traditional LMS platforms track grades but do not incentivize consistent productivity.  
canBet introduces a reward-based system that:
- Encourages task completion
- Gamifies academic progress
- Creates friendly competition through leaderboards
- Increases engagement with coursework

---

# Tech Stack
## Frontend
- HTML
- CSS
- JavaScript

## Backend
- Python / Django

## Integration
- Canvas LMS REST API

---

# Browser Extension

The extension runs on any `*.instructure.com` page and automatically pulls your assignment and submission data using your active Canvas session.

## Installing on Chrome

1. Go to `chrome://extensions`
2. Enable **Developer Mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the `extension/chrome/` folder
5. Navigate to any `*.instructure.com` page
6. Open DevTools (`F12`) → Console to verify output

## Installing on Firefox

1. Go to `about:debugging`
2. Click **This Firefox**
3. Click **Load Temporary Add-on**
4. Select `extension/firefox/manifest.json`
5. Navigate to any `*.instructure.com` page
6. Open Browser Console (`Ctrl+Shift+J`) to verify output

> Firefox temporary add-ons are removed on browser restart.

---
