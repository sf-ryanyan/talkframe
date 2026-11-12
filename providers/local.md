# Provider: local GPU (free, private, slower)

Local models are installed by the user once (Claude guides, step by step, from each project's official README). TalkFrame then calls their command line and does photo/audio prep, QC and assembly itself.
Tell the user where each folder is expected: set env vars `TALKFRAME_MUSETALK_DIR`, `TALKFRAME_LATENTSYNC_DIR`, `TALKFRAME_SADTALKER_DIR`, `TALKFRAME_INFINITETALK_DIR` so `tf_check.py` can find them.

## Pick by VRAM (from `tf_check.py`)

| VRAM | Natural mode | Conservative mode (mouth only, face cannot drift) |
|---|---|---|
| 4–6 GB | SadTalker `--still` (older look, blinks + small head motion) | — |
| 6–8 GB | SadTalker `--still` | MuseTalk 1.5 on a still base video |
| 8–12 GB | SadTalker `--still` | **LatentSync 1.5** (official min 8 GB; improved on Chinese) or MuseTalk 1.5 |
| 12–16 GB | InfiniteTalk 480p in low-VRAM mode / Wan2GP (slow; 32 GB system RAM advised) | LatentSync 1.5 |
| 18 GB+ | InfiniteTalk 480p/720p | **LatentSync 1.6** (512 px, sharper teeth and lips; official min 18 GB) |

Apple Silicon: most repos are CUDA-first; MuseTalk has a community MLX port. Recommend the cloud routes on Mac unless the user wants to experiment.

**Older NVIDIA cards (GTX 10-series / Pascal):** check that the installed PyTorch still supports the card:
`python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.cuda.get_arch_list())"` — the list must contain the card's arch (GTX 10-series = `sm_61`). If not, install an older CUDA build of PyTorch that still ships it. Expect slow fp32 speed; keep clips short.

## Conservative mode (recommended local default)

```bash
python tf_media.py still --photo {work}/photo.jpg --seconds <segment seconds> --out {work}/base_01.mp4 --motion breathe
```

LatentSync (run inside its folder and env; check its `inference.sh` for the current flags):
```bash
python -m scripts.inference --unet_config_path configs/unet/stage2.yaml \
  --inference_ckpt_path checkpoints/latentsync_unet.pt --inference_steps 20 --guidance_scale 1.5 \
  --video_path {work}/base_01.mp4 --audio_path {work}/seg01.wav --video_out_path {work}/clip_01.mp4
# 1.6: use configs/unet/stage2_512.yaml and the 1.6 checkpoint
```

MuseTalk 1.5 (accepts a photo or a video; write a small inference yaml):
```yaml
task_0:
  video_path: "{work}/base_01.mp4"
  audio_path: "{work}/seg01.wav"
  bbox_shift: 0
```
```bash
python -m scripts.inference --inference_config {work}/musetalk.yaml --result_dir {work}/musetalk_out \
  --unet_model_path models/musetalkV15/unet.pth --unet_config models/musetalkV15/musetalk.json --version v15
```
`bbox_shift` moves the mouth crop (positive = more mouth open range). If the mouth looks too closed or too open, try -5…+5.

Convert audio to WAV for local models: `ffmpeg -y -i seg01.mp3 -ac 1 -ar 16000 seg01.wav`.

## Natural mode

SadTalker (one photo → talking head, minimal motion):
```bash
python inference.py --driven_audio {work}/seg01.wav --source_image {work}/photo.jpg --result_dir {work}/sad \
  --still --preprocess full --expression_scale 0.8 --enhancer gfpgan
```
`--still` + `--preprocess full` keeps the original pose and pastes the face back into the full photo. Lower `--expression_scale` = calmer. For better lips, run its output through LatentSync as a second pass (mouth only).

InfiniteTalk (heavy): follow the official README; for small GPUs use its `--num_persistent_param_in_dit 0` low-VRAM option or the Wan2GP app. Warn the user: minutes per few seconds of video.

## Voice locally

- `edge-tts` (pip): free, no key, good Chinese voices, needs internet, no cloning — see voice.md.
- Local cloning (CosyVoice, IndexTTS, GPT-SoVITS…): install from their README, export WAV, then treat it as the user's audio.

## Rules

- Never download multi-GB weights without telling the user the size and getting a yes.
- Run one 5–8 s test before a long job; report time per second of video so the user can plan.
- If the GPU runs out of memory: shorter segments, lower batch size / resolution, close other apps, or switch to a cloud route.
