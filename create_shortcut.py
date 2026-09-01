"""
Generate custom ScrapeAgent icon and create Windows Desktop Shortcut.
Installs an instant, zero-terminal shortcut directly onto the user's Desktop.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"
ASSETS_DIR.mkdir(exist_ok=True)
ICO_PATH = ASSETS_DIR / "scrape_agent.ico"
PNG_PATH = ASSETS_DIR / "scrape_agent.png"


def create_agent_icon() -> Path:
    """Create a high-resolution 256x256 Obsidian & Electric Cyan application icon."""
    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 12

    # 1. Base Squircle / Rounded Rectangle
    # Background: Deep Obsidian Navy (#0a0f1d)
    draw.rounded_rectangle(
        [margin, margin, 256 - margin, 256 - margin],
        radius=54,
        fill=(10, 15, 29, 255),
        outline=(56, 189, 248, 235),  # Electric Cyan border
        width=6,
    )

    # 2. Inner glow border
    draw.rounded_rectangle(
        [margin + 8, margin + 8, 256 - margin - 8, 256 - margin - 8],
        radius=46,
        outline=(30, 48, 77, 180),
        width=2,
    )

    # 3. Geometric Web / Data Nodes Emblem
    # Central hub coordinates
    cx, cy = 128, 128

    # Outer network node positions
    nodes = [
        (128, 64),   # Top
        (192, 128),  # Right
        (128, 192),  # Bottom
        (64, 128),   # Left
        (82, 82),    # Top-Left
        (174, 82),   # Top-Right
        (174, 174),  # Bottom-Right
        (82, 174),   # Bottom-Left
    ]

    # Connecting web rays (Cyan glow)
    for nx, ny in nodes:
        draw.line([(cx, cy), (nx, ny)], fill=(34, 114, 168, 190), width=3)

    # Hexagonal / octagonal data web outer ring
    for i in range(len(nodes)):
        p1 = nodes[i]
        p2 = nodes[(i + 1) % len(nodes)]
        draw.line([p1, p2], fill=(56, 189, 248, 160), width=3)

    # Draw outer peripheral data nodes
    for nx, ny in nodes:
        draw.ellipse([nx - 6, ny - 6, nx + 6, ny + 6], fill=(56, 189, 248, 255), outline=(255, 255, 255, 200), width=1)

    # Central Core Radar / Beacon
    # Outer core ring (Emerald glow)
    draw.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(16, 185, 129, 60), outline=(16, 185, 129, 220), width=3)

    # Core diamond
    diamond = [
        (cx, cy - 18),
        (cx + 18, cy),
        (cx, cy + 18),
        (cx - 18, cy),
    ]
    draw.polygon(diamond, fill=(56, 189, 248, 255), outline=(255, 255, 255, 255))

    # Core center white spark
    draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=(255, 255, 255, 255))

    # Save as high-res PNG
    img.save(PNG_PATH, format="PNG")

    # Save as Windows multi-resolution .ico
    img.save(
        ICO_PATH,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )

    print(f"[+] Successfully generated custom logo icon: {ICO_PATH}")
    return ICO_PATH


def create_desktop_shortcuts(ico_path: Path):
    """Create zero-terminal desktop shortcut with icon on user's Desktop folders."""
    python_dir = Path(sys.executable).parent
    pythonw_exe = python_dir / "pythonw.exe"
    if not pythonw_exe.exists():
        pythonw_exe = Path(sys.executable)

    gui_script = PROJECT_ROOT / "desktop_gui.py"

    desktop_paths = [
        Path(os.path.expanduser("~")) / "OneDrive" / "Belgeler" / "Ekler" / "Masaüstü",
        Path(os.path.expanduser("~")) / "Desktop",
        Path(os.environ.get("USERPROFILE", "")) / "Desktop",
    ]

    # Deduplicate paths
    unique_paths = []
    for p in desktop_paths:
        if p.exists() and p not in unique_paths:
            unique_paths.append(p)

    created_links = []
    for d_path in unique_paths:
        lnk_path = d_path / "ScrapeAgent.lnk"
        ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{lnk_path}')
$Shortcut.TargetPath = '{pythonw_exe}'
$Shortcut.Arguments = '"{gui_script}"'
$Shortcut.WorkingDirectory = '{PROJECT_ROOT}'
$Shortcut.IconLocation = '{ico_path},0'
$Shortcut.Description = 'ScrapeAgent - Autonomous Web Scraping Desktop App'
$Shortcut.WindowStyle = 1
$Shortcut.Save()
"""
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            created_links.append(lnk_path)
            print(f"[SUCCESS] Created Desktop Shortcut at: {lnk_path}")
        else:
            print(f"[ERROR] PowerShell failed to create shortcut at {lnk_path}: {res.stderr}")

    return created_links


if __name__ == "__main__":
    icon = create_agent_icon()
    create_desktop_shortcuts(icon)
