"""Build the installable custom integration archive from the current tree."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "custom_components/smart_notifications/manifest.json").read_text())
    version = manifest["version"]
    output = root / "dist" / f"smart-notifications-{version}.zip"
    output.parent.mkdir(exist_ok=True)
    package_root = root / "custom_components" / "smart_notifications"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package_root.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, Path("custom_components/smart_notifications") / path.relative_to(package_root))
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        required = {
            "custom_components/smart_notifications/manifest.json",
            "custom_components/smart_notifications/strings.json",
            "custom_components/smart_notifications/translations/de.json",
            "custom_components/smart_notifications/translations/en.json",
            "custom_components/smart_notifications/brand/icon.png",
        }
        missing = required - names
        if missing:
            print(f"Missing package files: {sorted(missing)}", file=sys.stderr)
            return 1
        print(f"Built {output} ({len(names)} files)")
        print(f"SHA256: {__import__('hashlib').sha256(output.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
