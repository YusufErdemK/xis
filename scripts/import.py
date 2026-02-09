#!/usr/bin/env python3
"""
ZeXis State Share - Import Script
Imports a .xis archive and restores application state
"""

import json
import os
import sys
import tarfile
import tempfile
import subprocess
import time
from pathlib import Path
from typing import Dict, Any

XISFS_ROOT = Path.home() / "xis" / "xisfs"


def extract_xis_archive(xis_path: str) -> Dict[str, Any]:
    """
    Extract .xis archive and return manifest data
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Extract archive
        with tarfile.open(xis_path, "r:gz") as tar:
            tar.extractall(tmpdir_path)

        # Read manifest
        manifest_path = tmpdir_path / "manifest.json"
        if not manifest_path.exists():
            raise ValueError("Invalid .xis file: missing manifest.json")

        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        # Copy mods if present
        mods_src = tmpdir_path / "mods"
        if mods_src.exists():
            mods_dst = XISFS_ROOT / "mods"
            mods_dst.mkdir(parents=True, exist_ok=True)
            import shutil
            for mod_file in mods_src.iterdir():
                if mod_file.is_file():
                    shutil.copy2(mod_file, mods_dst / mod_file.name)

        return manifest


def restore_app_state(manifest: Dict[str, Any]) -> None:
    """
    Restore application state from manifest data
    """
    # Restore config
    if manifest.get("config"):
        config_file = XISFS_ROOT / "config" / "app.conf"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(manifest["config"], f, indent=2)

    # Restore state files
    if manifest.get("state"):
        state_dir = XISFS_ROOT / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        for state_name, state_content in manifest["state"].items():
            state_file = state_dir / f"{state_name}.json"
            with open(state_file, 'w') as f:
                json.dump(state_content, f, indent=2)

    # Restore window state
    if manifest.get("window"):
        window_file = XISFS_ROOT / "window" / "window.json"
        window_file.parent.mkdir(parents=True, exist_ok=True)
        with open(window_file, 'w') as f:
            json.dump(manifest["window"], f, indent=2)

    # Restore mod configs
    if manifest.get("mods"):
        mods_config_dir = XISFS_ROOT / "config" / "mods"
        mods_config_dir.mkdir(parents=True, exist_ok=True)
        for idx, mod_config in enumerate(manifest["mods"], 1):
            mod_file = mods_config_dir / f"mod{idx}.json"
            with open(mod_file, 'w') as f:
                json.dump(mod_config, f, indent=2)

    print(f"✓ Restored state for {manifest.get('app', 'unknown app')}")


def launch_application(app_name: str, window_state: Dict[str, Any]) -> None:
    """
    Launch the application and restore window geometry
    """
    app_name_lower = app_name.lower()
    
    # Common application launch commands
    app_commands = {
        'firefox': ['firefox'],
        'chrome': ['google-chrome'],
        'chromium': ['chromium'],
        'code': ['code'],
        'vscode': ['code'],
        'terminal': ['gnome-terminal'],
        'gnome-terminal': ['gnome-terminal'],
        'konsole': ['konsole'],
        'nautilus': ['nautilus'],
        'spotify': ['spotify'],
        'discord': ['discord'],
        'slack': ['slack'],
        'telegram': ['telegram-desktop'],
    }
    
    # Find appropriate command
    launch_cmd = None
    for key, cmd in app_commands.items():
        if key in app_name_lower:
            launch_cmd = cmd
            break
    
    if not launch_cmd:
        # Try to use the app name directly
        launch_cmd = [app_name_lower]
    
    try:
        # Launch the application
        print(f"Launching {app_name}...")
        process = subprocess.Popen(
            launch_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for window to appear
        time.sleep(2)
        
        # Restore window geometry if available
        if window_state and 'geometry' in window_state:
            geometry = window_state['geometry']
            x = geometry.get('x', 100)
            y = geometry.get('y', 100)
            width = geometry.get('width', 800)
            height = geometry.get('height', 600)
            
            # Use wmctrl to set window position and size
            try:
                # Find the window
                result = subprocess.run(
                    ['wmctrl', '-l'],
                    capture_output=True,
                    text=True
                )
                
                window_id = None
                for line in result.stdout.split('\n'):
                    if app_name.lower() in line.lower():
                        window_id = line.split()[0]
                        break
                
                if window_id:
                    # Move and resize window
                    # Format: wmctrl -i -r <window_id> -e <gravity>,<x>,<y>,<width>,<height>
                    subprocess.run([
                        'wmctrl', '-i', '-r', window_id,
                        '-e', f'0,{x},{y},{width},{height}'
                    ])
                    print(f"✓ Restored window geometry: {width}x{height}+{x}+{y}")
                    
                    # Set workspace if available
                    if 'workspace' in window_state:
                        workspace = window_state['workspace']
                        subprocess.run([
                            'wmctrl', '-i', '-r', window_id,
                            '-t', str(workspace)
                        ])
                        print(f"✓ Moved to workspace {workspace}")
                else:
                    print("⚠ Window not found for geometry restoration")
                    
            except FileNotFoundError:
                print("⚠ wmctrl not found, skipping window positioning")
            except Exception as e:
                print(f"⚠ Could not restore window geometry: {e}")
        
        print(f"✓ Launched {app_name}")
        
    except FileNotFoundError:
        print(f"✗ Could not launch {app_name}: command not found")
        print(f"  Please install {app_name} or launch it manually")
    except Exception as e:
        print(f"✗ Error launching {app_name}: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: import.py <file.xis>")
        sys.exit(1)

    xis_path = sys.argv[1]

    if not os.path.exists(xis_path):
        print(f"Error: {xis_path} not found")
        sys.exit(1)

    # Extract and restore state
    manifest = extract_xis_archive(xis_path)
    restore_app_state(manifest)
    
    # Launch application with restored window state
    app_name = manifest.get('app', '')
    window_state = manifest.get('window', {})
    
    if app_name:
        launch_application(app_name, window_state)
    else:
        print("⚠ No application name in manifest, skipping launch")


if __name__ == "__main__":
    main()