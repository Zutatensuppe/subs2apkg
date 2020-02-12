# subs2apkg
script to convert video+subs to anki deck

## Requirements

- pipenv
- ffmpeg

```
git clone git@github.com:Zutatensuppe/subs2apkg.git
cd subs2apkg
pipenv install
pipenv run subs2apkg.py -h
```

## Usage

```
usage: subs2apkg.py [-h] -i VIDEO [-s SUB] [-o APKG] [-n NAME]

optional arguments:
  -h, --help            show this help message and exit
  -i VIDEO, --in VIDEO  Video file
  -s SUB, --subs SUB    Subtitle file
  -o APKG, --out APKG   Output anki deck file
  -n NAME, --name NAME  Name of anki deck
```

Only video file is required, in that case the subtitle file, output file and name are determined from the video file.

## Example

```
$ tree -L 1
.
├── subs2apkg.py
├── Pipfile
├── Pipfile.lock
├── Video_001.ass
└── Video_001.mp4

$ pipenv run subs2apkg.py -i Video_001.mp4

$ tree -L 1
.
├── subs2apkg.py
├── Pipfile
├── Pipfile.lock
├── Video_001        # directory containing the temporary files created from video file
├── Video_001.apkg   # the anki deck
├── Video_001.ass
└── Video_001.mp4

```

