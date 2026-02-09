#!/usr/bin/env python3
"""
ZeXis State Share - Main UI
GTK-based interface for selecting apps and managing state transfers
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
import subprocess
import os
from pathlib import Path

XISFS_ROOT = Path.home() / "xis" / "xisfs"


class ZeXisStateShareUI(Gtk.Window):
    def __init__(self):
        super().__init__(title="ZeXis State Share")
        self.set_border_width(20)
        self.set_default_size(600, 400)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Apply CSS
        self.apply_css()

        # Main container
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.add(vbox)

        # Header
        header = Gtk.Label()
        header.set_markup("<span size='x-large' weight='bold'>State Share</span>")
        header.set_halign(Gtk.Align.START)
        vbox.pack_start(header, False, False, 0)

        # App selection
        app_label = Gtk.Label(label="Select running application:", xalign=0)
        vbox.pack_start(app_label, False, False, 0)

        self.app_combo = Gtk.ComboBoxText()
        self.app_combo.set_entry_text_column(0)
        self.populate_running_apps()
        vbox.pack_start(self.app_combo, False, False, 0)

        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        vbox.pack_start(button_box, False, False, 10)

        export_btn = Gtk.Button(label="Export State")
        export_btn.connect("clicked", self.on_export_clicked)
        export_btn.get_style_context().add_class("primary-button")
        button_box.pack_start(export_btn, False, False, 0)

        import_btn = Gtk.Button(label="Import State")
        import_btn.connect("clicked", self.on_import_clicked)
        button_box.pack_start(import_btn, False, False, 0)

        send_btn = Gtk.Button(label="Send to Computer")
        send_btn.connect("clicked", self.on_send_clicked)
        send_btn.get_style_context().add_class("send-button")
        button_box.pack_start(send_btn, False, False, 0)

        # Status area
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.get_style_context().add_class("status-label")
        vbox.pack_end(self.status_label, False, False, 0)

    def apply_css(self):
        """Load and apply CSS styling"""
        css_file = Path(__file__).parent / "style.css"
        if css_file.exists():
            css_provider = Gtk.CssProvider()
            css_provider.load_from_path(str(css_file))
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def populate_running_apps(self):
        """Get list of running applications (simplified)"""
        # This is a placeholder - real implementation would query window manager
        sample_apps = ["Firefox", "VSCode", "Terminal", "Spotify"]
        for app in sample_apps:
            self.app_combo.append_text(app)
        self.app_combo.set_active(0)

    def on_export_clicked(self, widget):
        """Export selected app state to .xis file"""
        app_name = self.app_combo.get_active_text()
        if not app_name:
            self.status_label.set_text("Please select an application")
            return

        dialog = Gtk.FileChooserDialog(
            title="Save State As",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        dialog.set_current_name(f"{app_name.lower()}-state.xis")

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            output_path = dialog.get_filename()
            script_path = Path(__file__).parent.parent / "scripts" / "export.py"
            result = subprocess.run(
                ["python3", str(script_path), app_name, output_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.status_label.set_text(f"Exported: {output_path}")
            else:
                self.status_label.set_text(f"Export failed: {result.stderr}")

        dialog.destroy()

    def on_import_clicked(self, widget):
        """Import .xis file and restore state"""
        dialog = Gtk.FileChooserDialog(
            title="Select .xis File",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        filter_xis = Gtk.FileFilter()
        filter_xis.set_name("XIS files")
        filter_xis.add_pattern("*.xis")
        dialog.add_filter(filter_xis)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            xis_path = dialog.get_filename()
            script_path = Path(__file__).parent.parent / "scripts" / "import.py"
            result = subprocess.run(
                ["python3", str(script_path), xis_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.status_label.set_text("State imported successfully")
            else:
                self.status_label.set_text(f"Import failed: {result.stderr}")

        dialog.destroy()

    def on_send_clicked(self, widget):
        """Send state to another computer"""
        # This would trigger the connection dialog
        self.status_label.set_text("Send functionality requires target computer configuration")


def main():
    win = ZeXisStateShareUI()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()