"""Usage: python3 harness.py option-B_live-pacer 20        (live pacer at 20x speed)
       python3 harness.py option-A_video 4 file:///path/clip.webm 2   (needs a WebM clip; headless Chromium lacks H.264)
Run a Qualtrics question (HTML + JS) in headless Chromium with a mocked SurveyEngine."""
import asyncio, sys, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
from playwright.async_api import async_playwright

MOCK = """
window.__ed = {}; window.__next = 'unknown';
window.Qualtrics = { SurveyEngine: {
  _onload: null,
  addOnload(fn) { this._onload = fn; },
  addOnUnload(fn) {},
  setJSEmbeddedData(k, v) { window.__ed['__js_' + k] = v; },
  setEmbeddedData(k, v) { window.__ed[k] = v; }
}};
"""
def page_html(qdir, speed, video_url=None):
    html = (qdir / "question.html").read_text()
    js = (qdir / "question.js").read_text()
    if video_url: js = js.replace("https://YOUR-HOST.example/pacer_circle_4-6_full_session_silent.mp4", video_url)
    speedup = f"""
      const _pn = performance.now.bind(performance), _t0 = _pn();
      performance.now = () => _t0 + (_pn() - _t0) * {speed};
    """ if speed != 1 else ""
    return f"""<!doctype html><html><body>
    <script>{MOCK}{speedup}</script>
    <div id="QID1">{html}</div>
    <script>{js}</script>
    <script>
      const ctxObj = {{
        hideNextButton() {{ window.__next = 'hidden'; }},
        showNextButton() {{ window.__next = 'shown'; }},
        getQuestionContainer() {{ return document.getElementById('QID1'); }}
      }};
      Qualtrics.SurveyEngine._onload.call(ctxObj);
    </script></body></html>"""

async def run(option, speed, video_url, hide_at, wait_s):
    qdir = ROOT / "qualtrics" / option
    out = ROOT / "tests" / f"{option}.html"
    out.write_text(page_html(qdir, speed, video_url))
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--autoplay-policy=user-gesture-required"])
        pg = await b.new_page(viewport={"width": 1200, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(f"file://{out}")
        print("next after load:", await pg.evaluate("window.__next"))
        await pg.click("#spb-start")
        if option.startswith("option-A"):
            await pg.wait_for_timeout(500)
            await pg.evaluate(f"document.querySelector('#spb-video').playbackRate = {speed}")
            # a forward seek attempt should be snapped back
            await pg.evaluate("const v=document.querySelector('#spb-video'); v.currentTime = v.currentTime + 120;")
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path=str(out.with_suffix('.running.png')))
        if hide_at:
            await pg.wait_for_timeout(hide_at * 1000)
            # simulate a tab switch
            await pg.evaluate("""Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
                                 document.dispatchEvent(new Event('visibilitychange'));""")
            await pg.wait_for_timeout(2000)
            await pg.evaluate("""Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});
                                 document.dispatchEvent(new Event('visibilitychange'));""")
            await pg.wait_for_timeout(300)
            print("status after return:", await pg.inner_text("#spb-status"))
            print("next while paused:", await pg.evaluate("window.__next"))
            await pg.click("#spb-resume")
        for _ in range(int(wait_s)):
            await pg.wait_for_timeout(1000)
            if await pg.evaluate("window.__next") == "shown": break
        await pg.screenshot(path=str(out.with_suffix('.end.png')))
        print("next at end:", await pg.evaluate("window.__next"))
        print("status:", await pg.inner_text("#spb-status"))
        ed = await pg.evaluate("window.__ed")
        print(json.dumps({k: v for k, v in ed.items() if k.startswith('__js_') and k != '__js_spb_ua'}, indent=1))
        print("page errors:", errs)
        await b.close()

if __name__ == "__main__":
    option, speed = sys.argv[1], float(sys.argv[2])
    video = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else None
    hide_at = float(sys.argv[4]) if len(sys.argv) > 4 else 0
    asyncio.run(run(option, speed, video, hide_at, 200))
