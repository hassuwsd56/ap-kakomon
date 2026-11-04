"""中断ボタンと、タスクキル（強制終了）後のデータの残り方のテスト
実行: "/c/Users/skyio/anaconda3/python.exe" tests/test_interrupt.py
"""
import json, os, shutil, sys, tempfile
sys.path.insert(0, os.path.expanduser("~/.claude/skills/webapp-test/scripts"))
import cdp
from cdp import Browser, Checker, serve

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
URL = serve(ROOT)
KEY = "ap-kakomon_v1"
OUT = os.path.join(os.environ.get("TEMP", "."), "ap-kakomon-shots")
os.makedirs(OUT, exist_ok=True)
ALL = {q["id"]: q for e in json.load(open(os.path.join(ROOT, "data", "exams.json"), encoding="utf-8"))
       for q in json.load(open(os.path.join(ROOT, "data", f"{e}.json"), encoding="utf-8"))["qs"]}
BLANK = {"version": 1, "ans": {}, "marks": {}, "history": [], "settings": {"count": 10, "genres": []}, "cur": None}

def state(b): return b.js(f"JSON.parse(localStorage.getItem('{KEY}'))")
def text(b): return b.js("document.body.innerText")
def answer(b, correct=True):
    c = state(b)["cur"]; q = ALL[c["ids"][c["i"]]]
    b.tap_el(f"[data-pick='{q['ans'] if correct else (q['ans'] + 1) % 4}']")
    return q["id"]

ck = Checker()

with Browser() as b:
    with ck.step("中断ボタン"):
        b.open(URL, seed={KEY: BLANK})
        b.tap_el("[data-act=start]")
        ck.check("問題画面の左上に「中断」ボタンがある", "中断" in b.js("document.querySelector('.qbar [data-act=quit]').innerText"))
        ck.check("問題画面の下にも中断ボタンがある", b.exists(".quitlow"))
        b.screenshot(os.path.join(OUT, "11_quit_button.png"))
        answer(b); b.tap_el("[data-act=next]")
        answer(b, correct=False); b.tap_el("[data-act=next]")
        b.tap_el(".quitlow")
        ck.check("確認なしで出題画面に戻る", b.exists("[data-act=start]") and not b.exists("#choices"))
        ck.check("「中断しました」と表示される", "中断しました" in text(b))
        ck.check("「続きから解く」に 2 / 10 問 回答済み", "2 / 10 問 回答済み" in text(b))
        b.screenshot(os.path.join(OUT, "12_after_quit.png"))
        b.tap_el("[data-act=resume]")
        ck.check("再開すると 3 問目から", "3 / 10" in text(b))
        b.tap_el(".qbar [data-act=quit]")
        ck.check("左上の中断ボタンでも戻れる", b.exists("[data-act=resume]"))
        b.js("startQuiz([Object.keys(QM)[0]], 'single')"); b.pump(0.3)
        ck.check("1 問だけ開いたときは「閉じる」と表示", "閉じる" in b.js("document.querySelector('.qbar [data-act=quit]').innerText") and not b.exists(".quitlow"))
        b.tap_el(".qbar [data-act=quit]")
        ck.check("JS エラーなし", not b.errors, b.errors)

# ---------- タスクキル ----------
# 同じ保存領域（プロファイル）で、強制終了 → 起動し直す
prof = tempfile.mkdtemp(prefix="ap-kill-")
orig = tempfile.mkdtemp
cdp.tempfile.mkdtemp = lambda prefix="": prof
try:
    b = Browser()
    b.open(URL, seed={KEY: BLANK})
    b.tap_el("[data-act=start]")
    done = []
    for k in range(3):
        done.append(answer(b, correct=(k != 1)))
        if k < 2: b.tap_el("[data-act=next]")
    b.tap_el("[data-act=star]")
    b.pump(2.0)                      # 答えてから 2 秒後に…
    b._proc.kill(); b._proc.wait()   # 終了処理なしで強制終了（タスクキル相当）
    try: b._ws.close()
    except Exception: pass

    b2 = Browser()
    with ck.step("タスクキル後"):
        b2.open(URL)                 # seed なし＝保存されていたデータだけで起動
        s = state(b2)
        ck.check("答えた 3 問の記録が残る", all(i in s["ans"] for i in done), list(s["ans"]))
        ck.check("間違えた問題も残る（間違えた問題モードに出る）", s["ans"][done[1]]["last"] == 0)
        ck.check("☆ の印が残る", done[2] in s["marks"])
        ck.check("途中の位置が残り「続きから解く」が出る", "3 / 10 問 回答済み" in text(b2))
        b2.tap_el("[data-act=resume]")
        ck.check("再開すると、答え終わった 3 問目（次へ を押す前）から", "3 / 10" in text(b2) and b2.exists(".judge"))
        b2.screenshot(os.path.join(OUT, "13_after_kill.png"))
        ck.check("JS エラーなし", not b2.errors, b2.errors)
    b2.close()
finally:
    cdp.tempfile.mkdtemp = orig
    shutil.rmtree(prof, ignore_errors=True)

sys.exit(ck.summary())
