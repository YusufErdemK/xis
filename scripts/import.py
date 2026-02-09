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


def main():
    if len(sys.argv) < 2:
        print("Usage: import.py <file.xis>")
        sys.exit(1)

    xis_path = sys.argv[1]

    if not os.path.exists(xis_path):
        print(f"Error: {xis_path} not found")
        sys.exit(1)

    manifest = extract_xis_archive(xis_path)
    restore_app_state(manifest)


if __name__ == "__main__":
    main()