#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Daniel Nylander <daniel@danielnylander.se>

"""Locale Tester — see how dates, numbers, currency, and sorting look in different locales."""

import sys
import os
import locale
import subprocess
import ctypes
import ctypes.util
import gettext
import datetime
import textwrap

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
# Optional desktop notifications
try:
    gi.require_version("Notify", "0.7")
    from gi.repository import Notify as _Notify
    HAS_NOTIFY = True
except (ValueError, ImportError):
    HAS_NOTIFY = False
from gi.repository import Gtk, Adw, Gio, GLib, Pango  # noqa: E402

APP_ID = "se.danielnylander.LocaleTester"
GETTEXT_DOMAIN = "locale-tester"

# i18n
_locale_dir = os.path.join(os.path.dirname(__file__), "..", "..", "po")
if not os.path.isdir(_locale_dir):
    _locale_dir = "/usr/share/locale"
gettext.bindtextdomain(GETTEXT_DOMAIN, _locale_dir)
gettext.textdomain(GETTEXT_DOMAIN)
_ = gettext.gettext


# ---------------------------------------------------------------------------
# Locale helpers
# ---------------------------------------------------------------------------

def get_available_locales():
    """Return sorted list of available system locales."""
    try:
        out = subprocess.check_output(["locale", "-a"], text=True, stderr=subprocess.DEVNULL)
        return sorted(set(out.strip().splitlines()))
    except Exception:
        return ["C", "POSIX", "en_US.UTF-8"]


def safe_setlocale(cat, loc):
    """Try to set locale category, return True on success."""
    try:
        locale.setlocale(cat, loc)
        return True
    except locale.Error:
        return False


def locale_info(loc):
    """Gather locale information for *loc* and return a dict."""
    info = {}
    old = locale.getlocale(locale.LC_ALL)

    if not safe_setlocale(locale.LC_ALL, loc):
        # Try with .UTF-8 suffix
        if not safe_setlocale(locale.LC_ALL, loc + ".UTF-8"):
            return None

    now = datetime.datetime.now()

    # Date / time
    try:
        info["date_short"] = now.strftime("%x")
    except Exception:
        info["date_short"] = "N/A"
    try:
        info["date_long"] = now.strftime("%c")
    except Exception:
        info["date_long"] = "N/A"
    try:
        info["time"] = now.strftime("%X")
    except Exception:
        info["time"] = "N/A"

    # Weekday names
    try:
        info["weekdays"] = ", ".join(
            (now.replace(day=9 + i) if now.month == 2 and now.year == 2026 else now.replace(day=1) + datetime.timedelta(days=i)).strftime("%A")
            for i in range(7)
        )
    except Exception:
        # Fallback: use a known Monday
        base = datetime.datetime(2026, 2, 9)  # Monday
        info["weekdays"] = ", ".join((base + datetime.timedelta(days=i)).strftime("%A") for i in range(7))

    # Month names
    try:
        info["months"] = ", ".join(
            datetime.datetime(2026, m, 1).strftime("%B") for m in range(1, 13)
        )
    except Exception:
        info["months"] = "N/A"

    # AM/PM
    try:
        am = datetime.datetime(2026, 1, 1, 6, 0).strftime("%p")
        pm = datetime.datetime(2026, 1, 1, 18, 0).strftime("%p")
        info["ampm"] = f"{am} / {pm}" if am else _("(not used)")
    except Exception:
        info["ampm"] = "N/A"

    # Number formatting
    conv = locale.localeconv()
    info["decimal_point"] = conv.get("decimal_point", "N/A")
    info["thousands_sep"] = conv.get("thousands_sep", "N/A") or _("(none)")
    info["currency_symbol"] = conv.get("currency_symbol", "N/A") or conv.get("int_curr_symbol", "N/A")

    # Formatted number
    try:
        info["number"] = locale.format_string("%.2f", 1234567.89, grouping=True)
    except Exception:
        info["number"] = "N/A"

    # Percent
    try:
        info["percent"] = locale.format_string("%.1f%%", 85.3, grouping=True)
    except Exception:
        info["percent"] = "85.3%"

    # Currency
    try:
        info["currency"] = locale.currency(1234567.89, grouping=True)
    except Exception:
        info["currency"] = "N/A"

    # Collation example
    sample_words = ["äpple", "apple", "ångström", "zoo", "über", "öl", "cherry", "ärta", "banana"]
    try:
        import functools
        sorted_words = sorted(sample_words, key=functools.cmp_to_key(locale.strcoll))
        info["collation"] = ", ".join(sorted_words)
    except Exception:
        info["collation"] = ", ".join(sorted(sample_words))

    # Relative date (simple)
    yesterday = now - datetime.timedelta(days=1)
    info["date_relative_yesterday"] = yesterday.strftime("%x")

    # LC_* vars
    lc_cats = [
        "LC_CTYPE", "LC_NUMERIC", "LC_TIME", "LC_COLLATE",
        "LC_MONETARY", "LC_MESSAGES", "LC_ALL", "LANG",
    ]
    info["lc_vars"] = "\n".join(f"{c} = {os.environ.get(c, _('(unset)'))}" for c in lc_cats)

    # Restore
    try:
        locale.setlocale(locale.LC_ALL, old)
    except Exception:
        locale.setlocale(locale.LC_ALL, "")

    return info


def strftime_test(loc, fmt):
    """Test a strftime format string under a given locale."""
    old = locale.getlocale(locale.LC_ALL)
    if not safe_setlocale(locale.LC_ALL, loc):
        safe_setlocale(locale.LC_ALL, loc + ".UTF-8")
    try:
        result = datetime.datetime.now().strftime(fmt)
    except Exception as e:
        result = str(e)
    try:
        locale.setlocale(locale.LC_ALL, old)
    except Exception:
        locale.setlocale(locale.LC_ALL, "")
    return result


# ---------------------------------------------------------------------------
# Locale info panel widget
# ---------------------------------------------------------------------------


import json as _json
import platform as _platform
from pathlib import Path as _Path
from datetime import datetime as _dt_now

_NOTIFY_APP = "locale-tester"


def _notify_config_path():
    return _Path(GLib.get_user_config_dir()) / _NOTIFY_APP / "notifications.json"


def _load_notify_config():
    try:
        return _json.loads(_notify_config_path().read_text())
    except Exception:
        return {"enabled": False}


def _save_notify_config(config):
    p = _notify_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_json.dumps(config))


def _send_notification(summary, body="", icon="dialog-information"):
    if HAS_NOTIFY and _load_notify_config().get("enabled"):
        try:
            n = _Notify.Notification.new(summary, body, icon)
            n.show()
        except Exception:
            pass


def _get_system_info():
    return "\n".join([
        f"App: Locale Tester",
        f"Version: {"0.1.0"}",
        f"GTK: {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}",
        f"Adw: {Adw.get_major_version()}.{Adw.get_minor_version()}.{Adw.get_micro_version()}",
        f"Python: {_platform.python_version()}",
        f"OS: {_platform.system()} {_platform.release()} ({_platform.machine()})",
    ])


class LocalePanel(Gtk.Box):
    """A panel showing locale details for a single locale."""

    def __init__(self, locales_list, label_text=""):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_hexpand(True)
        self.set_vexpand(True)

        # Locale selector
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox.set_margin_top(6)
        hbox.set_margin_start(6)
        hbox.set_margin_end(6)

        if label_text:
            lbl = Gtk.Label(label=label_text)
            lbl.add_css_class("heading")
            hbox.append(lbl)

        self.combo = Gtk.DropDown()
        self.string_list = Gtk.StringList()
        for loc in locales_list:
            self.string_list.append(loc)
        self.combo.set_model(self.string_list)
        self.combo.set_hexpand(True)

        # Enable search
        self.combo.set_enable_search(True)
        expr = Gtk.PropertyExpression.new(Gtk.StringObject, None, "string")
        self.combo.set_expression(expr)

        hbox.append(self.combo)
        self.append(hbox)

        # Scrolled content
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_vexpand(True)

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.content.set_margin_start(12)
        self.content.set_margin_end(12)
        self.content.set_margin_top(6)
        self.content.set_margin_bottom(12)

        sw.set_child(self.content)
        self.append(sw)

        self.combo.connect("notify::selected", self._on_locale_changed)

    def get_selected_locale(self):
        idx = self.combo.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION:
            return None
        return self.string_list.get_string(idx)

    def _on_locale_changed(self, dropdown, _pspec):
        self.refresh()

    def refresh(self):
        loc = self.get_selected_locale()
        if not loc:
            return
        # Clear
        while True:
            child = self.content.get_first_child()
            if child is None:
                break
            self.content.remove(child)

        info = locale_info(loc)
        if info is None:
            err = Gtk.Label(label=_("Could not set locale: %s") % loc)
            err.set_wrap(True)
            err.add_css_class("error")
            self.content.append(err)
            return

        rows = [
            (_("Date (short)"), info["date_short"]),
            (_("Date (long)"), info["date_long"]),
            (_("Yesterday"), info["date_relative_yesterday"]),
            (_("Time"), info["time"]),
            ("", ""),
            (_("Number (1 234 567.89)"), info["number"]),
            (_("Currency"), info["currency"]),
            (_("Percent"), info["percent"]),
            (_("Decimal point"), f"'{info['decimal_point']}'"),
            (_("Thousands separator"), f"'{info['thousands_sep']}'"),
            (_("Currency symbol"), info["currency_symbol"]),
            ("", ""),
            (_("AM / PM"), info["ampm"]),
            (_("Weekday names"), info["weekdays"]),
            (_("Month names"), info["months"]),
            ("", ""),
            (_("Collation order"), info["collation"]),
        ]

        for label, value in rows:
            if label == "" and value == "":
                sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                sep.set_margin_top(4)
                sep.set_margin_bottom(4)
                self.content.append(sep)
                continue
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            lbl = Gtk.Label(label=label, xalign=0)
            lbl.add_css_class("dim-label")
            lbl.add_css_class("caption")
            row.append(lbl)
            val = Gtk.Label(label=value, xalign=0)
            val.set_wrap(True)
            val.set_selectable(True)
            row.append(val)
            self.content.append(row)

    def select_locale(self, name):
        for i in range(self.string_list.get_n_items()):
            if self.string_list.get_string(i) == name:
                self.combo.set_selected(i)
                return


# ---------------------------------------------------------------------------
# Application window
# ---------------------------------------------------------------------------

class LocaleTesterWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=_("Locale Tester"), default_width=960, default_height=700)

        self.locales = get_available_locales()

        # Header bar
        header = Adw.HeaderBar()
        # View switcher in title
        self.view_stack = Adw.ViewStack()
        switcher_title = Adw.ViewSwitcherTitle(stack=self.view_stack)
        header.set_title_widget(switcher_title)

        # About button via menu
        menu = Gio.Menu.new()
        menu.append(_("About Locale Tester"), "app.about")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        header.pack_end(menu_btn)

        # Theme toggle
        self._theme_btn = Gtk.Button(icon_name="weather-clear-night-symbolic",
                                     tooltip_text="Toggle dark/light theme")
        self._theme_btn.connect("clicked", self._on_theme_toggle)
        header.pack_end(self._theme_btn)

        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(header)

        # Bottom bar for narrow
        switcher_bar = Adw.ViewSwitcherBar(stack=self.view_stack)
        switcher_title.connect("notify::title-visible", lambda st, _: switcher_bar.set_reveal(st.get_title_visible()))

        # --- Page 1: Single locale ---
        self.single_panel = LocalePanel(self.locales)
        self.view_stack.add_titled_with_icon(self.single_panel, "single", _("Inspect"), "system-search-symbolic")

        # --- Page 2: Compare ---
        compare_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1, homogeneous=True)
        self.left_panel = LocalePanel(self.locales, _("Locale A"))
        self.right_panel = LocalePanel(self.locales, _("Locale B"))
        compare_box.append(self.left_panel)
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        compare_box.append(sep)
        compare_box.append(self.right_panel)
        self.view_stack.add_titled_with_icon(compare_box, "compare", _("Compare"), "view-dual-symbolic")

        # --- Page 3: strftime tester ---
        strftime_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        strftime_box.set_margin_start(18)
        strftime_box.set_margin_end(18)
        strftime_box.set_margin_top(18)
        strftime_box.set_margin_bottom(18)

        st_label = Gtk.Label(label=_("Test strftime format strings under a chosen locale."), xalign=0)
        st_label.set_wrap(True)
        strftime_box.append(st_label)

        # Locale dropdown
        st_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        st_hbox.append(Gtk.Label(label=_("Locale:")))
        self.st_combo = Gtk.DropDown()
        self.st_string_list = Gtk.StringList()
        for loc in self.locales:
            self.st_string_list.append(loc)
        self.st_combo.set_model(self.st_string_list)
        self.st_combo.set_hexpand(True)
        self.st_combo.set_enable_search(True)
        expr = Gtk.PropertyExpression.new(Gtk.StringObject, None, "string")
        self.st_combo.set_expression(expr)
        st_hbox.append(self.st_combo)
        strftime_box.append(st_hbox)

        # Format entry
        fmt_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fmt_hbox.append(Gtk.Label(label=_("Format:")))
        self.fmt_entry = Gtk.Entry()
        self.fmt_entry.set_text("%A %d %B %Y, %X")
        self.fmt_entry.set_hexpand(True)
        fmt_hbox.append(self.fmt_entry)

        test_btn = Gtk.Button(label=_("Test"))
        test_btn.add_css_class("suggested-action")
        test_btn.connect("clicked", self._on_strftime_test)
        fmt_hbox.append(test_btn)
        strftime_box.append(fmt_hbox)

        self.fmt_entry.connect("activate", self._on_strftime_test)

        self.st_result = Gtk.Label(label="", xalign=0)
        self.st_result.set_selectable(True)
        self.st_result.set_wrap(True)
        self.st_result.add_css_class("title-2")
        strftime_box.append(self.st_result)

        # Common format reference
        ref_text = textwrap.dedent("""\
        %x  date    %X  time    %c  date+time
        %A  weekday %B  month   %p  AM/PM
        %d  day     %m  month#  %Y  year
        %H  hour24  %I  hour12  %M  minute  %S  second""")
        ref = Gtk.Label(label=ref_text, xalign=0)
        ref.add_css_class("monospace")
        ref.add_css_class("dim-label")
        ref.set_margin_top(12)
        strftime_box.append(ref)

        self.view_stack.add_titled_with_icon(strftime_box, "strftime", _("strftime"), "utilities-terminal-symbolic")

        # --- Page 4: LC_* environment ---
        env_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        env_box.set_margin_start(18)
        env_box.set_margin_end(18)
        env_box.set_margin_top(18)
        env_box.set_margin_bottom(18)

        env_label = Gtk.Label(label=_("Current LC_* environment variables:"), xalign=0)
        env_label.add_css_class("heading")
        env_box.append(env_label)

        lc_cats = [
            "LANG", "LANGUAGE", "LC_ALL", "LC_CTYPE", "LC_NUMERIC",
            "LC_TIME", "LC_COLLATE", "LC_MONETARY", "LC_MESSAGES",
            "LC_PAPER", "LC_NAME", "LC_ADDRESS", "LC_TELEPHONE",
            "LC_MEASUREMENT", "LC_IDENTIFICATION",
        ]
        for cat in lc_cats:
            val = os.environ.get(cat, _("(unset)"))
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            k = Gtk.Label(label=cat, xalign=0)
            k.set_size_request(180, -1)
            k.add_css_class("monospace")
            row.append(k)
            v = Gtk.Label(label=val, xalign=0)
            v.set_selectable(True)
            v.add_css_class("monospace")
            row.append(v)
            env_box.append(row)

        self.view_stack.add_titled_with_icon(env_box, "env", _("Environment"), "preferences-other-symbolic")

        main_box.append(self.view_stack)
        main_box.append(switcher_bar)
        # Status bar
        self._status_bar = Gtk.Label(label="", halign=Gtk.Align.START,
                                     margin_start=12, margin_end=12, margin_bottom=4)
        self._status_bar.add_css_class("dim-label")
        self._status_bar.add_css_class("caption")
        main_box.append(self._status_bar)

        self.set_content(main_box)

        # Default selection
        GLib.idle_add(self._set_defaults)

    def _set_defaults(self):
        current = locale.getlocale()[0] or "C"
        self.single_panel.select_locale(current)
        self.left_panel.select_locale(current)
        # Try to select a contrasting locale for right panel
        for candidate in ["de_DE.UTF-8", "ja_JP.UTF-8", "ar_SA.UTF-8", "C"]:
            if candidate in self.locales and candidate != current:
                self.right_panel.select_locale(candidate)
                break
        return False

    def _on_strftime_test(self, *_args):
        idx = self.st_combo.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION:
            return
        loc = self.st_string_list.get_string(idx)
        fmt = self.fmt_entry.get_text()
        result = strftime_test(loc, fmt)
        self.st_result.set_label(result)



    def _on_theme_toggle(self, _btn):
        sm = Adw.StyleManager.get_default()
        if sm.get_color_scheme() == Adw.ColorScheme.FORCE_DARK:
            sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            self._theme_btn.set_icon_name("weather-clear-night-symbolic")
        else:
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            self._theme_btn.set_icon_name("weather-clear-symbolic")

    def _update_status_bar(self):
        self._status_bar.set_text("Last updated: " + _dt_now.now().strftime("%Y-%m-%d %H:%M"))


class LocaleTesterApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        if HAS_NOTIFY:
            _Notify.init("locale-tester")
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("app.refresh", ["F5"])
        self.set_accels_for_action("app.shortcuts", ["<Control>slash"])
        for n, cb in [("quit", lambda *_: self.quit()),
                      ("refresh", lambda *_: self._do_refresh()),
                      ("shortcuts", self._show_shortcuts_window)]:
            a = Gio.SimpleAction.new(n, None); a.connect("activate", cb); self.add_action(a)

    def _do_refresh(self):
        w = self.get_active_window()
        if w and hasattr(w, '_refresh'): w._refresh()

    def _show_shortcuts_window(self, *_args):
        win = Gtk.ShortcutsWindow(transient_for=self.get_active_window(), modal=True)
        section = Gtk.ShortcutsSection(visible=True, max_height=10)
        group = Gtk.ShortcutsGroup(visible=True, title="General")
        for accel, title in [("<Control>q", "Quit"), ("F5", "Refresh"), ("<Control>slash", "Keyboard shortcuts")]:
            s = Gtk.ShortcutsShortcut(visible=True, accelerator=accel, title=title)
            group.append(s)
        section.append(group)
        win.add_child(section)
        win.present()

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            win = LocaleTesterWindow(self)
        win.present()

    def _on_about(self, action, param):
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name=_("Locale Tester"),
            application_icon="locale-tester",
            version="0.1.0",
            developer_name="Daniel Nylander",
            developers=["Daniel Nylander <daniel@danielnylander.se>"],
            copyright="© 2026 Daniel Nylander",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/yeager/locale-tester",
            issue_url="https://github.com/yeager/locale-tester/issues",
            translate_url="https://app.transifex.com/danielnylander/locale-tester/",
            comments=_("A localization tool by Daniel Nylander"),
            translator_credits=_("Translate this app: https://app.transifex.com/danielnylander/locale-tester/"),
        )
        about.set_debug_info(_get_system_info())
        about.set_debug_info_filename("locale-tester-debug.txt")
        about.present()


def main():
    app = LocaleTesterApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
