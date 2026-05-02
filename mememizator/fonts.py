import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from .config import load_config
from .constants import BASE_DIR, CONFIG_DIR, FONTS_DIR, TEMPLATE_DEFAULT_FONT
from .dependencies import require_pillow
from .utils import log


ATTEMPTED_FONT_DOWNLOADS: set[str] = set()


# Extracts font candidate names from a font config.
def get_font_candidates(font_config: Any) -> list[str]:
    if not isinstance(font_config, dict):
        return []

    candidates = font_config.get("font_candidates", [])
    if isinstance(candidates, str):
        return [candidates]
    if isinstance(candidates, list):
        return [candidate for candidate in candidates if isinstance(candidate, str) and candidate.strip()]
    return []


# Extracts download options from a font config.
def extract_download_config(font_config: Any) -> dict[str, Any]:
    if not isinstance(font_config, dict):
        return {}

    download = font_config.get("download", {})
    return download if isinstance(download, dict) else {}


# Resolves existing font files from candidate names.
def iter_font_candidates(candidates: list[str] | tuple[str, ...] | str | Any) -> list[Path]:
    if isinstance(candidates, str):
        candidates = [candidates]
    elif not isinstance(candidates, (list, tuple)):
        candidates = []

    common_dirs = [
        BASE_DIR,
        CONFIG_DIR,
        FONTS_DIR,
        Path.cwd(),
        Path("C:/Windows/Fonts"),
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path.home() / ".fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
    ]

    resolved: list[Path] = []
    seen: set[str] = set()

    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue

        raw_path = Path(candidate)
        possible_paths = [raw_path]
        possible_paths.extend(directory / candidate for directory in common_dirs)

        for path in possible_paths:
            try:
                normalized = str(path.resolve(strict=False)).lower()
            except OSError:
                normalized = str(path).lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            if path.is_file():
                resolved.append(path)

    return resolved


# Extracts a font file from a zip archive.
def extract_font_from_zip(zip_bytes: bytes, destination_dir: Path, target_file: str, archive_member: str | None = None) -> bool:
    destination_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        font_members = [
            member
            for member in archive.namelist()
            if not member.endswith("/") and Path(member).suffix.lower() in {".ttf", ".otf"}
        ]
        if not font_members:
            return False

        selected_member = None
        if isinstance(archive_member, str) and archive_member.strip():
            wanted_name = Path(archive_member).name.lower()
            for member in font_members:
                if Path(member).name.lower() == wanted_name:
                    selected_member = member
                    break

        if selected_member is None:
            target_name = Path(target_file).name.lower()
            for member in font_members:
                if Path(member).name.lower() == target_name:
                    selected_member = member
                    break

        if selected_member is None:
            selected_member = font_members[0]

        extracted_bytes = archive.read(selected_member)
        output_path = destination_dir / target_file
        output_path.write_bytes(extracted_bytes)
        return output_path.is_file()


# Downloads missing font assets declared by a font config.
def download_font_assets(font_config: Any) -> None:
    candidates = get_font_candidates(font_config)
    if iter_font_candidates(candidates):
        return

    download_config = extract_download_config(font_config)
    download_url = download_config.get("url")
    target_file = download_config.get("target_file")
    archive_member = download_config.get("archive_member")

    if not isinstance(download_url, str) or not download_url.strip():
        return
    if not isinstance(target_file, str) or not target_file.strip():
        if candidates:
            target_file = Path(candidates[0]).name
        else:
            return

    attempt_key = f"{download_url}|{target_file}"
    if attempt_key in ATTEMPTED_FONT_DOWNLOADS:
        return
    ATTEMPTED_FONT_DOWNLOADS.add(attempt_key)

    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        request = urllib.request.Request(
            download_url,
            headers={"User-Agent": "ComfyUI-Mememizator/0.0.1"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
    except Exception as exc:
        log(f"Failed to download font from {download_url}: {exc}")
        return

    try:
        if download_url.lower().endswith(".zip"):
            if extract_font_from_zip(payload, FONTS_DIR, target_file, archive_member if isinstance(archive_member, str) else None):
                log(f"Downloaded font {target_file} to {FONTS_DIR}")
            else:
                log(f"Downloaded archive from {download_url}, but no font file was found inside")
            return

        output_path = FONTS_DIR / target_file
        output_path.write_bytes(payload)
        log(f"Downloaded font {target_file} to {FONTS_DIR}")
    except Exception as exc:
        log(f"Failed to save font {target_file}: {exc}")


# Ensures downloadable fonts for all templates are available.
def ensure_template_fonts_available() -> None:
    config = load_config()
    for template in config.get("templates", []):
        if not isinstance(template, dict):
            continue

        font_config = template.get("font")
        if isinstance(font_config, dict):
            download_font_assets(font_config)


# Returns font names available to the settings node.
def get_available_font_names() -> tuple[str, ...]:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    font_names = sorted({path.name for path in FONTS_DIR.glob("*.ttf") if path.is_file()})
    if font_names:
        return tuple(font_names)

    fallback_names: set[str] = set()
    for template in load_config().get("templates", []):
        if not isinstance(template, dict):
            continue
        for key in ("font", "title", "subtitle"):
            for candidate in get_font_candidates(template.get(key, {})):
                if candidate.lower().endswith(".ttf"):
                    fallback_names.add(Path(candidate).name)

    return tuple(sorted(fallback_names))


# Returns settings-node font options including the template default.
def get_settings_font_options() -> tuple[str, ...]:
    return (TEMPLATE_DEFAULT_FONT, *get_available_font_names())


# Loads a configured font at the requested size.
def load_font(font_config: Any, size: int):
    _, _, _, ImageFont = require_pillow()
    download_font_assets(font_config)
    font_candidates = get_font_candidates(font_config)

    for candidate in iter_font_candidates(font_candidates):
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue

    return ImageFont.load_default()


