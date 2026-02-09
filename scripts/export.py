#!/usr/bin/env python3
"""
ZeXis State Share - Export Script
Exports application state, config, and mods into a .xis archive
"""

import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, Any

XISFS_ROOT = Path.home() / "xis" / "xisfs"


def collect_app_state(app_name: str) -> Dict[str, Any]:
    """
    Collect all state information for the given application
    """
    state_data = {
        "app": app_name,
        "version": "1.0.0",
        "timestamp": "",
        "config": {},
        "state": {},
        "mods": [],
        "window": {}
    }

    # Load config
    config_file = XISFS_ROOT / "config" / "app.conf"
    if config_file.exists():
        with open(config_file, 'r') as f:
            state_data["config"] = json.load(f)

    # Load state files
    state_dir = XISFS_ROOT / "state"
    if state_dir.exists():
        for state_file in state_dir.glob("*.json"):
            with open(state_file, 'r') as f:
                state_data["state"][state_file.stem] = json.load(f)

    # Load window state
    window_file = XISFS_ROOT / "window" / "window.json"
    if window_file.exists():
        with open(window_file, 'r') as f:
            state_data["window"] = json.load(f)

    # Load mods
    mods_config_dir = XISFS_ROOT / "config" / "mods"
    if mods_config_dir.exists():
        for mod_file in mods_config_dir.glob("*.json"):
            with open(mod_file, 'r') as f:
                state_data["mods"].append(json.load(f))

    return state_data


def create_xis_archive(app_name: str, output_path: str) -> None:
    """
    Create a compressed .xis archive containing all application state
    """
    state_data = collect_app_state(app_name)

    # Create temporary directory for staging
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Write manifest
        manifest_path = tmpdir_path / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(state_data, f, indent=2)

        # Copy mod files if they exist
        mods_src = XISFS_ROOT / "mods"
        if mods_src.exists() and any(mods_src.iterdir()):
            mods_dst = tmpdir_path / "mods"
            mods_dst.mkdir(exist_ok=True)
            for mod_file in mods_src.iterdir():
                if mod_file.is_file():
                    import shutil
                    shutil.copy2(mod_file, mods_dst / mod_file.name)

        # Create .xis archive (tar.gz)
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(manifest_path, arcname="manifest.json")
            if (tmpdir_path / "mods").exists():
                tar.add(tmpdir_path / "mods", arcname="mods")

    print(f"✓ Exported state to {output_path}")


def main():
    if len(sys.argv) < 3:
        print("Usage: export.py <app_name> <output.xis>")
        sys.exit(1)

    app_name = sys.argv[1]
    output_path = sys.argv[2]

    if not output_path.endswith('.xis'):
        output_path += '.xis'

    create_xis_archive(app_name, output_path)


if __name__ == "__main__":
    main()