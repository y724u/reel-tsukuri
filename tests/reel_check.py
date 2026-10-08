# 動画づくりの道具の試験。iPhone の縦撮りに似せた素材（HEVC・回して表示する印つき）を作り、
# Pillow で縦書きのテロップを作って重ね、H.264 でつないで書き出し、できあがりを確かめる。
# kit/CLAUDE.md の「道具」「テロップ」「書き出し」の決まりと同じやり方を使う。
import os, platform, subprocess, sys, time

import PIL
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
FONT_M = "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc"
FONT_G = "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
bad = []


def ff(args):
    r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y"] + args, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr)
        sys.exit(f"ffmpeg が失敗: {args}")


def info(path):  # この ffmpeg には ffprobe が無いので -i の表示を読む（終了コード1は正常）
    return subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True).stderr


def step(name, t):
    print(f"{name}: {time.time() - t:.1f}秒")
    return time.time()


print(f"python {platform.machine()} / Pillow {PIL.__version__} / ffmpeg {os.path.basename(FF)}")
t = time.time()

# 1. 素材: iPhone の縦撮りと同じ、横 3840x2160・59.94fps の HEVC に「回して表示する」印（-90度）を付けた3本（各3秒）
clips = []
for i, src in enumerate(["testsrc2", "smptehdbars", "testsrc"], 1):
    raw, mov = f"{OUT}/raw{i}.mov", f"{OUT}/clip{i}.mov"
    ff(["-f", "lavfi", "-i", f"{src}=size=3840x2160:rate=60000/1001", "-t", "3",
        "-c:v", "libx265", "-tag:v", "hvc1", "-pix_fmt", "yuv420p", "-x265-params", "log-level=error", raw])
    ff(["-display_rotation:v:0", "-90", "-i", raw, "-c", "copy", mov])
    if "displaymatrix" not in info(mov):
        bad.append(f"素材{i}に回転の印が付かなかった")
    clips.append(mov)
t = step("素材を作る", t)

# 2. テロップ: 1文字ずつ上から並べる。ー〜 とかっこは回す、、。は右上に寄せる
for p in (FONT_M, FONT_G):
    if not os.path.exists(p):
        bad.append(f"フォントが無い: {p}")


def tate(text, path, index, fill, stroke=0, stroke_fill=None, size=90):
    f = ImageFont.truetype(path, size, index=index)
    cell = int(size * 1.3)
    im = Image.new("RGBA", (cell, cell * len(text)), (0, 0, 0, 0))
    for i, ch in enumerate(text):
        c = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
        ImageDraw.Draw(c).text((cell // 2, cell // 2), ch, font=f, fill=fill, anchor="mm",
                               stroke_width=stroke, stroke_fill=stroke_fill)
        if ch in "ー〜「」（）":
            c = c.rotate(-90)
        elif ch in "、。":
            s = int(cell * 0.6)
            c = c.transform(c.size, Image.AFFINE, (1, 0, -s, 0, 1, s))
        im.alpha_composite(c, (0, i * cell))
    return im


telops = []
for i, args in enumerate([("縦書きの、確認。", FONT_M, 2, "white"),
                          ("長音ーと「かぎ」", FONT_G, 0, (255, 220, 0), 6, "black"),
                          ("テスト", FONT_M, 2, "white")], 1):
    canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    tel = tate(*args)
    canvas.alpha_composite(tel, (1080 - tel.width - 60, 160))
    p = f"{OUT}/telop{i}.png"
    canvas.save(p)
    telops.append(p)
t = step("テロップを作る", t)

# 3. 1本ずつ、回転の印を 0 にして画そのものを時計回りに回し、1080x1920・30fps にしてテロップを重ね、
#    H.264 で書き出してつなぐ（完成品に回転の印を残さない）
ENC = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30"]
cuts = []
for i, (clip, tel) in enumerate(zip(clips, telops), 1):
    cut = f"{OUT}/cut{i}.mp4"
    ff(["-display_rotation", "0", "-i", clip, "-i", tel, "-filter_complex",
        "[0:v]transpose=clock,fps=30,scale=1080:1920:flags=lanczos,setsar=1[v];[v][1:v]overlay=0:0,format=yuv420p[o]",
        "-map", "[o]", "-frames:v", "90"] + ENC + [cut])
    cuts.append(cut)
with open(f"{OUT}/list.txt", "w") as lf:
    lf.writelines(f"file '{c}'\n" for c in cuts)
final = f"{OUT}/final.mp4"
ff(["-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt", "-c", "copy", final])
t = step("書き出し", t)

# 4. できあがりを確かめる
s = info(final)
for word, why in [("Video: h264", "H.264 でない"), ("1080x1920", "縦 1080x1920 でない"), ("Duration: 00:00:09.00", "長さが9秒でない")]:
    if word not in s:
        bad.append(why)
for word in ("displaymatrix", "rotate"):
    if word in s:
        bad.append(f"完成品に回転の印（{word}）が残った")
ff(["-ss", "1.5", "-i", final, "-frames:v", "1", "-vf", "scale=360:-1", f"{OUT}/frame.jpg"])
print("\n".join(l.strip() for l in s.splitlines() if "Duration" in l or "Stream" in l))

if bad:
    sys.exit("だめ: " + " / ".join(bad))
print("ぜんぶ通った")
