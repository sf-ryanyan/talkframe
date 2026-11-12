# Voice options (text → speech, or voice clone)

Pick in this order unless the user chose: user's own recording > cloned voice > a stock voice that fits the person in the photo (gender, age, tone).

| Option | Key | Chinese | Clone | Command |
|---|---|---|---|---|
| User recording | — | ✓ | — | `tf_media.py audio --in my.m4a --outdir {work}/aud` |
| fal MiniMax speech-02-hd | FAL_KEY | strong | ✓ (`tf_fal.py clone`) | `tf_fal.py tts --text-file script.txt --voice-id <id> --out {work}/tts.mp3` |
| ListenHub | ListenHub key | strong | ✓ | `listenhub openapi speech --script ... --speaker-id ... --json` |
| Edge TTS | none (free, online) | good | ✗ | `edge-tts --voice zh-CN-YunxiNeural --rate=-5% --file script.txt --write-media {work}/tts.mp3` |
| Local TTS (CosyVoice, IndexTTS, GPT-SoVITS…) | none | varies | ✓ | follow its README, export WAV |

Edge voices often used for Mandarin: `zh-CN-XiaoxiaoNeural` (female), `zh-CN-XiaoyiNeural` (female), `zh-CN-YunxiNeural` (male), `zh-CN-YunjianNeural` (male); Taiwan `zh-TW-HsiaoChenNeural`; Cantonese `zh-HK-HiuGaaiNeural`. List all: `edge-tts --list-voices`.

MiniMax system voice ids change over time; if the default `male-qn-qingse` is rejected, ask the user to pick one from the MiniMax/fal voice list, or clone.

## Script tips (better mouth shapes)

- Speech rate ~4 Chinese characters or ~2.5 English words per second. Slightly slow (`--speed 0.9` / `--rate=-5%`) gives cleaner lips.
- Write numbers, dates, English names the way they should be read (e.g. "2026年" → "二零二六年" if it is read that way); fix 多音字 by rewording.
- Short sentences, clear pauses at punctuation — pauses are where long audio gets split.
- No background music in the voice track; add music after lip sync.
- Always let the user listen to the voice before spending video money.

## Clone consent

Only clone a voice whose owner agreed. Ask once, clearly. Never clone public figures.
