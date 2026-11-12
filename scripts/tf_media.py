#!/usr/bin/env python3
"""TalkFrame media helper (ffmpeg-based, no extra Python packages).

Subcommands
  photo     prepare a portrait: crop or pad to a ratio, min size, JPEG <= 10 MB
  audio     normalize audio, pad short audio, split long audio at pauses
  still     make a "base video" from a photo (static or very subtle breathing zoom)
  qc        build contact sheets (photo + frames, pause frames) and timing report
  assemble  join clips, optional clean-audio swap, trim, AI label

Every subcommand prints one JSON object on stdout. Errors -> {"ok": false, "error": "..."} and exit 1.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys

# Windows consoles default to a legacy code page; force UTF-8 so Chinese text never crashes the output.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa
        pass

RATIOS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080),
          "3:4": (1080, 1440), "4:3": (1440, 1080)}


def die(msg):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def need(tool):
    if not shutil.which(tool):
        die(f"{tool} not found. Install ffmpeg (Windows: winget install Gyan.FFmpeg / Mac: brew install ffmpeg).")


def run(cmd, check=True):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        die("command failed: " + " ".join(cmd) + "\n" + p.stderr[-1500:])
    return p


def probe(path):
    p = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    return json.loads(p.stdout)


def duration(path):
    info = probe(path)
    d = info.get("format", {}).get("duration")
    if d is None:
        for s in info.get("streams", []):
            if s.get("duration"):
                d = s["duration"]
                break
    return float(d) if d else 0.0


def video_size(path):
    for s in probe(path).get("streams", []):
        if s.get("codec_type") == "video":
            return int(s["width"]), int(s["height"])
    die(f"no image/video stream in {path}")


def has_audio(path):
    return any(s.get("codec_type") == "audio" for s in probe(path).get("streams", []))


def silences(path, noise="-35dB", min_d=0.3):
    p = run(["ffmpeg", "-hide_banner", "-i", path, "-af", f"silencedetect=noise={noise}:d={min_d}",
             "-f", "null", "-"], check=False)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", p.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    out = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else duration(path)
        out.append((s, e))
    return out


# ---------------------------------------------------------------- photo
def normalize_photo(src, tmpdir):
    """Return a JPEG/PNG path with EXIF rotation applied and HEIC converted. Uses Pillow when available."""
    ext = os.path.splitext(src)[1].lower()
    os.makedirs(tmpdir, exist_ok=True)
    dst = os.path.join(tmpdir, "_upright.png")
    try:
        from PIL import Image, ImageOps
        if ext in (".heic", ".heif"):
            try:
                import pillow_heif
                pillow_heif.register_heif_opener()
            except ImportError:
                pass
        im = Image.open(src)
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.save(dst)
        return dst, "pillow"
    except Exception:  # noqa  Pillow missing or cannot read -> other routes
        pass
    if ext in (".heic", ".heif"):
        if shutil.which("sips"):  # macOS built-in converter
            jpg = os.path.join(tmpdir, "_upright.jpg")
            run(["sips", "-s", "format", "jpeg", src, "--out", jpg])
            return jpg, "sips"
        die("HEIC photo: run `pip install pillow pillow-heif` once, or export the photo as JPG.")
    return src, "ffmpeg"  # ffmpeg applies EXIF rotation itself when decoding


def decoded_size(path):
    """Size of the image as ffmpeg actually decodes it (after auto-rotation)."""
    w, h = video_size(path)
    # ffprobe reports stored size; ffmpeg rotates JPEGs with EXIF 5-8 when decoding
    tmp = path + ".probe.png"
    run(["ffmpeg", "-y", "-hide_banner", "-i", path, "-frames:v", "1", "-vf", "scale=iw/8:ih/8", tmp], check=False)
    if os.path.exists(tmp):
        tw, th = video_size(tmp)
        os.remove(tmp)
        if (tw > th) != (w > h):
            w, h = h, w
    return w, h


def cmd_photo(a):
    need("ffmpeg")
    if not os.path.exists(a.input):
        die(f"photo not found: {a.input}")
    W, H = RATIOS[a.ratio]
    tmpdir = os.path.join(os.path.dirname(os.path.abspath(a.out)), "_photo_tmp")
    src, how = normalize_photo(a.input, tmpdir)
    w0, h0 = decoded_size(src)
    if a.mode == "crop":
        # scale to cover (aspect kept), crop with a slight upward bias to keep head and chin
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*{a.bias}")
    else:
        # fit inside, fill the rest with a blurred copy of the photo
        vf = (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:5[bg];"
              f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    q = 2
    run(["ffmpeg", "-y", "-hide_banner", "-i", src, "-vf", vf, "-frames:v", "1", "-q:v", str(q), a.out])
    size = os.path.getsize(a.out)
    while size > 10 * 1024 * 1024 and q < 10:
        q += 2
        run(["ffmpeg", "-y", "-hide_banner", "-i", src, "-vf", vf, "-frames:v", "1", "-q:v", str(q), a.out])
        size = os.path.getsize(a.out)
    shutil.rmtree(tmpdir, ignore_errors=True)
    ow, oh = video_size(a.out)
    warn = []
    if min(w0, h0) < 720:
        warn.append("low_resolution_source")
    if a.mode == "crop" and (w0 / h0 > 1.2 and W / H < 1):
        warn.append("landscape_photo_cropped_to_portrait_check_head_is_inside")
    print(json.dumps({"ok": True, "out": a.out, "source_size": [w0, h0], "out_size": [ow, oh],
                      "bytes": size, "mode": a.mode, "decoder": how, "warnings": warn}, ensure_ascii=False))


# ---------------------------------------------------------------- audio
def cmd_audio(a):
    need("ffmpeg")
    if not os.path.exists(a.input):
        die(f"audio not found: {a.input}")
    os.makedirs(a.outdir, exist_ok=True)
    voice = os.path.join(a.outdir, "voice.mp3")
    af = "loudnorm=I=-16:TP=-1.5:LRA=11" if not a.no_normalize else "anull"
    run(["ffmpeg", "-y", "-hide_banner", "-i", a.input, "-vn", "-ac", "1", "-ar", "44100", "-af", af,
         "-c:a", "libmp3lame", "-b:a", "192k", voice])
    total = duration(voice)
    if total < 0.3:
        die("audio is empty or too short")
    speech_end = total
    sil = silences(voice, a.noise, 0.3)
    if sil and sil[-1][1] >= total - 0.05:
        speech_end = sil[-1][0]

    segs = []
    if total <= a.max_seg:
        segs.append((0.0, total))
    else:
        # greedy: cut at the middle of a pause, as late as possible but <= max_seg
        cuts = [(s + e) / 2 for s, e in sil if e - s >= 0.25]
        start = 0.0
        while total - start > a.max_seg:
            limit = start + a.max_seg
            cands = [c for c in cuts if start + a.min_seg <= c <= limit]
            cut = max(cands) if cands else limit  # no pause found -> hard cut
            segs.append((start, cut))
            start = cut
        segs.append((start, total))

    out = []
    for i, (s, e) in enumerate(segs, 1):
        path = os.path.join(a.outdir, f"seg{i:02d}.mp3")
        run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", voice,
             "-c:a", "libmp3lame", "-b:a", "192k", path])
        d = duration(path)
        padded = False
        if d < a.min_len:
            tmp = path + ".pad.mp3"
            run(["ffmpeg", "-y", "-hide_banner", "-i", path, "-af", f"apad=whole_dur={a.min_len}",
                 "-c:a", "libmp3lame", "-b:a", "192k", tmp])
            os.replace(tmp, path)
            d, padded = duration(path), True
        out.append({"file": path, "start": round(s, 3), "end": round(e, 3),
                    "seconds": round(d, 3), "padded_to_min": padded})
    print(json.dumps({"ok": True, "voice": voice, "total_seconds": round(total, 3),
                      "speech_end": round(speech_end, 3), "segments": out}, ensure_ascii=False))


# ---------------------------------------------------------------- still base video
def cmd_still(a):
    need("ffmpeg")
    w, h = video_size(a.photo)
    w, h = w - w % 2, h - h % 2
    fps = 25
    frames = max(1, int(math.ceil(a.seconds * fps)))
    if a.motion == "breathe":
        # very slow 1.5% zoom in and out, period ~6 s: feels alive, keeps the face stable
        z = "1.0+0.0075*(1-cos(2*PI*on/150))"
        vf = (f"scale={w*2}:{h*2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={w}x{h}:fps={fps},format=yuv420p")
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loop", "1", "-i", a.photo, "-vf", vf,
               "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", a.out]
    else:
        vf = f"scale={w}:{h},format=yuv420p"
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loop", "1", "-framerate", str(fps), "-i", a.photo,
               "-vf", vf, "-t", f"{a.seconds:.3f}", "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "16", "-tune", "stillimage", a.out]
    run(cmd)
    print(json.dumps({"ok": True, "out": a.out, "seconds": round(duration(a.out), 3),
                      "size": [w, h], "motion": a.motion}, ensure_ascii=False))


# ---------------------------------------------------------------- qc
def cmd_qc(a):
    need("ffmpeg")
    os.makedirs(a.outdir, exist_ok=True)
    vdur = duration(a.video)
    adur = duration(a.audio) if a.audio else None
    W, H = video_size(a.video)
    tmp = os.path.join(a.outdir, "_qc_tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)

    def grab(t, idx):
        p = os.path.join(tmp, f"f_{idx:03d}.jpg")
        run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{max(0, t):.3f}", "-i", a.video, "-frames:v", "1",
             "-vf", f"scale={W}:{H}", "-q:v", "3", p])
        return p

    # frame 000 = the original photo, same size as the video
    photo0 = os.path.join(tmp, "f_000.jpg")
    if a.photo:
        run(["ffmpeg", "-y", "-hide_banner", "-i", a.photo, "-vf",
             f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
             "-frames:v", "1", "-q:v", "3", photo0])
    else:
        grab(0, 0)
    n = a.frames
    times = [vdur * (i + 0.5) / n for i in range(n)]
    for i, t in enumerate(times, 1):
        grab(t, i)
    cols = min(4, n + 1)
    rows = math.ceil((n + 1) / cols)
    sheet = os.path.join(a.outdir, "qc_sheet.jpg")
    run(["ffmpeg", "-y", "-hide_banner", "-framerate", "1", "-i", os.path.join(tmp, "f_%03d.jpg"),
         "-vf", f"scale=-2:{a.thumb},tile={cols}x{rows}:padding=4:color=white", "-frames:v", "1", sheet])

    pause_sheet, pauses = None, []
    if a.audio:
        for s, e in silences(a.audio, "-35dB", 0.4):
            if e - s >= 0.4 and (s + e) / 2 < vdur - 0.2 and s > 0.2:
                pauses.append(round((s + e) / 2, 3))
        pauses = pauses[:4]
        if pauses:
            ptmp = os.path.join(tmp, "p")
            os.makedirs(ptmp)
            for i, t in enumerate(pauses):
                run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{t:.3f}", "-i", a.video, "-frames:v", "1",
                     "-vf", f"scale={W}:{H}", "-q:v", "3", os.path.join(ptmp, f"p_{i:03d}.jpg")])
            pause_sheet = os.path.join(a.outdir, "qc_pauses.jpg")
            run(["ffmpeg", "-y", "-hide_banner", "-framerate", "1", "-i", os.path.join(ptmp, "p_%03d.jpg"),
                 "-vf", f"scale=-2:{a.thumb},tile={len(pauses)}x1:padding=4:color=white",
                 "-frames:v", "1", pause_sheet])
    shutil.rmtree(tmp, ignore_errors=True)
    diff = round(vdur - adur, 3) if adur is not None else None
    print(json.dumps({
        "ok": True, "video_seconds": round(vdur, 3), "audio_seconds": round(adur, 3) if adur else None,
        "length_diff": diff, "length_ok": (abs(diff) < 0.3) if diff is not None else None,
        "video_has_audio": has_audio(a.video), "size": [W, H],
        "sheet": sheet, "sheet_order": "first tile = original photo, then frames in time order",
        "sample_times": [round(t, 2) for t in times],
        "pause_sheet": pause_sheet, "pause_times": pauses}, ensure_ascii=False))


# ---------------------------------------------------------------- assemble
def cmd_assemble(a):
    need("ffmpeg")
    clips = a.clips
    for c in clips:
        if not os.path.exists(c):
            die(f"clip not found: {c}")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    work = a.out + ".tmp.mp4"
    W, H = video_size(clips[0])
    norm = []
    for i, c in enumerate(clips):
        # normalize every clip (size, fps, audio) so concat never glitches
        n = f"{a.out}.part{i:02d}.mp4"
        cmd = ["ffmpeg", "-y", "-hide_banner", "-i", c]
        if not has_audio(c):
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-shortest"]
        cmd += ["-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps=25,format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-ar", "44100", "-ac", "1", "-b:a", "192k", n]
        run(cmd)
        norm.append(n)
    lst = a.out + ".list.txt"
    with open(lst, "w", encoding="utf-8") as f:
        for n in norm:
            f.write("file '" + os.path.abspath(n).replace("\\", "/").replace("'", "'\\''") + "'\n")
    run(["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", work])

    notes = []
    if a.clean_audio:
        vd, ad = duration(work), duration(a.clean_audio)
        if abs(vd - ad) <= a.swap_tolerance:
            tmp2 = a.out + ".swap.mp4"
            run(["ffmpeg", "-y", "-hide_banner", "-i", work, "-i", a.clean_audio, "-map", "0:v", "-map", "1:a",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", tmp2])
            os.replace(tmp2, work)
            notes.append("clean_audio_swapped")
        else:
            notes.append(f"clean_audio_skipped_length_mismatch({vd:.2f}s vs {ad:.2f}s)")

    vf = []
    if a.label:
        txt = a.label.replace(":", "\\:").replace("'", "")
        vf.append(f"drawtext=text='{txt}':fontcolor=white@0.85:fontsize=h/40:box=1:boxcolor=black@0.35:"
                  f"boxborderw=8:x=w-tw-24:y=24" + (":fontfile='" + a.font.replace("\\", "/").replace(":", "\\:") + "'" if a.font else ""))
    cmd = ["ffmpeg", "-y", "-hide_banner", "-i", work]
    if a.trim:
        cmd += ["-t", f"{a.trim:.3f}"]
    if vf:
        cmd += ["-vf", ",".join(vf), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18"]
    else:
        cmd += ["-c:v", "copy"]
    cmd += ["-c:a", "copy", "-metadata", "comment=AI-generated video (TalkFrame)", "-movflags", "+faststart", a.out]
    p = run(cmd, check=False)
    if p.returncode != 0 and vf:
        notes.append("label_failed_no_font: visible label skipped, metadata label kept")
        cmd = ["ffmpeg", "-y", "-hide_banner", "-i", work] + (["-t", f"{a.trim:.3f}"] if a.trim else []) + \
              ["-c", "copy", "-metadata", "comment=AI-generated video (TalkFrame)", "-movflags", "+faststart", a.out]
        run(cmd)
    elif p.returncode != 0:
        die(p.stderr[-1500:])
    elif a.label:
        notes.append("visible_label_added")
    for f in norm + [lst, work]:
        try:
            os.remove(f)
        except OSError:
            pass
    print(json.dumps({"ok": True, "out": a.out, "seconds": round(duration(a.out), 3),
                      "clips": len(clips), "notes": notes}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description="TalkFrame media helper")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("photo")
    p.add_argument("--in", dest="input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--ratio", choices=list(RATIOS), default="9:16")
    p.add_argument("--mode", choices=["crop", "pad"], default="crop")
    p.add_argument("--bias", type=float, default=0.3, help="vertical crop position 0=top 0.5=center")
    p.set_defaults(fn=cmd_photo)

    p = sp.add_parser("audio")
    p.add_argument("--in", dest="input", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--max-seg", type=float, default=55.0, help="max seconds per segment (provider limit)")
    p.add_argument("--min-seg", type=float, default=3.0)
    p.add_argument("--min-len", type=float, default=0.0, help="pad segments shorter than this (e.g. 5 for PixVerse)")
    p.add_argument("--noise", default="-35dB")
    p.add_argument("--no-normalize", action="store_true")
    p.set_defaults(fn=cmd_audio)

    p = sp.add_parser("still")
    p.add_argument("--photo", required=True)
    p.add_argument("--seconds", type=float, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--motion", choices=["none", "breathe"], default="breathe")
    p.set_defaults(fn=cmd_still)

    p = sp.add_parser("qc")
    p.add_argument("--video", required=True)
    p.add_argument("--photo")
    p.add_argument("--audio")
    p.add_argument("--outdir", required=True)
    p.add_argument("--frames", type=int, default=7)
    p.add_argument("--thumb", type=int, default=360)
    p.set_defaults(fn=cmd_qc)

    p = sp.add_parser("assemble")
    p.add_argument("--clips", nargs="+", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--clean-audio")
    p.add_argument("--swap-tolerance", type=float, default=0.25)
    p.add_argument("--trim", type=float)
    p.add_argument("--label", default="AI Generated", help="visible corner label; empty string to disable")
    p.add_argument("--font", help="font file for the label (needed for Chinese text)")
    p.set_defaults(fn=cmd_assemble)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
