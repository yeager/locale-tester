# Locale Tester

A GTK4/Adwaita application for inspecting and comparing system locale settings on Linux.

![Screenshot](data/screenshots/screenshot-01.png)

## Features

- Inspect any installed system locale: dates, time, numbers, currency, percent
- Collation order — see how sample words sort under different locales
- Weekday names, month names, AM/PM indicators
- Decimal point, thousands separator, currency symbol details
- Compare two locales side by side
- strftime tester — enter custom format strings and see results
- LC_* environment variables overview

## Installation

### Debian/Ubuntu

```bash
# Add repository
curl -fsSL https://yeager.github.io/debian-repo/KEY.gpg | sudo gpg --dearmor -o /usr/share/keyrings/yeager-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/yeager-archive-keyring.gpg] https://yeager.github.io/debian-repo stable main" | sudo tee /etc/apt/sources.list.d/yeager.list
sudo apt update
sudo apt install locale-tester
```

### Fedora/RHEL

```bash
sudo dnf config-manager --add-repo https://yeager.github.io/rpm-repo/yeager.repo
sudo dnf install locale-tester
```

### From source

```bash
pip install .
locale-tester
```

## 🌍 Contributing Translations

Help translate this app into your language! All translations are managed via Transifex.

**→ [Translate on Transifex](https://app.transifex.com/danielnylander/locale-tester/)**

### How to contribute:
1. Visit the [Transifex project page](https://app.transifex.com/danielnylander/locale-tester/)
2. Create a free account (or log in)
3. Select your language and start translating

### Currently supported languages:
Arabic, Czech, Danish, German, Spanish, Finnish, French, Italian, Japanese, Korean, Norwegian Bokmål, Dutch, Polish, Brazilian Portuguese, Russian, Swedish, Ukrainian, Chinese (Simplified)

### Notes:
- Please do **not** submit pull requests with .po file changes — they are synced automatically from Transifex
- Source strings are pushed to Transifex daily via GitHub Actions
- Translations are pulled back and included in releases

New language? Open an [issue](https://github.com/yeager/locale-tester/issues) and we'll add it!

## License

GPL-3.0-or-later — Daniel Nylander <daniel@danielnylander.se>
