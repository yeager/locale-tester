# Locale Tester

A GTK4/Adwaita application for inspecting and comparing locale behavior on Linux. See how dates, numbers, currency, sorting, and more look across different system locales — useful for finding locale bugs and understanding i18n behavior.

![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)

## Features

- **Inspect** any installed system locale: dates (short/long/relative), time, numbers, currency, percent
- **Collation order** — see how sample words sort under different locales
- **Weekday names, month names, AM/PM** indicators
- **Decimal point, thousands separator, currency symbol** details
- **Compare two locales** side by side
- **strftime tester** — enter custom format strings and see results under any locale
- **LC_\* environment variables** overview

## Installation

### From .deb (Debian/Ubuntu)

```bash
# Add the repository
curl -fsSL https://yeager.github.io/debian-repo/pub.key | sudo gpg --dearmor -o /usr/share/keyrings/yeager.gpg
echo "deb [signed-by=/usr/share/keyrings/yeager.gpg] https://yeager.github.io/debian-repo stable main" | sudo tee /etc/apt/sources.list.d/yeager.list
sudo apt update
sudo apt install locale-tester
```

### From source

```bash
pip install .
locale-tester
```

### Dependencies

- Python 3.10+
- GTK 4
- libadwaita 1
- PyGObject

On Debian/Ubuntu: `sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1`

## Usage

```bash
locale-tester
```

## Translating

Translations are managed via [Transifex](https://app.transifex.com/danielnylander/locale-tester/).

To generate the POT file:

```bash
xgettext --language=Python --keyword=_ --output=po/locale-tester.pot src/locale_tester/main.py
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

## Author

Daniel Nylander <daniel@danielnylander.se>
