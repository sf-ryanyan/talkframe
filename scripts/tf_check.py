#!/usr/bin/env python3
"""TalkFrame environment check (setup wizard backend).

Detects tools, API keys (presence only, never values), GPU, and local model folders,
then recommends routes. Use --save to write ~/.talkframe/config.json (no secrets inside).
Prints one JSON object.
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys

# Windows consoles default to a legacy code page; force UTF-8 so Chinese text never crashes the output.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa
        pass

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".talkframe")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def sh(cmd, timeout=15):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=isinstance(cmd, str))
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa
        return 1, str(e)


def first_line(s):
    return (s or "").strip().splitlines()[0] if (s or "").strip() else ""


def gpu_info():
    if not shutil.which("nvidia-smi"):
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            return {"vendor": "apple", "name": "Apple Silicon", "vram_gb": None,
                    "note": "Apple GPU: most local lip-sync repos are CUDA-first; MuseTalk has an MLX port."}
        return None
    code, outp = sh(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"])
    if code != 0 or not outp.strip():
        return None
    name, mem, drv = [x.strip() for x in outp.strip().splitlines()[0].split(",")[:3]]
    return {"vendor": "nvidia", "name": name, "vram_gb": round(int(float(mem)) / 1024, 1), "driver": drv}


def listenhub_state():
    if not shutil.which("listenhub"):
        return {"cli": False, "api_key": False}
    code, ver = sh(["listenhub", "--version"])
    cfg = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config"),
                       "listenhub", "openapi.json")
    has_key = bool(os.environ.get("LISTENHUB_API_KEY"))
    if not has_key and os.path.exists(cfg):
        try:
            with open(cfg, encoding="utf-8") as f:
                has_key = bool(json.load(f).get("apiKey"))
        except Exception:  # noqa
            pass
    return {"cli": True, "version": first_line(ver), "api_key": has_key}


def py_has(mod):
    try:
        __import__(mod)
        return True
    except Exception:  # noqa
        return False


def local_dirs():
    found = {}
    for name, env in [("musetalk", "TALKFRAME_MUSETALK_DIR"), ("latentsync", "TALKFRAME_LATENTSYNC_DIR"),
                      ("sadtalker", "TALKFRAME_SADTALKER_DIR"), ("infinitetalk", "TALKFRAME_INFINITETALK_DIR")]:
        d = os.environ.get(env)
        found[name] = {"env": env, "path": d, "exists": bool(d and os.path.isdir(d))}
    return found


def recommend(st):
    routes = []
    if st["keys"]["fal"]:
        routes += [
            {"id": "fal-kling", "mode": "natural", "desc": "fal Kling Avatar v2 (std draft / pro final)"},
            {"id": "fal-omnihuman", "mode": "natural", "desc": "fal OmniHuman 1.5 (strong lip sync, more motion)"},
            {"id": "fal-infinitalk", "mode": "natural", "desc": "fal InfiniteTalk (cheapest, <=28s per segment)"},
            {"id": "fal-sync", "mode": "conservative", "desc": "still base video (free) + fal Sync lipsync-2 (mouth only)"},
        ]
    if st["listenhub"].get("api_key"):
        routes += [{"id": "listenhub-pixverse", "mode": "natural/conservative",
                    "desc": "ListenHub PixVerse base video + lip_sync (uses ListenHub credits)"}]
    g = st["gpu"]
    vram = (g or {}).get("vram_gb") or 0
    if g and g.get("vendor") == "nvidia":
        if vram >= 6:
            routes.append({"id": "local-musetalk", "mode": "conservative",
                           "desc": "local MuseTalk 1.5 (mouth only, ~6-8 GB VRAM)"})
        if vram >= 8:
            routes.append({"id": "local-latentsync15", "mode": "conservative",
                           "desc": "local LatentSync 1.5 (mouth only, 8 GB, better on Chinese)"})
        if vram >= 4:
            routes.append({"id": "local-sadtalker", "mode": "natural-lite",
                           "desc": "local SadTalker --still (one photo, 4-6 GB, older look)"})
        if vram >= 18:
            routes.append({"id": "local-latentsync16", "mode": "conservative",
                           "desc": "local LatentSync 1.6 (512px, sharper teeth/lips, 18 GB)"})
        if vram >= 12:
            routes.append({"id": "local-infinitetalk", "mode": "natural",
                           "desc": "local InfiniteTalk 480p via low-VRAM mode / Wan2GP (slow, 32 GB RAM advised)"})
    voices = []
    if st["keys"]["fal"]:
        voices.append({"id": "fal-minimax", "desc": "MiniMax speech-02-hd on fal (strong Chinese; clone available)"})
    if st["listenhub"].get("api_key"):
        voices.append({"id": "listenhub", "desc": "ListenHub TTS / voice clone"})
    if st["python_pkgs"]["edge_tts"]:
        voices.append({"id": "edge-tts", "desc": "Edge TTS (free, no key, needs internet; no cloning)"})
    voices.append({"id": "user-audio", "desc": "user's own recording"})
    return routes, voices


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true", help="write ~/.talkframe/config.json")
    ap.add_argument("--priority", choices=["quality", "speed", "cost"], help="store the user's priority")
    a = ap.parse_args()

    st = {
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": sys.version.split()[0],
        "tools": {t: bool(shutil.which(t)) for t in ["ffmpeg", "ffprobe", "node", "npm", "git"]},
        "keys": {"fal": bool(os.environ.get("FAL_KEY")),
                 "elevenlabs": bool(os.environ.get("ELEVENLABS_API_KEY"))},
        "listenhub": listenhub_state(),
        "python_pkgs": {"fal_client": py_has("fal_client"), "edge_tts": py_has("edge_tts"),
                        "pillow": py_has("PIL"), "pillow_heif": py_has("pillow_heif")},
        "gpu": gpu_info(),
        "local_models": local_dirs(),
    }
    routes, voices = recommend(st)
    st["video_routes"] = routes
    st["voice_routes"] = voices
    missing = []
    if not st["tools"]["ffmpeg"]:
        missing.append("ffmpeg (Windows: winget install Gyan.FFmpeg / Mac: brew install ffmpeg)")
    if st["keys"]["fal"] and not st["python_pkgs"]["fal_client"]:
        missing.append("pip install fal-client")
    if not st["python_pkgs"]["pillow_heif"]:
        missing.append("optional: pip install pillow pillow-heif (iPhone HEIC photos + safer photo rotation)")
    if not routes:
        missing.append("no video route yet: set FAL_KEY, or configure ListenHub, or install a local model")
    st["missing"] = missing

    if a.save:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        cfg = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:  # noqa
                cfg = {}
        cfg.update({"routes": [r["id"] for r in routes], "voices": [v["id"] for v in voices],
                    "gpu": st["gpu"]})
        if a.priority:
            cfg["priority"] = a.priority
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        st["saved_config"] = CONFIG_PATH
    elif os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                st["existing_config"] = json.load(f)
        except Exception:  # noqa
            pass
    print(json.dumps(st, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
