<div align="center">

# 🎙️ TalkFrame

**One photo + a script or voice → a talking digital human with accurate lip sync**
**一张照片 + 文案或录音 → 口型精准的数字人说话视频**

A Claude skill · 一个 Claude 技能

![version](https://img.shields.io/badge/version-v0.1%20preview-orange)
![license](https://img.shields.io/badge/license-MIT-blue)
![claude](https://img.shields.io/badge/Claude-Skill-8A63D2)
![language](https://img.shields.io/badge/output-中文%20%2F%20English-green)

[English](#-english) · [中文](#-中文)

🔗 **Repository:** https://github.com/sf-ryanyan/talkframe

</div>

---

## 🇺🇸 English

### 📌 Overview

TalkFrame lets Claude turn **one portrait photo** and **a script or an audio recording** into a **talking-head video**. The mouth follows the words, the face stays like the photo, and the motion stays calm and natural.

You choose how the video is made: a **cloud API** (fal.ai or ListenHub) or **your own GPU**. Claude handles everything else — checking your setup, preparing the photo and voice, choosing the model, checking quality and assembling the final video.

It is built with Chinese-speaking creators in mind (Chinese by default), and it works in English too.

### 😣 The problems it solves

| Pain point | How TalkFrame solves it |
|---|---|
| Talking-head tools often **warp the face** — a different jaw, odd teeth, moving eyes | Two modes. When a result drifts, it switches to a **conservative mode** that edits **only the mouth**, so the face cannot change |
| **Lips out of sync** with the words, or moving during pauses | Audio is cleaned and split at pauses; every clip is checked frame by frame, including frames taken **during pauses** |
| **Too much motion** — big smiles, waving hands, head swinging | Calm prompts by default: blinking, breathing, a slight head movement — nothing more |
| Every platform is different; **locked to one vendor** | One workflow for many providers: fal.ai (Kling Avatar, OmniHuman, InfiniteTalk, Sync), ListenHub, or local open-source models |
| **Wasted money** on failed renders | It checks inputs first, shows the cost, tests a short clip before the full job, and never retries a paid job without asking |
| **Setup is confusing** for non-engineers | A first-run setup wizard checks your computer and tells you exactly what is missing |
| Phone photos come out **rotated or stretched**; iPhone **HEIC** files fail | Phone-photo rotation is fixed automatically, and HEIC is supported |

### ✨ Features

- 🧙 **Setup wizard** — detects tools, keys (presence only), GPU and VRAM, then saves your preferred routes
- 🖼️ **Smart photo check** — picks the best photo, flags risky ones (side angle, open smile, glasses glare) and crops to 9:16, 16:9, 1:1 or 3:4
- 🗣️ **Voice options** — your own recording, a cloned voice, or a ready-made voice (MiniMax via fal, ListenHub, or the free Edge TTS)
- 🎬 **Two modes**
  - **Natural:** photo + audio → video in one step
  - **Conservative:** near-still base video → mouth-only lip sync ("no smile, no motion, just talking")
- 🔍 **Automatic quality check** — a contact sheet comparing the photo with video frames, frames taken during pauses, and a length check
- 🔁 **Smart fallback** — warped face → conservative mode; blurry lips → a sharper model; lips lagging → slower voice and shorter segments
- 🧩 **Long videos** — splits long audio at natural pauses, then joins the clips seamlessly
- 🏷️ **Responsible by default** — consent check, a visible "AI Generated" label (you can turn it off) and an AI tag in the file metadata
- 📒 **Learns over time** — keeps a log of what worked (photo type, model, speed) and reuses it

### ⚙️ How it works

```
Photo ─┐
       ├─► check & prepare ─► choose route ─► generate ─► quality check ─► final video
Voice ─┘                         │
                                 ├─ Natural:      Kling Avatar / OmniHuman / InfiniteTalk / SadTalker
                                 └─ Conservative: still base + Sync lipsync / PixVerse / LatentSync / MuseTalk
```

### 🧭 Choose your route

You need **at least one** way to make video. Voice can come from a different place.

| Route | What you need | Best for |
|---|---|---|
| ☁️ **fal.ai** (recommended) | A `FAL_KEY` (pay per second) | Best quality, simplest setup — one key covers video and voice |
| ☁️ **ListenHub** | ListenHub CLI + API key (uses credits) | People who already have ListenHub credits |
| 💻 **Local GPU** | NVIDIA GPU (about 6–8 GB+ VRAM) + models you install | Free and private, but slower |

Reference prices on fal.ai (Nov 2026; prices change — check fal.ai):
Kling Avatar v2 Standard ≈ $0.056/s · Pro ≈ $0.115/s · OmniHuman 1.5 ≈ $0.16/s · Sync lipsync-2 ≈ $0.05/s.
**A 30-second video usually costs about $1.5–$5.**

### 📦 Installation

**1. Requirements**
- [Claude Code](https://docs.claude.com) (recommended — the skill runs scripts on your computer)
- Python 3.9+
- ffmpeg — Windows: `winget install Gyan.FFmpeg` · Mac: `brew install ffmpeg`

**2. Install the skill**

Mac / Linux:
```bash
git clone https://github.com/sf-ryanyan/talkframe.git ~/.claude/skills/talkframe
```
Windows (PowerShell):
```powershell
git clone https://github.com/sf-ryanyan/talkframe.git "$env:USERPROFILE\.claude\skills\talkframe"
```
No git? Click **Code → Download ZIP**, unzip it, and put the folder at the path above, named `talkframe`.

**3. Python packages**
```bash
pip install fal-client pillow pillow-heif edge-tts
```

**4. Connect at least one route**
- **fal.ai:** create a key at fal.ai, then set it as an environment variable named `FAL_KEY`
  - Windows: `setx FAL_KEY "your-key"`, then reopen the terminal
  - Mac: add `export FAL_KEY="your-key"` to `~/.zshrc`, then reopen the terminal
- **ListenHub:** `npm install -g @marswave/listenhub-cli@latest`, then `listenhub openapi config set-key`
- **Local GPU:** run the setup wizard — it tells you which models fit your VRAM and guides the install

> 🔐 Never paste API keys into the chat. TalkFrame only checks whether a key **exists**; it never reads, prints or stores it.

**5. Restart Claude Code.** The first time you use TalkFrame, the setup wizard runs automatically.

### 🚀 How to use

Just ask Claude, for example:

- *"Use TalkFrame to make a talking video from `me.jpg`. Script: Hi, I'm Ryan…"*
- *"Photo `host.png` and audio `intro.m4a` — make a 9:16 talking-head video."*
- *"Clone my voice from `sample.m4a`, then make the avatar say this script."*
- *"The face looks off. Redo it in conservative mode."*

What happens next:
1. Claude checks your photo and voice, then shows **one confirmation card** with the route, mode and estimated cost
2. It makes **segment 1 first** so you can check it
3. You approve, then it makes the rest, checks every clip and assembles `final.mp4`

### 💡 Tips for the best lip sync

- 📸 A front-facing, sharp photo with **closed or relaxed lips**, even light and one person
- 🎧 Clean voice with no background music — add music after the video is made
- 🐢 A slightly slow pace (about 0.9×) gives cleaner mouth shapes
- ✂️ Short sentences with clear pauses; long audio is split at those pauses
- 🎬 For long scripts, a small cut is visible where segments join — cover it with B-roll or a zoom in your editor

### ⚠️ Current limitations (v0.1 preview)

- Video generation needs a cloud API key or a local GPU; Claude alone cannot render video
- Each segment starts from the photo pose, so long videos have small cuts at the joins
- Real-world quality varies by photo and model — always test a short clip first
- No subtitles yet (planned)

### 🛡️ Responsible use & disclaimer

- Use only photos and voices of **people who have given consent**
- **Do not** create videos of public figures or minors, or use TalkFrame for impersonation, fake endorsements, fraud or misinformation
- Label AI-generated videos clearly where you publish them; TalkFrame adds an "AI Generated" label by default
- Model providers have their own terms and content rules. Uploaded files are stored by those providers
- This software is provided "as is". The author is not responsible for how it is used or for any provider charges

### 🙏 Acknowledgements

Built on great work by:
[fal.ai](https://fal.ai) · Kling AI Avatar (Kuaishou) · OmniHuman (ByteDance) · [InfiniteTalk](https://github.com/MeiGen-AI/InfiniteTalk) · [Sync](https://sync.so) · MiniMax Speech · [ListenHub](https://listenhub.ai) / PixVerse · [MuseTalk](https://github.com/TMElyralab/MuseTalk) · [LatentSync](https://github.com/bytedance/LatentSync) · [SadTalker](https://github.com/OpenTalker/SadTalker) · [edge-tts](https://github.com/rany2/edge-tts) · [FFmpeg](https://ffmpeg.org) · [Anthropic Claude](https://www.anthropic.com)

### 👤 About the author

Made by **Ryan Yan**, a data analyst.

### 📄 License & copyright

Copyright © 2026 Ryan Yan. Released under the [MIT License](LICENSE).
Third-party models and services keep their own licenses and terms.

---

## 🇨🇳 中文

### 📌 项目简介

TalkFrame 是一个 Claude 技能：给它**一张人物照片**和**一段文案或录音**，就能生成**会说话的数字人视频**。嘴型跟着内容动，脸和照片保持一致，动作自然克制。

生成方式由你选：**云端 API**（fal.ai 或 ListenHub）或者**自己电脑的显卡**。其余的事情都交给 Claude：检查环境、处理照片和声音、选择模型、质检、拼接成片。

默认中文输出，主要面向中文创作者，也支持英文。

### 😣 解决什么问题

| 痛点 | TalkFrame 怎么解决 |
|---|---|
| 很多数字人工具会让**脸变形**：下巴变了、牙齿奇怪、眼睛乱动 | 两种模式。效果不好时自动建议切换**保守模式**，**只改嘴部**，脸不会变 |
| **口型对不上**，或者停顿时嘴还在动 | 音频先清理，再按停顿切段；每一段都逐帧检查，还会专门检查**停顿时的画面** |
| **动作太夸张**：大笑、挥手、摇头 | 默认使用克制的提示词：只眨眼、呼吸、轻微动头 |
| 每个平台用法都不一样，**被一家绑定** | 一套流程，支持多家：fal.ai（Kling Avatar、OmniHuman、InfiniteTalk、Sync）、ListenHub、本地开源模型 |
| 生成失败**白花钱** | 先检查素材，再显示费用，先试一小段，付费任务不会在你不知情时自动重试 |
| 普通人**不会配置** | 第一次运行有设置向导，自动检查电脑，告诉你缺什么、怎么装 |
| 手机照片**方向错乱或被拉伸**，iPhone **HEIC** 格式读不了 | 自动按正确方向摆正照片，支持 HEIC |

### ✨ 功能

- 🧙 **设置向导**：检测工具、Key（只看有没有）、显卡和显存，保存你的可用方案
- 🖼️ **照片检查**：自动挑最好的一张，提示有风险的照片（侧脸、大笑露牙、眼镜反光），裁成 9:16、16:9、1:1 或 3:4
- 🗣️ **多种声音**：自己的录音、克隆声音，或现成配音（fal 上的 MiniMax、ListenHub、免费的 Edge TTS）
- 🎬 **两种模式**
  - **自然模式**：照片＋声音一步生成
  - **保守模式**：先做几乎不动的底片视频，再只改嘴型（不笑、不动，只张嘴说话）
- 🔍 **自动质检**：照片和视频帧拼成对比图，检查停顿时的画面和时长
- 🔁 **自动兜底**：脸变形 → 改保守模式；嘴模糊 → 换更清晰的模型；口型慢半拍 → 放慢语速、缩短分段
- 🧩 **长视频**：按自然停顿切段，生成后自动拼接
- 🏷️ **合规默认开启**：确认已获得本人授权，画面角落显示"AI Generated"（可关闭），文件信息里也写明 AI 生成
- 📒 **越用越好**：记录每次哪种照片、模型、语速效果好，下次直接用

### ⚙️ 工作流程

```
照片 ─┐
      ├─► 检查与处理 ─► 选择方案 ─► 生成 ─► 质检 ─► 成片
声音 ─┘                    │
                           ├─ 自然模式：Kling Avatar / OmniHuman / InfiniteTalk / SadTalker
                           └─ 保守模式：静止底片 + Sync 对口型 / PixVerse / LatentSync / MuseTalk
```

### 🧭 选择生成方式

**至少需要一种**生成视频的方式。声音可以用别家的，自由搭配。

| 方式 | 需要什么 | 适合 |
|---|---|---|
| ☁️ **fal.ai**（推荐） | 一个 `FAL_KEY`（按秒付费） | 效果最好、设置最简单，一个 Key 同时包含视频和配音 |
| ☁️ **ListenHub** | ListenHub 命令行工具 + API Key（用积分） | 已经有 ListenHub 积分的用户 |
| 💻 **本地显卡** | NVIDIA 显卡（显存约 6–8 GB 以上）+ 自己安装模型 | 免费、隐私好，但速度慢 |

fal.ai 参考价（2026 年 11 月，价格会变，以 fal 官网为准）：
Kling Avatar v2 标准版 ≈ $0.056/秒 · 专业版 ≈ $0.115/秒 · OmniHuman 1.5 ≈ $0.16/秒 · Sync lipsync-2 ≈ $0.05/秒。
**一条 30 秒的视频大约 $1.5–$5。**

### 📦 安装

**1. 准备环境**
- [Claude Code](https://docs.claude.com)（推荐，因为这个技能需要在你电脑上运行脚本）
- Python 3.9 或以上
- ffmpeg：Windows 运行 `winget install Gyan.FFmpeg`，Mac 运行 `brew install ffmpeg`

**2. 安装技能**

Mac / Linux：
```bash
git clone https://github.com/sf-ryanyan/talkframe.git ~/.claude/skills/talkframe
```
Windows（PowerShell）：
```powershell
git clone https://github.com/sf-ryanyan/talkframe.git "$env:USERPROFILE\.claude\skills\talkframe"
```
没装 git？点仓库页面的 **Code → Download ZIP**，解压后把文件夹改名为 `talkframe`，放到上面的路径。

**3. 安装 Python 依赖**
```bash
pip install fal-client pillow pillow-heif edge-tts
```

**4. 至少连接一种生成方式**
- **fal.ai**：在 fal.ai 创建 Key，设置成环境变量 `FAL_KEY`
  - Windows：运行 `setx FAL_KEY "你的Key"`，然后重新打开终端
  - Mac：在 `~/.zshrc` 里加一行 `export FAL_KEY="你的Key"`，然后重新打开终端
- **ListenHub**：运行 `npm install -g @marswave/listenhub-cli@latest`，再运行 `listenhub openapi config set-key`
- **本地显卡**：运行设置向导，它会告诉你的显存能跑哪些模型，并一步步指导安装

> 🔐 不要把 API Key 粘贴到聊天里。TalkFrame 只检查 Key **是否存在**，不会读取、显示或保存它。

**5. 重启 Claude Code。** 第一次使用时会自动运行设置向导。

### 🚀 使用方法

直接跟 Claude 说，例如：

- "用 TalkFrame 把 `me.jpg` 做成说话视频，文案是：大家好，我是……"
- "照片 `host.png`，音频 `intro.m4a`，做一个竖屏数字人视频"
- "用 `sample.m4a` 克隆我的声音，再让数字人说这段文案"
- "脸不太对，用保守模式重做"

接下来会这样进行：
1. Claude 检查照片和声音，给你一张**确认卡片**，写清方案、模式和预估费用
2. **先做第 1 段**给你看
3. 你确认后再做剩下的部分，每段都质检，最后拼成 `final.mp4`

### 💡 让口型更准的技巧

- 📸 正脸、清晰，**嘴巴自然闭着**，光线均匀，只有一个人
- 🎧 声音干净、不要背景音乐（音乐等视频做好后再加）
- 🐢 语速稍慢一点（约 0.9 倍），嘴型更清楚
- ✂️ 句子短一些、停顿清楚，长音频会在停顿处切段
- 🎬 长文案分段的接口处会有一个小跳切，可以在剪辑软件里用空镜或缩放盖住

### ⚠️ 当前限制（v0.1 预览版）

- 生成视频必须有云端 API Key 或本地显卡，Claude 本身不能生成视频
- 每一段都从照片的姿势开始，所以长视频在分段接口处会有小跳切
- 实际效果因照片和模型而异，建议先试一小段
- 暂不支持字幕（已在计划中）

### 🛡️ 合理使用与免责声明

- 只使用**本人或已获得本人授权**的照片和声音
- **不要**制作公众人物或未成年人的视频，不要用于冒充他人、虚假代言、诈骗或传播虚假信息
- 发布时请清楚标注 AI 生成；TalkFrame 默认会加 "AI Generated" 标记
- 各模型平台有自己的使用条款和内容规则，上传的文件会存储在这些平台上
- 本软件按"现状"提供，作者不对使用方式及平台产生的费用承担责任

### 🙏 致谢

感谢以下项目和服务：
[fal.ai](https://fal.ai) · Kling AI Avatar（快手）· OmniHuman（字节跳动）· [InfiniteTalk](https://github.com/MeiGen-AI/InfiniteTalk) · [Sync](https://sync.so) · MiniMax Speech · [ListenHub](https://listenhub.ai) / PixVerse · [MuseTalk](https://github.com/TMElyralab/MuseTalk) · [LatentSync](https://github.com/bytedance/LatentSync) · [SadTalker](https://github.com/OpenTalker/SadTalker) · [edge-tts](https://github.com/rany2/edge-tts) · [FFmpeg](https://ffmpeg.org) · [Anthropic Claude](https://www.anthropic.com)

### 👤 关于作者

**Ryan Yan**，一名数据分析师。

### 📄 许可与版权

Copyright © 2026 Ryan Yan，基于 [MIT 许可证](LICENSE) 开源。
第三方模型和服务各自遵循其许可证和使用条款。
