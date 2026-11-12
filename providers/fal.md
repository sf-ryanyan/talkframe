# Provider: fal.ai (cloud, one key for video + voice)

Needs: env `FAL_KEY`, `pip install fal-client`, ffmpeg. Local files are uploaded by the script automatically.
Runner: `python <skill>/scripts/tf_fal.py <subcommand> ...` (add `--dry-run` to see the request without paying).

## Models

| Alias | Endpoint | Mode | Input limits | Use when |
|---|---|---|---|---|
| `kling-std` | `fal-ai/kling-video/ai-avatar/v2/standard` | natural | image + audio (+prompt) | **Default.** Good lip sync, fair price. Draft and most finals. |
| `kling-pro` | `fal-ai/kling-video/ai-avatar/v2/pro` | natural | same | Final render when skin/hair detail matters (about 2× std). |
| `omnihuman` | `fal-ai/bytedance/omnihuman/v1.5` | natural | audio ≤ 60 s at 720p, ≤ 30 s at 1080p | Strongest lip sync; tends to move more — keep the calm prompt. |
| `infinitalk` | `fal-ai/infinitalk` | natural | 480p/720p, prompt required, ≤ ~28 s (721 frames @25 fps) | Cheapest; good for drafts and long scripts split into segments. |
| `sync` | `fal-ai/sync-lipsync/v2` | **conservative** | video + audio; `lipsync-2` / `lipsync-2-pro` | Mouth-only edit on a still base video → face cannot drift. |
| `tts` | `fal-ai/minimax/speech-02-hd` | voice | text ≤ 5000 chars | Chinese voiceover. |
| `clone` | `fal-ai/minimax/voice-clone` | voice | sample ≥ 10 s | Clone the user's voice (consent required). |

Prices change; tell the user to check fal.ai before big jobs. Typical order of cost per second: infinitalk < kling-std < sync ≈ kling-pro < omnihuman.

## Commands

```bash
# natural mode (one step)
python tf_fal.py avatar --model kling-std --image {work}/photo.jpg --audio {work}/seg01.mp3 --out {work}/clip_01.mp4
python tf_fal.py avatar --model omnihuman --resolution 720p --image ... --audio ... --out ...
python tf_fal.py avatar --model infinitalk --resolution 480p --image ... --audio ... --out ...

# conservative mode (two steps; the base video is made locally for free)
python tf_media.py still --photo {work}/photo.jpg --seconds <segment seconds> --out {work}/base_01.mp4 --motion breathe
python tf_fal.py lipsync --video {work}/base_01.mp4 --audio {work}/seg01.mp3 --out {work}/clip_01.mp4            # add --sync-model lipsync-2-pro for teeth/lip detail
```

The script sends the calm default prompt (no gestures, no big smile, static camera, keep the face identical). Override with `--prompt` only when the user wants a different feel; keep the "keep the face identical" sentence.

## Notes

- `--motion breathe` = a very slow 1.5% zoom so the still base does not look frozen. Use `--motion none` for a fully static frame.
- Sync lipsync on a still photo has no blinks. If the user wants blinks with zero face drift, use ListenHub PixVerse conservative base or a local SadTalker `--still` base, then mouth-only lip sync.
- Errors are returned as JSON with the API message (validation, safety filter, balance). Safety rejections of a real face: do not retry the same input; try another model or the conservative route.
- Voice clone on fal is deleted after 7 days unless used once in TTS.
