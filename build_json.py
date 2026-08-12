import os
import re
import json
import shutil
import zipfile
import hashlib
from datetime import datetime

import pysubs2


# ============================================================
# CONFIGURATION
# ============================================================

SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_FOLDER, "config.txt")

def load_config():
    """
    Read project_folder and video_folder from config.txt.

    Expected format:

        project_folder=C:\Projects\MyShow
        video_folder=D:\Media\MyShow
    """

    if not os.path.isfile(CONFIG_FILE):
        print("ERROR: config.txt was not found.")
        print()
        print(f"Expected location:")
        print(f"  {CONFIG_FILE}")
        return None

    config = {}

    with open(
        CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            line = line.strip()

            # Ignore blank lines and comments
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip()

            config[key] = value

    project_folder = config.get("project_folder")
    video_folder = config.get("video_folder")

    if not project_folder:
        print("ERROR: project_folder is missing from config.txt.")
        return None

    if not video_folder:
        print("ERROR: video_folder is missing from config.txt.")
        return None

    return (
        os.path.abspath(project_folder),
        os.path.abspath(video_folder)
    )


# ============================================================
# FILE HELPERS
# ============================================================

def get_file_hash(path):
    """
    Return a SHA-256 hash of a file.
    """

    sha256 = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def files_are_identical(path1, path2):
    """
    Compare two files by size first, then by SHA-256 hash.
    """

    if os.path.getsize(path1) != os.path.getsize(path2):
        return False

    return get_file_hash(path1) == get_file_hash(path2)


def format_file_size(size):
    """
    Format bytes into a readable size.
    """

    if size < 1024:
        return f"{size} B"

    if size < 1024 ** 2:
        return f"{size / 1024:.1f} KB"

    if size < 1024 ** 3:
        return f"{size / (1024 ** 2):.1f} MB"

    return f"{size / (1024 ** 3):.1f} GB"


def format_modified_date(path):
    """
    Return a readable last-modified date.
    """

    timestamp = os.path.getmtime(path)

    return datetime.fromtimestamp(
        timestamp
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# FILENAME HELPERS
# ============================================================

def get_episode_info(filename):
    """
    Extract season, episode, and title from:

        S01E01.The.Crawling.Eye.srt

    Returns:

        {
            "season": 1,
            "episode": 1,
            "title": "The Crawling Eye"
        }

    or None if the filename doesn't match.
    """

    base = os.path.splitext(filename)[0]

    match = re.match(
        r"^S(\d{2})E(\d{2})\.(.+)$",
        base,
        re.IGNORECASE
    )

    if not match:
        return None

    season = int(match.group(1))
    episode = int(match.group(2))
    title = match.group(3).replace(".", " ")

    return {
        "season": season,
        "episode": episode,
        "title": title
    }


# ============================================================
# TIMESTAMP HELPERS
# ============================================================

def timestamp_to_string(milliseconds):
    """
    Convert pysubs2 milliseconds to:

        HH:MM:SS,mmm
    """

    total_ms = int(milliseconds)

    hours = total_ms // 3_600_000
    total_ms %= 3_600_000

    minutes = total_ms // 60_000
    total_ms %= 60_000

    seconds = total_ms // 1_000
    ms = total_ms % 1_000

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def timestamp_to_milliseconds(timestamp):
    """
    Convert SRT timestamp to milliseconds.
    """

    match = re.match(
        r"(\d{2}):(\d{2}):(\d{2}),(\d{3})",
        timestamp
    )

    if not match:
        return 0

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    milliseconds = int(match.group(4))

    return (
        hours * 3_600_000
        + minutes * 60_000
        + seconds * 1_000
        + milliseconds
    )


# ============================================================
# ASK USER ABOUT DIFFERENCE
# ============================================================

def ask_about_difference(old_path, new_path):
    """
    Show information about the existing video-folder file
    and the new project-folder file.

    Returns True if the user wants to copy the new file.
    """

    old_size = os.path.getsize(old_path)
    new_size = os.path.getsize(new_path)

    old_date = format_modified_date(old_path)
    new_date = format_modified_date(new_path)

    print()
    print("=" * 70)
    print("SUBTITLE DIFFERENCE FOUND")
    print("=" * 70)

    print()
    print("EXISTING FILE (video folder):")
    print(f"  {old_path}")
    print(f"  Size:     {format_file_size(old_size)}")
    print(f"  Modified: {old_date}")

    print()
    print("NEW FILE (project folder):")
    print(f"  {new_path}")
    print(f"  Size:     {format_file_size(new_size)}")
    print(f"  Modified: {new_date}")

    print()
    print("The files have different contents.")

    while True:

        answer = input(
            "Copy the new file over the existing file? [Y/N]: "
        ).strip().lower()

        if answer in ("y", "yes"):
            return True

        if answer in ("n", "no"):
            return False

        print("Please enter Y or N.")


# ============================================================
# MAIN
# ============================================================

def main():
    config = load_config()
    if config is None:
        return 1

    project_folder, video_folder = config

    subtitle_folder = os.path.join(
        project_folder,
        "subtitles"
    )

    print()
    print("=" * 70)
    print("SUBTITLE SYNC / BUILD")
    print("=" * 70)
    print()

    print("Project folder:")
    print(f"  {project_folder}")

    print()
    print("Subtitle folder:")
    print(f"  {subtitle_folder}")

    print()
    print("Video folder:")
    print(f"  {video_folder}")

    print()

    # --------------------------------------------------------
    # Validate folders
    # --------------------------------------------------------

    if not os.path.isdir(project_folder):
        print("ERROR: Project folder does not exist.")
        return 1

    if not os.path.isdir(subtitle_folder):
        print("ERROR: Subtitle folder does not exist.")
        return 1

    if not os.path.isdir(video_folder):
        print("ERROR: Video folder does not exist.")
        return 1

    # --------------------------------------------------------
    # Find SRT files
    # --------------------------------------------------------

    subtitle_files = [
        filename
        for filename in os.listdir(subtitle_folder)
        if filename.lower().endswith(".srt")
    ]

    subtitle_files.sort(key=str.lower)

    print(
        f"Found {len(subtitle_files)} SRT files."
    )

    print()
    print("=" * 70)
    print("CHECKING SUBTITLE FILES")
    print("=" * 70)

    copied_files = []
    skipped_identical = []
    declined_files = []
    missing_files = []
    invalid_files = []

    # ========================================================
    # COMPARE FILES
    # ========================================================

    for filename in subtitle_files:

        info = get_episode_info(filename)

        if info is None:

            print()
            print(
                f"SKIPPING INVALID FILENAME: {filename}"
            )

            invalid_files.append(filename)
            continue

        new_path = os.path.join(
            subtitle_folder,
            filename
        )

        season_folder = os.path.join(
            video_folder,
            f"Season {info['season']:02d}"
        )

        old_path = os.path.join(
            season_folder,
            filename
        )

        # ----------------------------------------------------
        # Season folder missing
        # ----------------------------------------------------

        if not os.path.isdir(season_folder):

            print()
            print(
                f"MISSING SEASON FOLDER:"
                f" Season {info['season']:02d}"
            )

            print(
                f"  {filename}"
            )

            missing_files.append(filename)
            continue

        # ----------------------------------------------------
        # Subtitle doesn't exist in video folder
        # ----------------------------------------------------

        if not os.path.isfile(old_path):

            print()
            print(
                f"MISSING - copying:"
            )

            print(
                f"  {filename}"
            )

            shutil.copy2(
                new_path,
                old_path
            )

            copied_files.append(filename)
            continue

        # ----------------------------------------------------
        # Compare contents
        # ----------------------------------------------------

        if files_are_identical(
            new_path,
            old_path
        ):

            print(
                f"IDENTICAL: {filename}"
            )

            skipped_identical.append(filename)
            continue

        # ----------------------------------------------------
        # Files differ
        # ----------------------------------------------------

        if ask_about_difference(
            old_path,
            new_path
        ):

            shutil.copy2(
                new_path,
                old_path
            )

            print()
            print(
                "COPIED."
            )

            copied_files.append(filename)

        else:

            print()
            print(
                "NOT COPIED."
            )

            declined_files.append(filename)

    # ========================================================
    # CREATE METADATA.JSON
    # ========================================================

    print()
    print("=" * 70)
    print("CREATING METADATA.JSON")
    print("=" * 70)

    metadata = []

    for filename in subtitle_files:

        info = get_episode_info(filename)

        if info is None:
            continue

        metadata.append({
            "season": info["season"],
            "episode": info["episode"],
            "title": info["title"],
            "file": f"subtitles/{filename}",
            "source": "",
            "quality": "",
            "notes": ""
        })

    metadata.sort(
        key=lambda item: (
            item["season"],
            item["episode"]
        )
    )

    metadata_path = os.path.join(
        project_folder,
        "metadata.json"
    )

    with open(
        metadata_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"Created: {metadata_path}"
    )

    # ========================================================
    # CREATE SEARCH-INDEX.JSON
    # ========================================================

    print()
    print("=" * 70)
    print("CREATING SEARCH-INDEX.JSON")
    print("=" * 70)

    search_index = []

    for filename in subtitle_files:

        info = get_episode_info(filename)

        if info is None:
            continue

        subtitle_path = os.path.join(
            subtitle_folder,
            filename
        )

        try:

            subs = pysubs2.load(
                subtitle_path,
                encoding="utf-8"
            )

        except Exception as e:

            print()
            print(
                f"ERROR reading {filename}: {e}"
            )

            continue

        for event in subs:

            text = event.plaintext.strip()

            if not text:
                continue

            search_index.append({
                "season": info["season"],
                "episode": info["episode"],
                "title": info["title"],
                "file": f"subtitles/{filename}",
                "time": timestamp_to_string(
                    event.start
                ),
                "text": text
            })

    search_index.sort(
        key=lambda item: (
            item["season"],
            item["episode"],
            timestamp_to_milliseconds(
                item["time"]
            )
        )
    )

    search_index_path = os.path.join(
        project_folder,
        "search-index.json"
    )

    with open(
        search_index_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            search_index,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"Created: {search_index_path}"
    )

    # ========================================================
    # CREATE SUBTITLES.ZIP
    # ========================================================

    print()
    print("=" * 70)
    print("CREATING SUBTITLES.ZIP")
    print("=" * 70)

    zip_path = os.path.join(
        project_folder,
        "subtitles.zip"
    )

    if os.path.exists(zip_path):
        os.remove(zip_path)

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED
    ) as zip_file:

        for filename in subtitle_files:

            full_path = os.path.join(
                subtitle_folder,
                filename
            )

            archive_path = os.path.join(
                "subtitles",
                filename
            )

            # ZIP paths always use forward slashes
            archive_path = archive_path.replace(
                os.sep,
                "/"
            )

            zip_file.write(
                full_path,
                archive_path
            )

    print(
        f"Created: {zip_path}"
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    print(
        f"SRT files found : {len(subtitle_files)}"
    )

    print(
        f"Identical       : {len(skipped_identical)}"
    )

    print(
        f"Copied          : {len(copied_files)}"
    )

    print(
        f"Declined        : {len(declined_files)}"
    )

    print(
        f"Missing         : {len(missing_files)}"
    )

    print(
        f"Invalid names   : {len(invalid_files)}"
    )

    # --------------------------------------------------------
    # List files that were declined
    # --------------------------------------------------------

    if declined_files:

        print()
        print("=" * 70)
        print("FILES NOT COPIED")
        print("=" * 70)

        for filename in declined_files:
            print(filename)

    # --------------------------------------------------------
    # List missing season folders
    # --------------------------------------------------------

    if missing_files:

        print()
        print("=" * 70)
        print("FILES WITH MISSING SEASON FOLDERS")
        print("=" * 70)

        for filename in missing_files:
            print(filename)

    print()
    print("Build complete.")
    print()

    return 0


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    raise SystemExit(main())
