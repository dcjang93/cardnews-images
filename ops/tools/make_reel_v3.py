"""릴스 v3 (2026-11-28, 첫 3초 이탈 개선판)
기준선: 릴스 평균 시청 2.3~3.7초(24초 영상) → 대부분 표지에서 이탈.
바뀐 점
 1) 0.9초 '훅 프레임': 큰 주황 숫자 + 짧은 두 줄 (cards.json 의 reel_hook) — 첫 장면부터 결론을 던진다.
 2) 표지에 천천히 확대(줌인) 움직임 → 정지 화면처럼 보이지 않게.
 3) 위쪽 띠: 시리즈명 + 훅 한 줄을 영상 내내 고정 → 어느 장에서 들어와도 '무슨 얘기'인지 보인다.
 4) 진행 점(●○○…): 몇 장 남았는지 보여 줘서 끝까지 보게.
 5) 장 길이: 표지 2.0초, 항목 2.6초, 정리 3.4초, 마지막 3.0초.
사용법: python3 make_reel_v3.py <카드폴더> <cards.json> [출력파일]
  cards.json 에 선택 항목:
   "reel_hook": {"big": "14조 원", "line1": "모르면 계속 잠자는", "line2": "내 돈, 지금 찾으세요"}
   "reel_top": "모르면 손해 · 잠자는 내 돈 찾기"   (없으면 표지 kicker + title1)
출력 끝에 THUMB_MS=<ms> 를 찍는다 → Buffer thumbnailOffset 에 그대로 넣는다(표지가 썸네일이 되게).
"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FD = Path.home() / ".local/share/fonts"
def F(w, s): return ImageFont.truetype(str(FD / f"Pretendard-{w}.otf"), s)
NAVY, ORANGE, WHITE, DIM = (15, 39, 66), (255, 122, 26), (255, 255, 255), (150, 165, 185)
W, H, CARD_Y = 1080, 1920, 300          # 카드(1080x1350)는 y=300~1650. 아래 270px 는 인스타 UI 영역이라 비워 둔다.

d = Path(sys.argv[1]); spec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
out = sys.argv[3] if len(sys.argv) > 3 else str(d / "reel.mp4")
cards = sorted(d.glob("card_*.jpg")); n = len(cards)
cover = spec["cards"][0]
top_text = spec.get("reel_top") or f'{cover.get("kicker","")} · {cover.get("title1","")}'.strip(" ·")

def fit(draw, text, weight, size, maxw):
    while size > 30 and draw.textlength(text, font=F(weight, size)) > maxw: size -= 2
    return F(weight, size)

def frame(card_path, idx):
    f = Image.new("RGB", (W, H), NAVY); dr = ImageDraw.Draw(f)
    ft = fit(dr, top_text, "Bold", 46, W - 120)
    dr.text((W // 2, 150), top_text, font=ft, fill=WHITE, anchor="mm")
    dr.rounded_rectangle((W // 2 - 44, 196, W // 2 + 44, 202), radius=3, fill=ORANGE)
    gap = 26; x0 = W // 2 - gap * (n - 1) / 2                       # 진행 점
    for k in range(n):
        r = 8 if k == idx else 5
        dr.ellipse((x0 + k * gap - r, 250 - r, x0 + k * gap + r, 250 + r), fill=ORANGE if k <= idx else DIM)
    f.paste(Image.open(card_path).convert("RGB"), (0, CARD_Y))
    return f

frames = []
for i, c in enumerate(cards):
    p = d / f"reel_{i+1:02d}.png"; frame(c, i).save(p); frames.append(p)

hook = spec.get("reel_hook"); seq = []; durs = []
if hook:
    f = Image.new("RGB", (W, H), NAVY); dr = ImageDraw.Draw(f)
    fb = fit(dr, hook["big"], "Black", 230, W - 120)
    dr.text((W // 2, 820), hook["big"], font=fb, fill=ORANGE, anchor="mm")
    for k, key in enumerate(("line1", "line2")):
        if hook.get(key):
            dr.text((W // 2, 1040 + k * 96), hook[key], font=fit(dr, hook[key], "ExtraBold", 76, W - 140), fill=WHITE, anchor="mm")
    p = d / "reel_00.png"; f.save(p); seq.append(p); durs.append(0.9)
seq += frames
durs += [2.0] + [2.6] * max(0, n - 3) + ([3.4, 3.0] if n >= 3 else [2.6] * (n - 1))
T = 0.3
inp = []
for p, t in zip(seq, durs): inp += ["-framerate", "30", "-loop", "1", "-t", f"{t + T:.2f}", "-i", str(p)]
inp += ["-f", "lavfi", "-t", f"{sum(durs) + T:.2f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
ci = 1 if hook else 0                                   # 표지 입력 번호
fc = []
for i in range(len(seq)):
    if i == ci:   # 표지 줌인 (1.00 → 1.05)
        fc.append(f"[{i}:v]scale=2160:3840,zoompan=z='min(1+0.0009*on,1.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps=30,setsar=1[s{i}]")
    else:
        fc.append(f"[{i}:v]fps=30,setsar=1[s{i}]")
prev = "[s0]"   # 입력 길이 = 장 길이 + T 이므로 i번째 전환 시작 = 앞 장 길이 합
for i in range(1, len(seq)):
    tr = "fade" if (hook and i == 1) else "slideleft"
    fc.append(f"{prev}[s{i}]xfade=transition={tr}:duration={T}:offset={sum(durs[:i]):.2f}[v{i}]"); prev = f"[v{i}]"
fc.append(f"{prev}format=yuv420p[vout]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inp + ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", f"{len(seq)}:a",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out], check=True)
print(out)
print(f"THUMB_MS={int((durs[0] + 0.5) * 1000) if hook else 300}")
