#!/usr/bin/env python3
"""TalkFrame fal.ai runner. Needs: pip install fal-client ; env FAL_KEY.

Subcommands
  models                      list model aliases and their limits
  upload FILE                 upload a local file to fal storage -> URL
  avatar  --model ALIAS ...   photo + audio -> talking video (one-step)
  lipsync --video V --audio A mouth-only lip sync on an existing video (conservative mode)
  tts     --text ...          MiniMax speech-02-hd (good Chinese) -> mp3
  clone   --audio FILE        MiniMax voice clone -> custom_voice_id (costs money, needs consent)

Local paths are uploaded automatically. --dry-run prints the request without calling fal.
Every subcommand prints one JSON object on stdout.
"""
import argparse
import json
import math
import os
import sys
import urllib.request

# Windows consoles default to a legacy code page; force UTF-8 so Chinese text never crashes the output.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa
        pass

MODELS = {
    # alias: endpoint, kind, notes. Limits verified from fal model pages; re-check `--help` pages if a call fails.
    "kling-std": {"endpoint": "fal-ai/kling-video/ai-avatar/v2/standard", "kind": "avatar",
                  "note": "Kling AI Avatar v2 Standard. Good lip sync, low price. Default draft/final for most jobs."},
    "kling-pro": {"endpoint": "fal-ai/kling-video/ai-avatar/v2/pro", "kind": "avatar",
                  "note": "Kling AI Avatar v2 Pro. Sharper face detail, about 2x price of std."},
    "omnihuman": {"endpoint": "fal-ai/bytedance/omnihuman/v1.5", "kind": "avatar",
                  "note": "OmniHuman 1.5. Very strong lip sync, more motion. Audio max 60s at 720p, 30s at 1080p.",
                  "max_audio": {"720p": 60, "1080p": 30}},
    "infinitalk": {"endpoint": "fal-ai/infinitalk", "kind": "avatar",
                   "note": "InfiniteTalk. Cheapest, 480p/720p, prompt required, num_frames 41-721 (25 fps, ~28.8s max)."},
    "sync": {"endpoint": "fal-ai/sync-lipsync/v2", "kind": "lipsync",
             "note": "Sync lipsync-2 (mouth only, keeps the face). model lipsync-2 or lipsync-2-pro."},
    "tts": {"endpoint": "fal-ai/minimax/speech-02-hd", "kind": "tts",
            "note": "MiniMax speech-02-hd. Text max 5000 chars."},
    "clone": {"endpoint": "fal-ai/minimax/voice-clone", "kind": "clone",
              "note": "MiniMax voice clone. Sample >= 10s. Use the voice in TTS within 7 days or it is deleted."},
}

CALM_PROMPT = ("A person speaking directly to the camera with a calm, natural, friendly expression. "
               "Accurate lip sync. Minimal head movement, no hand gestures, no big smile. "
               "Static camera, stable framing, constant soft light. Keep the face identical to the photo.")


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False))
    sys.exit(code)


def client():
    try:
        import fal_client  # noqa
    except ImportError:
        out({"ok": False, "error": "fal-client not installed. Run: pip install fal-client"}, 1)
    if not os.environ.get("FAL_KEY"):
        out({"ok": False, "error": "FAL_KEY is not set. Set it as an environment variable (never paste it in chat)."}, 1)
    import fal_client
    return fal_client


def as_url(fc, path_or_url, dry):
    if path_or_url is None:
        return None
    if path_or_url.startswith(("http://", "https://", "data:")):
        return path_or_url
    if not os.path.exists(path_or_url):
        out({"ok": False, "error": f"file not found: {path_or_url}"}, 1)
    if dry:
        return f"<upload:{os.path.basename(path_or_url)}>"
    return fc.upload_file(path_or_url)


def call(fc, endpoint, args, dry, timeout=1800):
    if dry:
        out({"ok": True, "dry_run": True, "endpoint": endpoint, "arguments": args})
    logs = []

    def on_update(u):
        if hasattr(u, "logs") and u.logs:
            for l in u.logs:
                logs.append(l.get("message", ""))
    try:
        try:
            return fc.subscribe(endpoint, arguments=args, with_logs=True, on_queue_update=on_update,
                                client_timeout=timeout)
        except TypeError as e:  # older fal-client without client_timeout
            if "client_timeout" not in str(e):
                raise
            return fc.subscribe(endpoint, arguments=args, with_logs=True, on_queue_update=on_update)
    except Exception as e:  # surface the API message (validation errors, safety rejections, balance)
        out({"ok": False, "endpoint": endpoint, "error": str(e)[:2000], "logs": logs[-5:]}, 1)


def download(url, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "TalkFrame/0.1"})
    with urllib.request.urlopen(req, timeout=600) as r, open(path, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    return path


def audio_seconds(path):
    import subprocess
    if path.startswith("http"):
        return None
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        return None


# ------------------------------------------------------------------ commands
def cmd_models(a):
    out({"ok": True, "models": {k: {"endpoint": v["endpoint"], "kind": v["kind"], "note": v["note"]}
                                for k, v in MODELS.items()}})


def cmd_upload(a):
    fc = client()
    out({"ok": True, "url": as_url(fc, a.file, False)})


def cmd_avatar(a):
    m = MODELS.get(a.model)
    if not m or m["kind"] != "avatar":
        out({"ok": False, "error": f"unknown avatar model {a.model}; choose: " +
             ", ".join(k for k, v in MODELS.items() if v["kind"] == "avatar")}, 1)
    secs = audio_seconds(a.audio)
    if a.model == "omnihuman" and secs:
        lim = m["max_audio"][a.resolution or "720p"]
        if secs > lim:
            out({"ok": False, "error": f"audio {secs:.1f}s > {lim}s limit for omnihuman {a.resolution or '720p'}; split the audio"}, 1)
    if a.model == "infinitalk" and secs and secs > 28.5:
        out({"ok": False, "error": f"audio {secs:.1f}s > ~28.5s (721 frames) for infinitalk; split the audio"}, 1)
    fc = None if a.dry_run else client()
    args = {"image_url": as_url(fc, a.image, a.dry_run), "audio_url": as_url(fc, a.audio, a.dry_run)}
    prompt = a.prompt or CALM_PROMPT
    if a.model in ("kling-std", "kling-pro", "omnihuman", "infinitalk"):
        args["prompt"] = prompt
    if a.model == "omnihuman":
        args["resolution"] = a.resolution or "720p"
        if a.turbo:
            args["turbo_mode"] = True
    if a.model == "infinitalk":
        args["resolution"] = a.resolution if a.resolution in ("480p", "720p") else "480p"
        frames = 145
        if secs:
            frames = int(math.ceil(secs * 25)) + 2
        frames = max(41, min(721, frames))
        frames = 4 * math.ceil((frames - 1) / 4) + 1  # Wan-based models need 4n+1 frames
        args["num_frames"] = min(frames, 721)
        args["acceleration"] = "regular"
    if a.extra:
        args.update(json.loads(a.extra))
    res = call(fc, m["endpoint"], args, a.dry_run)
    url = (res.get("video") or {}).get("url")
    if not url:
        out({"ok": False, "error": "no video in response", "response": res}, 1)
    download(url, a.out)
    out({"ok": True, "model": a.model, "endpoint": m["endpoint"], "out": a.out, "video_url": url,
         "duration": res.get("duration")})


def cmd_lipsync(a):
    fc = None if a.dry_run else client()
    args = {"video_url": as_url(fc, a.video, a.dry_run), "audio_url": as_url(fc, a.audio, a.dry_run),
            "model": a.sync_model, "sync_mode": a.sync_mode}
    res = call(fc, MODELS["sync"]["endpoint"], args, a.dry_run)
    url = (res.get("video") or {}).get("url")
    if not url:
        out({"ok": False, "error": "no video in response", "response": res}, 1)
    download(url, a.out)
    out({"ok": True, "model": a.sync_model, "out": a.out, "video_url": url})


def cmd_tts(a):
    text = a.text
    if a.text_file:
        with open(a.text_file, encoding="utf-8") as f:
            text = f.read().strip()
    if not text:
        out({"ok": False, "error": "empty text"}, 1)
    if len(text) > 5000:
        out({"ok": False, "error": f"text has {len(text)} chars; max 5000 per call. Split it."}, 1)
    vs = {"voice_id": a.voice_id, "speed": a.speed}
    if a.emotion:
        vs["emotion"] = a.emotion
    args = {"text": text, "voice_setting": vs, "language_boost": a.language, "output_format": "url"}
    fc = None if a.dry_run else client()
    res = call(fc, MODELS["tts"]["endpoint"], args, a.dry_run)
    url = (res.get("audio") or {}).get("url")
    if not url:
        out({"ok": False, "error": "no audio in response", "response": res}, 1)
    download(url, a.out)
    out({"ok": True, "out": a.out, "audio_url": url, "duration_ms": res.get("duration_ms"),
         "chars": len(text)})


def cmd_clone(a):
    if not a.consent:
        out({"ok": False, "error": "voice clone needs --consent (the voice owner agreed)."}, 1)
    fc = None if a.dry_run else client()
    args = {"audio_url": as_url(fc, a.audio, a.dry_run), "noise_reduction": True,
            "need_volume_normalization": True}
    if a.preview_text:
        args["text"] = a.preview_text
    res = call(fc, MODELS["clone"]["endpoint"], args, a.dry_run)
    vid = res.get("custom_voice_id")
    if not vid:
        out({"ok": False, "error": "no custom_voice_id in response", "response": res}, 1)
    preview = (res.get("audio") or {}).get("url")
    out({"ok": True, "custom_voice_id": vid, "preview_url": preview,
         "note": "Use this voice in tts at least once within 7 days or fal deletes it."})


def main():
    ap = argparse.ArgumentParser(description="TalkFrame fal.ai runner")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("models").set_defaults(fn=cmd_models)

    p = sp.add_parser("upload")
    p.add_argument("file")
    p.set_defaults(fn=cmd_upload)

    p = sp.add_parser("avatar")
    p.add_argument("--model", default="kling-std")
    p.add_argument("--image", required=True)
    p.add_argument("--audio", required=True)
    p.add_argument("--prompt")
    p.add_argument("--resolution", choices=["480p", "720p", "1080p"])
    p.add_argument("--turbo", action="store_true")
    p.add_argument("--extra", help="JSON merged into the request (advanced)")
    p.add_argument("--out", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_avatar)

    p = sp.add_parser("lipsync")
    p.add_argument("--video", required=True)
    p.add_argument("--audio", required=True)
    p.add_argument("--sync-model", choices=["lipsync-2", "lipsync-2-pro"], default="lipsync-2")
    p.add_argument("--sync-mode", choices=["cut_off", "loop", "bounce", "silence", "remap"], default="bounce")
    p.add_argument("--out", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_lipsync)

    p = sp.add_parser("tts")
    p.add_argument("--text")
    p.add_argument("--text-file")
    p.add_argument("--voice-id", default="male-qn-qingse",
                   help="MiniMax voice id (system voice or custom_voice_id from clone)")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--emotion", choices=["happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"])
    p.add_argument("--language", default="Chinese")
    p.add_argument("--out", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_tts)

    p = sp.add_parser("clone")
    p.add_argument("--audio", required=True)
    p.add_argument("--consent", action="store_true")
    p.add_argument("--preview-text")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_clone)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
