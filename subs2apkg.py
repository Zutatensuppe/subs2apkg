import argparse
import random
import subprocess
import pysubs2
import genanki
import re
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


def clean_text(t):
    return re.sub(r"\{\\[^}]+\}|\\N", "", t)


def audio_ref(f: Path):
    return f"[sound:{f.name}]"


def image_ref(f: Path):
    return f'<img src="{f.name}">'


def ffmpegtime(t):
    return pysubs2.time.ms_to_str(t, fractions=True)


def middle(start, end):
    return start + ((end - start) / 2)


def create_audio(video_path, audio_path, line, offset):
    if not audio_path.exists():
        cmd = [
            "ffmpeg",
            "-n",
            "-ss",
            ffmpegtime(line.start + offset + OFFSET_AUDIO_START),
            "-to",
            ffmpegtime(line.end + offset + OFFSET_AUDIO_END),
            "-i",
            str(video_path),
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
            str(audio_path),
        ]
        print(" ".join(cmd))
        subprocess.run(cmd, capture_output=True)
    return audio_path


def create_image(
    video_path, image_path, line, offset, cutbottom, cuttop, cutleft, cutright
):
    if not image_path.exists():
        cmd = [
            "ffmpeg",
            "-n",
            "-ss",
            ffmpegtime(middle(line.start + offset, line.end + offset) + OFFSET_IMAGE),
            "-i",
            str(video_path),
            "-vframes",
            "1",
        ]
        if cutbottom or cuttop or cutleft or cutright:
            cmd.extend(
                [
                    "-filter:v",
                    f"crop=in_w-{cutright}-{cutleft}:in_h-{cuttop}-{cutbottom}:{cutleft}:{cuttop}",
                ]
            )
        cmd.append(str(image_path))
        # print(" ".join(cmd))
        subprocess.run(cmd, capture_output=True)
    return image_path


def create_notes(
    subs, video_path: Path, tmp_path: Path, offset, cutbottom, cuttop, cutleft, cutright
):
    media_files = []
    notes = []

    # combine lines that have same start/end
    subs_2 = []
    last = None
    for line in subs:
        if not last or last.start != line.start or last.end != line.end:
            subs_2.append(line)
        else:
            last.text = f"{last.text} {line.text}"
        last = line

    for idx, line in enumerate(subs_2, start=1):
        print(f"{line!r}")
        audio_path = Path(f"{tmp_path}/{idx}.mp3")
        image_path = Path(f"{tmp_path}/{idx}.jpg")

        audio_file = create_audio(video_path, audio_path, line, offset)
        image_file = create_image(
            video_path, image_path, line, offset, cutbottom, cuttop, cutleft, cutright
        )
        if not audio_file.exists() or not image_file.exists():
            print("skipped")
            continue

        media_files.extend([audio_file, image_file])
        notes.append(
            genanki.Note(
                model=model,
                fields=[
                    f"{idx}",  # SequenceMarker
                    clean_text(line.text),  # Expression
                    "",  # Reading
                    "",  # Meaning
                    audio_ref(audio_path),
                    image_ref(image_path),
                ],
            )
        )
    return notes, media_files


def main(args):
    video = args.video
    sub = args.sub
    apkg = args.apkg
    name = args.name
    offset = args.offset
    cutbottom = args.cutbottom
    cuttop = args.cuttop
    cutleft = args.cutleft
    cutright = args.cutright

    video_path = Path(video)
    subs_path = Path(sub or video_path.with_suffix(".ass"))
    apkg_path = Path(apkg or video_path.with_suffix(".apkg"))
    name = name or str(video_path.with_suffix("").name)
    tmp_path = video_path.with_suffix("")

    if not tmp_path.is_dir():
        tmp_path.mkdir()

    subs = pysubs2.load(subs_path)
    notes, media_files = create_notes(
        subs, video_path, tmp_path, offset, cutbottom, cuttop, cutleft, cutright
    )

    deck = genanki.Deck(deck_id=random.randrange(1 << 30, 1 << 31), name=name)

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
    parser.add_argument(
        "--offset",
        dest="offset",
        type=int,
        default=0,
        help="Subtitle time offset in ms",
    )
    parser.add_argument(
        "--cutbottom",
        dest="cutbottom",
        type=int,
        default=0,
        help="Cut bottom pixels from created images",
    )
    parser.add_argument(
        "--cuttop",
        dest="cuttop",
        type=int,
        default=0,
        help="Cut top pixels from created images",
    )
    parser.add_argument(
        "--cutleft",
        dest="cutleft",
        type=int,
        default=0,
        help="Cut left pixels from created images",
    )
    parser.add_argument(
        "--cutright",
        dest="cutright",
        type=int,
        default=0,
        help="Cut right pixels from created images",
    )
    args = parser.parse_args()
    main(args)
