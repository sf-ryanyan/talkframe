# Provider: ListenHub (cloud, credits; PixVerse lip sync + ListenHub voices)

Needs: `npm install -g @marswave/listenhub-cli@latest`, API key set with `listenhub openapi config set-key` (PixVerse is API-key only), Node 18+, ffmpeg.
`--help` is the source of truth: run `listenhub openapi video pixverse generate --help` once per session.

## Route

```
photo → upload → PixVerse image_to_video "base video" (calm, mouth closed) → PixVerse lip_sync with the audio → clip
```

lip_sync only repaints the mouth of the base video, so the face stays like the photo. Natural vs conservative = the base-video prompt.

## Upload local files (PixVerse needs URLs)

```bash
node <skill>/scripts/lh_upload.mjs {work}/photo.jpg      # → {"fileUrl":"https://..."}
node <skill>/scripts/lh_upload.mjs {work}/seg01.mp3
```

The script reuses the CLI's SDK and saved key, and follows the domain the CLI uses (mainland China users included). Limits: image 10 MB, audio 20 MB, video 50 MB.

## Voice

```bash
listenhub openapi speakers list --language zh --json
listenhub openapi speech --script '...' --speaker-id '<speakerId>' --speed 1 --json     # returns an audio URL
listenhub openapi voice-clone create --file ./sample.m4a --lang zh --consent --auto-confirm --name '<name>' --gender male --json
```

Clone costs ~300 credits once the free quota is used; ask before `--use-credits`. `--consent` is a legal statement — only after the user confirms.

## Base video

Natural prompt:
```
The reference image is the opening frame; preserve the face identity, face shape, eyes, nose, mouth shape, skin texture, hairstyle, outfit and background exactly. The person faces the camera with a calm, friendly, neutral expression, lips gently closed, as if about to speak. Subtle natural life only: soft breathing, natural blinking, a very slight head movement. Static tripod camera, framing never changes. No talking, no smiling, no laughing, no hand gestures, no body turning, no new objects, no text. Soft even light that stays constant. Silence.
```
Conservative prompt:
```
The reference image is the opening frame; preserve the face identity, face shape, eyes, nose, mouth shape, skin texture, hairstyle, outfit and background exactly. The person stays still and faces the camera with a neutral relaxed expression and closed lips. Only natural blinking and very faint breathing. The head does not move. No expression change, no talking, no smiling, no gestures, no camera movement, no zoom, no text. Constant lighting. Silence.
```

```bash
listenhub openapi video pixverse estimate --capability image_to_video --quality 720p --duration <D> --json
listenhub openapi video pixverse generate --capability image_to_video --model pixverse \
  --image '<photoUrl>' --prompt '<prompt>' --quality 720p --aspect-ratio 9:16 --duration <D> --no-wait --json
listenhub openapi video get <taskId> --json          # poll every ~15 s: pending → generating → uploading → success | failed
```

`D` = ceil(longest segment), integer 1–60. If the API rejects the duration, try 5 / 8 / 10 and split the audio into segments ≤ the accepted length (`tf_media.py audio --max-seg <D>`).

Check the base video with `tf_media.py qc --video base.mp4 --photo photo.jpg` before lip sync. Never lip-sync a bad base.

## Lip sync

```bash
listenhub openapi video pixverse estimate --capability lip_sync --quality 720p --duration <segSeconds> --json
listenhub openapi video pixverse generate --capability lip_sync --model pixverse \
  --source-task-id '<baseTaskId>' --audio '<audioUrl>:<segSeconds>' --quality 720p --no-wait --json
```

- Audio 5–60 s per segment: prepare with `tf_media.py audio --min-len 5 --max-seg 55`.
- If `--source-task-id` is rejected, retry once with `--video '<baseVideoUrl>:<D>'`. Then stop and report.
- Do not use `--lip-sync-tts / --lip-sync-speaker-id / --lip-sync-content` (rejected by the validator). For TTS-driven lip sync use `--pixverse-json '{"tts":{"speakerId":"...","content":"..."}}'` without `--audio`.
- Rate limit: 5 requests/minute.
- Never auto-retry a paid task.

## First-run calibration (log the results)

1. Uploaded `fileUrl` accepted as `--image` / `--audio`.
2. `--source-task-id` works (else `--video URL`).
3. Allowed base durations; behavior when audio is longer than the base.
