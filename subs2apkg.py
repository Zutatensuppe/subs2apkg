import argparse
import random
import subprocess
import pysubs2
import genanki
from pathlib import Path

OFFSET_AUDIO_START = -250
OFFSET_AUDIO_END = 250
OFFSET_IMAGE = 0

model = genanki.Model(
    1740692504,
    "japanese + subs2srs",
    fields=[
        {"name": "SequenceMarker"},
        {"name": "Expression"},
        {"name": "Reading"},
        {"name": "Meaning"},
        {"name": "Audio"},
        {"name": "Image"},
    ],
    templates=[
        {
            "name": "Card 1",
            "qfmt": "<div class=jp> {{Expression}} </div>{{Audio}}{{Image}}",
            "afmt": """{{FrontSide}}

<hr id=answer>

<div class=jp> {{furigana:Reading}} </div><br>
{{Meaning}}""",
        },
    ],
    css=""".card {
 font-family: arial;
 font-size: 20px;
 text-align: center;
 color: black;
 background-color: white;
}
.jp { font-size: 30px }
.win .jp { font-family: "MS Mincho", "ＭＳ 明朝"; }
.mac .jp { font-family: "Hiragino Mincho Pro", "ヒラギノ明朝 Pro"; }
.linux .jp { font-family: "Kochi Mincho", "東風明朝"; }
.mobile .jp { font-family: "Hiragino Mincho ProN"; }""",
)


def audio_ref(f: Path):
    return f"[sound:{f.name}]"


def image_ref(f: Path):
    return f'<img src="{f.name}">'


def ffmpegtime(t):
    return pysubs2.time.ms_to_str(t, fractions=True)


def middle(start, end):
    return start + ((end - start) / 2)


def create_audio(video_path, audio_path, line):
    if not audio_path.exists():
        subprocess.run(
            [
                "ffmpeg",
                "-n",
                "-ss",
                ffmpegtime(line.start + OFFSET_AUDIO_START),
                "-to",
                ffmpegtime(line.end + OFFSET_AUDIO_END),
                "-i",
                video_path,
                # no video
                "-vn",
                # audio settings
                "-ar",
                "44100",
                "-ac",
                "2",
                "-ab",
                "96k",
                "-acodec",
                "mp3",
                audio_path,
            ],
            capture_output=True,
            check=True,
        )
    return audio_path


def create_image(video_path, image_path, line):
    if not image_path.exists():
        subprocess.run(
            [
                "ffmpeg",
                "-n",
                "-ss",
                ffmpegtime(middle(line.start, line.end) + OFFSET_IMAGE),
                "-i",
                video_path,
                "-vframes",
                "1",
                image_path,
            ],
            capture_output=True,
            check=True,
        )
    return image_path


def create_notes(subs, video_path: Path, tmp_path: Path):
    media_files = []
    notes = []

    for idx, line in enumerate(subs, start=1):
        print(f"{line!r}")
        audio_path = Path(f"{tmp_path}/{idx}.mp3")
        image_path = Path(f"{tmp_path}/{idx}.jpg")

        media_files.extend(
            [
                create_audio(video_path, audio_path, line),
                create_image(video_path, image_path, line),
            ]
        )
        notes.append(
            genanki.Note(
                model=model,
                fields=[
                    f"{idx}",  # SequenceMarker
                    line.text,  # Expression
                    "",  # Reading
                    "",  # Meaning
                    audio_ref(audio_path),
                    image_ref(image_path),
                ],
            )
        )
    return notes, media_files


def main(video: str, sub: str, apkg: str, name: str):
    video_path = Path(video)
    subs_path = Path(sub or video_path.with_suffix(".ass"))
    apkg_path = Path(apkg or video_path.with_suffix(".apkg"))
    name = name or str(video_path.with_suffix(""))
    tmp_path = video_path.with_suffix("")

    if not tmp_path.is_dir():
        tmp_path.mkdir()

    subs = pysubs2.load(subs_path)
    notes, media_files = create_notes(subs, video_path, tmp_path)

    deck = genanki.Deck(
        deck_id=random.randrange(1 << 30, 1 << 31),
        name=name
    )
    for note in notes:
        deck.add_note(note)
    apkg = genanki.Package(deck)
    apkg.media_files = media_files
    apkg.write_to_file(apkg_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--in", dest="video", help="Video file", required=True)
    parser.add_argument("-s", "--subs", dest="sub", help="Subtitle file")
    parser.add_argument("-o", "--out", dest="apkg", help="Output anki deck file")
    parser.add_argument("-n", "--name", dest="name", help="Name of anki deck")
    args = parser.parse_args()
    main(args.video, args.sub, args.apkg, args.name)

