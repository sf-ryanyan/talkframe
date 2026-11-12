---
name: talkframe
description: TalkFrame 数字人：一张人物照片 + 文案或音频 → 口型精准、五官不变形的说话视频。支持 fal.ai、ListenHub 云端或本地显卡，自动质检，效果差时切换保守模式。
---

# TalkFrame — photo + voice → talking digital human

Make a lip-synced talking-head video from **one portrait photo** and **a script or an audio file**. Works with cloud APIs (fal.ai, ListenHub) or a local GPU. Built for Chinese users: **all user-facing messages are in 简体中文**; prompts to models are English; file names are English.

Skill folder = `<skill>` below. Scripts: `<skill>/scripts/`. Provider details: `<skill>/providers/` — read **only** the file for the route you use (saves tokens).
Short names in commands: `tf_media.py` = `python <skill>/scripts/tf_media.py` (same for `tf_fal.py`, `tf_check.py`; use `python3` on Mac/Linux). Every script prints one JSON object; read it instead of guessing.

## What "good" means (in priority order)

1. **口型对** — mouth shapes match the words and timing; mouth closes in pauses.
2. **脸不变形** — face shape, eyes, nose, teeth, hairline stay like the photo.
3. **动作克制** — blinking, breathing, at most a slight head movement. No big smiles, gestures or body turns.
4. **不浪费** — check inputs first, show cost/time, get a yes, test short before long, never auto-retry a paid task.

## Two modes

| Mode | How | When |
|---|---|---|
| **自然模式 natural** (default) | one-step model: photo + audio → video | good front-facing photo |
| **保守模式 conservative** | still/near-still base video → **mouth-only** lip sync | risky photo, OR natural result failed QC. "不笑、不动，只张嘴说话" |

Auto fallback: a risky photo starts in conservative mode; a natural result that fails QC (face drift, warped mouth) → recommend a conservative retake (ask before spending again).

---

## Step 0 — First-run setup wizard (once; skip if `~/.talkframe/config.json` exists and the user does not ask to change it)

Run `python <skill>/scripts/tf_check.py` (use `python3` on Mac/Linux). It reports tools, which keys are **present** (never values), GPU/VRAM, local model folders, and possible routes.

Then ask, in **one** Chinese message (skip what the check already answered):

1. 你想用哪种方式？
   - **云端 API**（最快、效果最好，按秒付费）：fal.ai（一个 Key 包含视频+配音，推荐）/ ListenHub（用积分）
   - **本地显卡**（免费、隐私，速度慢，需要安装模型）— show what their VRAM can run (`providers/local.md` table)
2. 你最看重：**质量** / **速度** / **省钱**？
3. 声音来源：自己的录音 / 克隆自己的声音 / 用现成配音？

Key setup guidance (user does it in their own terminal — **never** ask them to paste a key into chat):
- fal.ai: create a key at fal.ai → set env var `FAL_KEY` (Windows: `setx FAL_KEY "..."` then reopen the terminal; Mac: add `export FAL_KEY=...` to `~/.zshrc`) → `pip install fal-client`.
- ListenHub: `npm install -g @marswave/listenhub-cli@latest` → `listenhub openapi config set-key`.
- ffmpeg is required for every route (Windows: `winget install Gyan.FFmpeg`; Mac: `brew install ffmpeg`).

Save: `python tf_check.py --save --priority <quality|speed|cost>`. Re-run the check whenever something fails with "not found / not set".

## Step 1 — Inputs (ask only what is missing, one message)

Photo(s) (1–5, close-up front face best) · script **or** audio · voice (if script) · ratio (default 9:16; 16:9 YouTube/web; 1:1 feed) · mode (default natural).

**Consent gate (ask once if unclear):** the person in the photo — and the owner of a cloned voice — agreed. Refuse public figures/celebrities, minors, and anything meant to deceive (fake endorsements, impersonation, fraud). The final video gets an "AI Generated" corner label by default; the user may turn it off, but remind them to disclose AI use where they publish.

Create the work folder `./talkframe-output/{YYYY-MM-DD}/{slug}/` → `{work}`.

## Step 2 — Choose and prepare the photo (free)

Look at each photo (Read the image). Pick the best:

- ✅ front-facing (turn < ~15°), eyes to camera, sharp, even light, lips relaxed/closed, one person, face ≥ ~1/4 of frame height.
- ⚠️ **risk → start conservative:** side angle, open-mouth smile/visible teeth, glasses glare, hair/hand/mic over the mouth, heavy beauty filter, < 720 px, harsh shadows.
- ❌ **ask for another photo:** mouth hidden, face tiny, several faces, chin cut off.

Tell the user in one line which photo and why. Never "AI-enhance" the face (changes identity). The script fixes phone-photo rotation and reads iPhone HEIC (needs `pip install pillow pillow-heif`; on Mac it falls back to `sips`). Prepare:

```bash
python tf_media.py photo --in <photo> --out {work}/photo.jpg --ratio 9:16          # --mode pad if cropping cuts the head; --bias 0.2 to move the crop up
```

## Step 3 — Prepare the voice

- **User audio:** `python tf_media.py audio --in <file> --outdir {work}/aud --max-seg <limit> [--min-len 5]`
  (normalizes loudness, splits long audio at pauses, pads short segments). If a segment had no pause to cut at, the script hard-cuts at the limit — tell the user and suggest adding a pause (punctuation) near that point.
- **Script:** pick the voice route from `providers/voice.md`; estimate length (~4 Chinese chars/s); generate to `{work}/tts.mp3`; **let the user listen before any video spend**; fix pronunciation by rewording. Then run `tf_media.py audio` on it.

Segment limit `--max-seg` by route: kling 55 · omnihuman 55 (720p) / 28 (1080p) · infinitalk 28 · sync 55 · ListenHub 55 with `--min-len 5` · local 30 (keeps memory low).

## Step 4 — Choose the route

Use the saved config + priority. Defaults:

| Priority | Natural | Conservative |
|---|---|---|
| 质量 quality | fal `kling-pro` (or `omnihuman` 720p for hardest lip sync) | still base + fal `sync` `lipsync-2-pro` |
| 平衡 (default) | fal `kling-std` | still base + fal `sync` `lipsync-2` |
| 省钱 cost | fal `infinitalk` 480p draft → `kling-std` final | still base + fal `sync` `lipsync-2` |
| ListenHub only | PixVerse base (natural prompt) + lip_sync | PixVerse base (conservative prompt) + lip_sync |
| Local GPU | SadTalker `--still` (or InfiniteTalk if ≥ 12–18 GB) | still base + LatentSync / MuseTalk |

Read the matching provider file now: `providers/fal.md`, `providers/listenhub.md` or `providers/local.md`.

## Step 5 — One confirmation card (always before spending money or long GPU time)

Reference prices on fal (Nov 2026 — prices change; say "以 fal 官网为准"): kling-std ≈ $0.056/s · kling-pro ≈ $0.115/s · omnihuman ≈ $0.16/s · sync lipsync-2 ≈ $0.05/s (pro ≈ 1.67×) · MiniMax TTS ≈ $0.1 / 1000 chars · voice clone ≈ $1.5. infinitalk: check fal. ListenHub: run its `estimate`. Local: estimate time after a 5–8 s test.

```
准备生成数字人：
  照片：{文件名}（{选择理由}）
  声音：{录音 / 配音：音色 / 克隆声音}，共 {x} 秒，分 {n} 段
  路线：{平台 · 模型}   模式：{自然 / 保守}（{原因}）
  比例：{9:16}  画质：{720p}
  预估：约 {$ / 积分 / 时间}
  建议：先试第 1 段（约 {s} 秒），满意再做全部
  确认开始？（任何参数都可以改）
```

**First job on a new route or new photo:** run segment 1 only, QC it, show the user, then do the rest.

**Long scripts:** every segment starts again from the photo pose, so a small cut is visible where segments join. The audio is split at pauses, so it reads like an edit cut; tell the user they can cover joins with B-roll or a zoom in their editor. Fewer, longer segments (within the model limit) = fewer joins.

## Step 6 — Generate

Follow the provider file. Name clips `{work}/clip_01.mp4`, `clip_02.mp4` … For conservative mode make each base with:

```bash
python tf_media.py still --photo {work}/photo.jpg --seconds <segment seconds> --out {work}/base_01.mp4 --motion breathe
```

Long jobs: run in the background, poll, give up after ~20 min per clip and tell the user how to check later. Respect provider rate limits.

## Step 7 — Quality check (every clip)

```bash
python tf_media.py qc --video {work}/clip_01.mp4 --photo {work}/photo.jpg --audio {work}/aud/seg01.mp3 --outdir {work}/qc_01
```

Read `qc_sheet.jpg` (first tile = original photo, then frames in time order) and `qc_pauses.jpg` (frames during pauses). Rate:

| Check | Pass |
|---|---|
| 长相 Identity | same face shape, eyes, nose, hairline as tile 1 |
| 嘴部 Mouth | no melting, blur blob, double lips, broken/extra teeth |
| 口型 Lip activity | mouth shapes vary with speech; **closed or nearly closed in pause frames** |
| 动作 Motion | no big smile, no gestures, head movement small, framing stable |
| 时长 Timing | `length_ok` true (video ≈ audio, < 0.3 s) |
| 画面 Artifacts | no text/watermark, no flicker, no light jumps |

Report each clip as **好 / 可修 / 废片** in one line. Cannot judge lip timing from stills alone → ask the user to watch clip 1 with sound before continuing.

**Fallback (one change at a time; ask before spending again):**

| Problem | Fix |
|---|---|
| Face drifts / warps (natural) | switch to **保守模式** (same audio) |
| Face drifts in conservative | different photo (more frontal, mouth closed, sharper) |
| Teeth/lips blurry | `lipsync-2-pro` / `kling-pro` / LatentSync 1.6; sharper photo with closed lips |
| Lips lag or mushy | slower voice (0.9×), clean audio (no music/noise), shorter segments (≤ 20 s) |
| Mouth moves in pauses | shorten long pauses; split at pauses; conservative mode |
| Too much motion / smiling | conservative mode, or calmer `--prompt` |
| Video shorter than audio | regenerate base longer; check segment length vs model limit |
| Rejected (safety/policy) | report it; do not retry the same input |

## Step 8 — Assemble and deliver

```bash
python tf_media.py assemble --clips {work}/clip_01.mp4 {work}/clip_02.mp4 --out {work}/final.mp4 \
  [--clean-audio {work}/aud/voice.mp3] [--trim <speech_end + 0.5>] [--label ""]
```

- `--clean-audio` swaps in the original clean voice only if lengths match (it checks).
- `--trim` when the last segment was padded to a minimum length.
- Label "AI Generated" is on by default (`--label ""` turns it off — remind about disclosure). Chinese label text needs `--font <path to a CJK font>`.

Report in Chinese: final path, route/model, mode, length, cost/credits or time, QC result, one tip. Append to `./talkframe-output/log.md`:

`| date | slug | route | model | mode | seconds | segments | cost | QC | note |`

Read the last 20 lines of the log at the start of a job to reuse what worked (photo type, model, speed, bbox_shift…). Record first-run calibration findings there too.

## Guardrails

- Consent for face and voice; no public figures, minors, impersonation or deceptive use.
- Keys only in env vars / CLI config; never in chat, files or logs.
- Never invent task IDs, URLs or results; show the real error.
- Confirm before every paid call, large download, or long GPU job; never auto-retry a paid task.
- Uploaded files go to the provider's storage — mention once if privacy matters.
