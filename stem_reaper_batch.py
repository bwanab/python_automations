#!/usr/bin/env python3
"""
stem_reaper_batch.py

Batch-processes a folder of live-band recordings:

  1. Separates each file into stems using audio-separator (a Demucs
     model, via the same models behind Ultimate Vocal Remover). The
     default model htdemucs_6s.yaml produces six stems: vocals, drums,
     bass, other, guitar, piano. Pass --model htdemucs_ft.yaml for the
     4-stem model (vocals/drums/bass/other) instead.
  2. Builds a REAPER project (.rpp) per song, with each stem on its own
     track. Vocals are attenuated and every other stem is boosted,
     using each track's VOLPAN (fader) setting rather than baking gain
     into the audio -- so you can still nudge levels by ear in REAPER
     afterwards.

Requirements (install once):
    pip install "audio-separator[cpu]" reathon soundfile audioread

    (Use "audio-separator[coreml]" instead of "[cpu]" on Apple Silicon if
    you want Core ML acceleration; check the project's README for the
    current extra name, as this changes between releases. "[cpu]" always
    works.)

Usage:
    python stem_reaper_batch.py /path/to/recordings /path/to/output \
        --vocal-db -6 --other-db 3

    --vocal-db is how many dB to change the vocals track by (negative = quieter).
    --other-db is how many dB to change every non-vocal track by (positive = louder).
    --model    audio-separator model filename (default: htdemucs_6s.yaml).
    --template REAPER project template. Bare filenames are looked up in
               ~/Library/Application Support/REAPER/ProjectTemplates/.
               Defaults to default_template.RPP; pass "" to disable.
               Stem tracks are appended to the template's existing tracks
               (routing to any bus tracks is manual, done in REAPER).

Output layout (6-stem default):
    output/
      SongName/
        SongName_vocals.wav
        SongName_drums.wav
        SongName_bass.wav
        SongName_other.wav
        SongName_guitar.wav
        SongName_piano.wav
        SongName.rpp        <- open this in REAPER

Notes:
    - Demucs stem separation on a live recording (bleed between mics,
      stage volume, etc.) will be less clean than on a studio multitrack.
      Expect some manual touch-up per song, which is exactly why this
      script hands you an editable multitrack project instead of a
      pre-baked mixdown.
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from audio_separator.separator import Separator
except ImportError:
    print("Missing dependency: pip install \"audio-separator[cpu]\"", file=sys.stderr)
    raise

try:
    from reathon.nodes import Project, Track, Item, Source
except ImportError:
    print("Missing dependency: pip install reathon", file=sys.stderr)
    raise


# Demucs model → stem list. htdemucs_6s adds Guitar and Piano; htdemucs_ft is
# the 4-stem model. See `audio-separator --list_models --list_filter=drums`.
MODEL_STEMS = {
    "htdemucs_6s.yaml": ["Vocals", "Drums", "Bass", "Other", "Guitar", "Piano"],
    "htdemucs_ft.yaml": ["Vocals", "Drums", "Bass", "Other"],
}
DEFAULT_MODEL = "htdemucs_6s.yaml"
DEFAULT_STEMS = MODEL_STEMS[DEFAULT_MODEL]
AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".flac", ".mp3", ".m4a"}

DEFAULT_TEMPLATE_DIR = Path.home() / "Library/Application Support/REAPER/ProjectTemplates"
DEFAULT_TEMPLATE_NAME = "default_template.RPP"


def db_to_gain(db: float) -> float:
    """Convert a dB offset to a linear gain multiplier (REAPER VOLPAN uses 1.0 = 0dB)."""
    return 10 ** (db / 20)


def get_duration_seconds(path: Path) -> float:
    """Audio duration lookup for the REAPER item LENGTH. Raises if unreadable."""
    try:
        import soundfile as sf
        info = sf.info(str(path))
        return info.frames / info.samplerate
    except Exception as e_sf:
        try:
            import wave
            with wave.open(str(path), "rb") as wf:
                return wf.getnframes() / wf.getframerate()
        except Exception as e_wave:
            raise RuntimeError(
                f"could not read duration of {path}: soundfile={e_sf}; wave={e_wave}"
            )


def separate_file(separator: Separator, audio_path: Path, song_dir: Path, stem_names: list) -> dict:
    """Run stem separation on one file, returns {stem_name: Path} for whatever was found."""
    song_dir.mkdir(parents=True, exist_ok=True)

    stem = audio_path.stem
    output_names = {name: f"{stem}_{name.lower()}" for name in stem_names}

    produced = separator.separate(str(audio_path), custom_output_names=output_names)

    # Separator writes into the output_dir it was constructed with (mutating
    # separator.output_dir after construction is not honored in 0.47.0). Locate
    # each produced file and move it into song_dir.
    search_dirs = [song_dir, Path(separator.output_dir or "."), Path.cwd()]
    result = {}
    for f in produced:
        name_only = Path(f).name
        src = next((d / name_only for d in search_dirs if (d / name_only).exists()), None)
        if src is None:
            print(f"  Warning: produced file {name_only} not found in {search_dirs}", file=sys.stderr)
            continue
        dest = song_dir / name_only
        if src.resolve() != dest.resolve():
            src.replace(dest)

        tokens = {t.lower() for t in re.split(r"[^A-Za-z0-9]+", dest.stem) if t}
        for name in stem_names:
            if name.lower() in tokens:
                result[name] = dest
                break
    return result


def _build_tracks(stem_files: dict, vocal_db: float, other_db: float, stem_names: list) -> list:
    """Build a list of reathon Track nodes for the stems that were produced."""
    vocal_gain = db_to_gain(vocal_db)
    other_gain = db_to_gain(other_db)
    tracks = []
    for name in stem_names:
        if name not in stem_files:
            print(f"  Warning: no {name} stem found, skipping that track", file=sys.stderr)
            continue

        audio_path = stem_files[name].resolve()  # absolute so REAPER can find it
        gain = vocal_gain if name == "Vocals" else other_gain
        try:
            duration = get_duration_seconds(audio_path)
        except RuntimeError as exc:
            print(f"  Warning: skipping {name} track ({exc})", file=sys.stderr)
            continue

        track = Track(
            Item(
                Source(file=str(audio_path)),
                position=0,
                length=round(duration, 6),
            ),
            name=name,
        )
        # VOLPAN: volume(linear, 1.0=0dB) pan(-1..1) panlaw(-1=project default)
        track.props.append(["VOLPAN", f"{gain:.6f} 0 -1"])
        tracks.append(track)
    return tracks


def _serialize_tracks(tracks: list) -> str:
    """Render Track nodes to REAPER .rpp text without a REAPER_PROJECT wrapper."""
    if not tracks:
        return ""
    scratch = Project()
    for track in tracks:
        scratch.traverse(track)  # appends the <TRACK ...> block to scratch.string
    return scratch.string


def build_reaper_project(
    stem_files: dict,
    vocal_db: float,
    other_db: float,
    project_path: Path,
    stem_names: list,
    template_path: Path | None = None,
) -> None:
    tracks = _build_tracks(stem_files, vocal_db, other_db, stem_names)

    if template_path is not None:
        template_text = template_path.read_text(encoding="utf-8")
        tracks_text = _serialize_tracks(tracks)
        # Splice tracks in just before the template's outer closing '>'.
        close_idx = template_text.rstrip().rfind(">")
        merged = template_text[:close_idx] + tracks_text + template_text[close_idx:]
        project_path.write_text(merged, encoding="utf-8")
        return

    project = Project()
    project.name = 'REAPER_PROJECT 0.1 "7.0" 0'
    for track in tracks:
        project.add(track)
    project.write(str(project_path))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_dir", type=Path, help="Folder of source recordings")
    parser.add_argument("output_dir", type=Path, help="Folder to write stems + .rpp projects into")
    parser.add_argument("--vocal-db", type=float, default=-6.0, help="dB change for vocals (default: -6)")
    parser.add_argument("--other-db", type=float, default=3.0, help="dB change for every non-vocal stem (default: +3)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"audio-separator model filename (default: {DEFAULT_MODEL})")
    parser.add_argument(
        "--template",
        default=DEFAULT_TEMPLATE_NAME,
        help=(
            f"REAPER project template filename or path (default: {DEFAULT_TEMPLATE_NAME}). "
            f"Bare filenames are looked up in {DEFAULT_TEMPLATE_DIR}. "
            "Pass an empty string to disable and generate a bare project."
        ),
    )
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        print(f"Input folder not found: {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    audio_files = sorted(
        p for p in args.input_dir.iterdir()
        if p.suffix.lower() in AUDIO_EXTENSIONS
    )
    if not audio_files:
        print(f"No audio files found in {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    stem_names = MODEL_STEMS.get(args.model, DEFAULT_STEMS)
    if args.model not in MODEL_STEMS:
        print(f"Unknown model {args.model}, assuming stems: {stem_names}", file=sys.stderr)

    template_path = None
    if args.template:
        p = Path(args.template).expanduser()
        if not p.is_absolute() and "/" not in args.template and "\\" not in args.template:
            p = DEFAULT_TEMPLATE_DIR / args.template
        if p.exists():
            template_path = p
            print(f"Using template {template_path}")
        else:
            print(f"Template not found at {p}, generating bare projects instead", file=sys.stderr)

    print(f"Loading model {args.model} ...")
    separator = Separator(output_format="WAV", output_dir=str(args.output_dir))
    separator.load_model(model_filename=args.model)

    for audio_path in audio_files:
        print(f"Processing {audio_path.name} ...")
        song_dir = args.output_dir / audio_path.stem
        try:
            stem_files = separate_file(separator, audio_path, song_dir, stem_names)
        except Exception as exc:
            print(f"  FAILED to separate {audio_path.name}: {exc}", file=sys.stderr)
            continue

        if len(stem_files) < len(stem_names):
            print(f"  Only matched stems: {list(stem_files)}")

        project_path = song_dir / f"{audio_path.stem}.rpp"
        build_reaper_project(stem_files, args.vocal_db, args.other_db, project_path, stem_names, template_path)
        print(f"  -> {project_path}")

    print("Done.")


if __name__ == "__main__":
    main()
    