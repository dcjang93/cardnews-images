"""카드뉴스 렌더러 v2 (신뢰형 에디토리얼 디자인): cards.json -> 1080x1350 JPG.
사용법: python3 render_cards_v2.py cards.json 출력폴더
글자가 칸을 넘치면 크기를 줄이지 않고 errors 로 알린다.
"""
import base64, html, json, mimetypes, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

W, H = 1080, 1350
NAVY, ORANGE, INK, GRAY, LIGHT, LINE = "#0F2742", "#FF7A1A", "#111827", "#5B6472", "#F3F4F6", "#D9DDE3"
e = html.escape

CSS = f"""
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{W}px; height:{H}px; font-family:'Pretendard','Noto Sans CJK KR',sans-serif; overflow:hidden;
        -webkit-font-smoothing:antialiased; font-feature-settings:'tnum'; }}
.card {{ position:relative; width:{W}px; height:{H}px; overflow:hidden; }}
.head {{ position:absolute; top:56px; left:72px; right:72px; display:flex; justify-content:space-between; align-items:center;
         font-size:26px; font-weight:600; letter-spacing:-0.2px; }}
.foot {{ position:absolute; bottom:48px; left:72px; right:72px; padding-top:22px; border-top:2px solid {LINE};
         display:flex; justify-content:space-between; font-size:24px; font-weight:500; color:{GRAY}; }}
.dark .foot {{ border-color:rgba(255,255,255,.25); color:rgba(255,255,255,.7); }}
.tag {{ border:2px solid currentColor; border-radius:999px; padding:6px 18px; font-size:24px; font-weight:600; }}
.kicker {{ display:inline-block; background:{ORANGE}; color:#fff; font-size:30px; font-weight:700; padding:8px 20px; border-radius:8px; }}
.t1 {{ font-weight:800; letter-spacing:-2.5px; line-height:1.18; white-space:nowrap; }}
.num {{ font-weight:800; color:{ORANGE}; letter-spacing:-4px; line-height:1; white-space:nowrap; }}
.unit {{ font-size:56px; font-weight:700; letter-spacing:-1px; margin-left:8px; color:{INK}; }}
.desc {{ font-size:42px; font-weight:500; color:{INK}; line-height:1.55; letter-spacing:-1px; white-space:nowrap; }}
.rule {{ width:88px; height:6px; background:{ORANGE}; border-radius:3px; }}
.li {{ display:flex; align-items:center; gap:22px; padding:20px 0; border-bottom:2px solid {LINE};
       font-size:40px; font-weight:600; color:{INK}; letter-spacing:-1px; white-space:nowrap; }}
.li:last-child {{ border-bottom:0; }}
.li b {{ flex:0 0 52px; height:52px; border-radius:50%; background:{NAVY}; color:#fff; font-size:28px; font-weight:700;
         display:flex; align-items:center; justify-content:center; }}
.chk {{ display:flex; align-items:center; gap:24px; padding:26px 0; border-bottom:2px solid rgba(255,255,255,.18);
        font-size:44px; font-weight:600; color:#fff; letter-spacing:-1px; white-space:nowrap; }}
.chk b {{ flex:0 0 52px; height:52px; border-radius:12px; background:{ORANGE}; color:#fff; font-size:32px;
          display:flex; align-items:center; justify-content:center; }}
.photo {{ background-size:cover; background-position:center; }}
"""

def img_url(path):
    if not path or not Path(path).exists():
        return None
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()

def head(spec, color):
    return f'<div class="head" style="color:{color}"><span>{e(spec.get("brand",""))}</span><span class="tag">{e(spec.get("category",""))}</span></div>'

def foot(spec, page):
    return f'<div class="foot"><span>출처 · {e(spec.get("source",""))}</span><span>{page}</span></div>'

def listcover(c, spec, url, page):
    bg = f"background-image:url('{url}');" if url else f"background:{LIGHT};"
    items = ''.join(f'<div class="li fit"><b>{k}</b><span>{e(x)}</span></div>' for k, x in enumerate(c['items'], 1))
    kicker = f'<div class="kicker">{e(c["kicker"])}</div>' if c.get('kicker') else ''
    return f"""<div class="card">
<div class="photo" style="position:absolute;inset:0;{bg}"></div>
<div style="position:absolute;left:0;right:0;top:0;height:640px;background:linear-gradient({NAVY} 78%,rgba(15,39,66,0));"></div>
{head(spec, '#fff')}
<div style="position:absolute;top:150px;left:72px;right:72px;">
  {kicker}
  <div class="t1 fit" style="font-size:92px;color:#fff;margin-top:26px">{e(c['title1'])}</div>
  <div class="t1 fit" style="font-size:92px;color:{ORANGE}">{e(c['title2'])}</div>
</div>
<div style="position:absolute;left:72px;right:72px;top:560px;background:#fff;border-radius:28px;padding:18px 44px;
            box-shadow:0 18px 50px rgba(15,39,66,.25);">{items}</div>
<div style="position:absolute;right:72px;bottom:56px;background:{NAVY};color:#fff;font-size:26px;font-weight:600;padding:12px 26px;border-radius:999px;">넘겨서 자세히 보기 →</div>
</div>"""

def item(c, spec, url, page):
    badge = c.get('badge', '')
    m = re.match(r'^\s*(\d+)\s*/\s*(\d+)\s*$', badge)
    if m:
        badge_html = f'<div style="font-size:30px;font-weight:700;color:{ORANGE};letter-spacing:1px">POINT <span style="font-size:64px;font-weight:800;letter-spacing:-2px;margin-left:6px">{int(m.group(1)):02d}</span><span style="color:{GRAY};font-size:30px"> / {int(m.group(2)):02d}</span></div>'
    else:
        badge_html = f'<div class="kicker">{e(badge)}</div>' if badge else ''
    num = ''
    if c.get('number'):
        unit = f'<span class="unit">{e(c["unit"])}</span>' if c.get('unit') else ''
        num = f'<div class="num fit" style="font-size:136px;margin-top:40px">{e(c["number"])}{unit}</div>'
    descs = ''.join(f'<div class="desc fit">{e(x)}</div>' for x in c.get('desc', []))
    photo = ''
    if url:
        photo = f'<div class="photo" style="position:absolute;left:72px;right:72px;bottom:130px;height:330px;border-radius:24px;background-image:url(\'{url}\');background-position:center 72%;"></div>'
    return f"""<div class="card" style="background:#fff">
{head(spec, NAVY)}
<div style="position:absolute;top:150px;left:72px;right:72px;">
  {badge_html}
  <div class="t1 fit" style="font-size:70px;color:{NAVY};margin-top:28px">{e(c['title1'])}</div>
  <div class="t1 fit" style="font-size:70px;color:{NAVY}">{e(c['title2'])}</div>
  <div class="rule" style="margin-top:34px"></div>
  {num}
  <div style="margin-top:30px">{descs}</div>
</div>
{photo}
{foot(spec, page)}
</div>"""

def summary(c, spec, url, page):
    rows = ''.join(f'<div class="chk fit"><b>✓</b><span>{e(x)}</span></div>' for x in c['checks'])
    return f"""<div class="card dark" style="background:{NAVY}">
{head(spec, '#fff')}
<div style="position:absolute;top:150px;left:72px;right:72px;">
  <div class="kicker">SUMMARY</div>
  <div class="t1 fit" style="font-size:78px;color:#fff;margin-top:26px">{e(c.get('title','한눈에 정리'))}</div>
  <div style="margin-top:40px">{rows}</div>
</div>
<div style="position:absolute;left:72px;bottom:130px;font-size:32px;font-weight:600;color:{ORANGE}">저장해 두고 필요할 때 꺼내 보세요</div>
{foot(spec, page)}
</div>"""

def last(c, spec, url, page):
    return f"""<div class="card" style="background:{LIGHT}">
{head(spec, NAVY)}
<div style="position:absolute;top:0;bottom:0;left:72px;right:72px;display:flex;flex-direction:column;justify-content:center;">
  <div class="kicker" style="align-self:flex-start">오늘 할 일</div>
  <div style="margin-top:30px;background:{NAVY};border-radius:28px;padding:48px 48px;">
    <div class="t1 fit" style="font-size:66px;color:#fff">{e(c['action'])}</div>
  </div>
  <div class="desc fit" style="margin-top:44px">{e(c.get('line1',''))}</div>
  <div class="desc fit">{e(c.get('line2',''))}</div>
  <div style="margin-top:56px;font-size:34px;font-weight:700;color:{ORANGE}">{e(c.get('footer','저장해 두고 확인해 보세요'))}</div>
</div>
{foot(spec, page)}
</div>"""

T = {"listcover": listcover, "item": item, "summary": summary, "last": last}

def main(spec_path, out_dir):
    spec_path = Path(spec_path); out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    cards = spec["cards"]; n = len(cards)
    files, errors = [], []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome") if Path("/usr/bin/google-chrome").exists() else p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for i, c in enumerate(cards, 1):
            url = img_url(spec_path.parent / c["photo"]) if c.get("photo") else None
            body = T[c["type"]](c, spec, url, f"{i:02d} / {n:02d}")
            pg.set_content(f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(200)
            over = pg.evaluate(f"""() => [...document.querySelectorAll('.fit')]
                .filter(el => {{ const r = el.getBoundingClientRect(); return r.left < 60 || r.right > {W-60} || el.scrollWidth > el.clientWidth + 2; }})
                .map(el => el.textContent)""")
            if over:
                errors.append(f"{i}장 글자가 너무 길어요: {over}")
            f = out / f"card_{i:02d}.jpg"
            pg.screenshot(path=str(f), type="jpeg", quality=93)
            files.append(str(f))
        b.close()
    print(json.dumps({"files": files, "errors": errors}, ensure_ascii=False, indent=1))
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
