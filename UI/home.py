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

        # Refresh button
        refresh_btn = Gtk.Button(label="🔄 Refresh")
        refresh_btn.connect("clicked", self.on_refresh_clicked)
        vbox.pack_start(refresh_btn, False, False, 0)

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

    def get_running_windows(self):
        """Get actual running windows using wmctrl"""
        try:
            # wmctrl -l shows all windows
            result = subprocess.run(
                ['wmctrl', '-lx'],
                capture_output=True,
                text=True,
                check=True
            )
            
            windows = []
            seen_classes = set()
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                parts = line.split(None, 3)
                if len(parts) < 4:
                    continue
                
                # Format: window_id desktop class_name window_title
                window_class = parts[2].split('.')[1] if '.' in parts[2] else parts[2]
                window_title = parts[3]
                
                # Skip duplicates and desktop/panel windows
                if window_class.lower() in ['desktop', 'panel', 'dock']:
                    continue
                    
                if window_class not in seen_classes:
                    seen_classes.add(window_class)
                    windows.append({
                        'class': window_class,
                        'title': window_title
                    })
            
            return windows
            
        except FileNotFoundError:
            self.status_label.set_text("wmctrl not installed. Install: sudo apt install wmctrl")
            return []
        except subprocess.CalledProcessError:
            self.status_label.set_text("Error getting window list")
            return []

    def populate_running_apps(self):
        """Get list of running applications from window manager"""
        self.app_combo.remove_all()
        
        windows = self.get_running_windows()
        
        if not windows:
            # Fallback to sample data if wmctrl not available
            sample_apps = ["Firefox", "VSCode", "Terminal", "Spotify"]
            for app in sample_apps:
                self.app_combo.append_text(app)
        else:
            for window in windows:
                display_name = f"{window['class']} - {window['title'][:40]}"
                self.app_combo.append_text(display_name)
        
        if self.app_combo.get_model() and len(self.app_combo.get_model()) > 0:
            self.app_combo.set_active(0)

    def on_refresh_clicked(self, widget):
        """Refresh the application list"""
        self.populate_running_apps()
        self.status_label.set_text("Refreshed application list")

    def on_export_clicked(self, widget):
        """Export selected app state to .xis file"""
        app_name = self.app_combo.get_active_text()
        if not app_name:
            self.status_label.set_text("Please select an application")
            return

        # Extract just the class name
        app_class = app_name.split(' - ')[0] if ' - ' in app_name else app_name

        dialog = Gtk.FileChooserDialog(
            title="Save State As",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        dialog.set_current_name(f"{app_class.lower()}-state.xis")

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            output_path = dialog.get_filename()
            script_path = Path(__file__).parent.parent / "scripts" / "export.py"
            result = subprocess.run(
                ["python3", str(script_path), app_class, output_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.status_label.set_text(f"✓ Exported: {os.path.basename(output_path)}")
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
                self.status_label.set_text("✓ State imported successfully")
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