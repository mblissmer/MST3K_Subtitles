#!/usr/bin/env python3

import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent

SUBTITLE_DIR = ROOT / "subtitles"

METADATA_FILE = ROOT / "metadata.json"
SEARCH_FILE = ROOT / "search-index.json"
ZIP_FILE = ROOT / "subtitles.zip"

filename_re = re.compile(
    r"^S(?P<season>\d+)E(?P<episode>\d+)\.(?P<title>.+)\.srt$",
    re.IGNORECASE,
)

timestamp_re = re.compile(
    r"(\d\d:\d\d:\d\d,\d\d\d)\s+-->\s+(\d\d:\d\d:\d\d,\d\d\d)"
)


def parse_srt(path):
    """
    Returns a list of subtitle entries:
    {
        "time": "...",
        "text": "..."
    }
    """

    entries = []

    with open(path, encoding="utf-8", errors="ignore") as f:
        lines = [line.rstrip() for line in f]

    i = 0

    while i < len(lines):
        line = lines[i].strip()
        # Subtitle number
        if line.isdigit():
            i += 1
            continue
        m = timestamp_re.match(line)
        if not m:
            i += 1
            continue
        start_time = m.group(1)
        i += 1
        dialogue = []
        while i < len(lines):
            line = lines[i].strip()
            if line == "":
                break
            dialogue.append(line)
            i += 1
        text = " ".join(dialogue).strip()
        if text:
            entries.append({
                "time": start_time,
                "text": text
            })
        i += 1

    return entries


metadata = []
search_index = []

print("Scanning subtitles...\n")

subtitle_files = sorted(SUBTITLE_DIR.glob("*.srt"))
for path in subtitle_files:
    m = filename_re.match(path.name)
    if not m:
        print(f"Skipping {path.name}")
        continue
    season = int(m["season"])
    episode = int(m["episode"])
    title = m["title"].replace(".", " ")
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    print(f"S{season:02}E{episode:02}  {title}")
    metadata.append({
        "season": season,
        "episode": episode,
        "title": title,
        "file": rel
    })
    for entry in parse_srt(path):

        search_index.append({
            "season": season,
            "episode": episode,
            "title": title,
            "file": rel,
            "time": entry["time"],
            "text": entry["text"]
        })
print()

print("Writing metadata.json...")
with open(METADATA_FILE, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print("Writing search-index.json...")
with open(SEARCH_FILE, "w", encoding="utf-8") as f:
    json.dump(search_index, f, indent=2, ensure_ascii=False)

print("Creating subtitles.zip...")
with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as z:
    for path in subtitle_files:
        z.write(path, arcname=path.name)

print()
print(f"{len(metadata)} subtitle files")
print(f"{len(search_index)} searchable subtitle entries")
print("Done.")
