"""ap-kakomon の動作テスト（iPhone サイズのヘッドレス Edge）
実行: "/c/Users/skyio/anaconda3/python.exe" tests/test_app.py
"""
import json, os, sys, glob
sys.path.insert(0, os.path.expanduser("~/.claude/skills/webapp-test/scripts"))
from cdp import Browser, Checker, serve

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
URL = serve(ROOT)
KEY = "ap-kakomon_v1"
OUT = os.path.join(os.environ.get("TEMP", "."), "ap-kakomon-shots")
os.makedirs(OUT, exist_ok=True)

exams = json.load(open(os.path.join(ROOT, "data", "exams.json"), encoding="utf-8"))
DATA = [json.load(open(os.path.join(ROOT, "data", f"{e}.json"), encoding="utf-8")) for e in exams]
ALL = [q for d in DATA for q in d["qs"]]
IDS = [q["id"] for q in ALL]
BYID = {q["id"]: q for q in ALL}

def blank(**kw):
    d = {"version": 1, "ans": {}, "marks": {}, "history": [], "settings": {"count": 20, "genres": []}, "cur": None}
    d.update(kw); return d

def state(b): return b.js(f"JSON.parse(localStorage.getItem('{KEY}'))")
def text(b): return b.js("document.body.innerText")

ck = Checker()

# ---------- データ自体の検査 ----------
with ck.step("データ"):
    ck.check("問題データが 1 回分以上ある", len(DATA) >= 1, exams)
    ck.check("各回 80 問", all(len(d["qs"]) == 80 for d in DATA))
    ck.check("ID が重複しない", len(set(IDS)) == len(IDS))
    ok = all(len(q["c"]) == 4 and all(c.strip() for c in q["c"]) and q["q"].strip() and q["x"].strip() and 0 <= q["ans"] <= 3 and 0 <= q["g"] <= 22 for q in ALL)
    ck.check("全問に問題文・選択肢4つ・正解・分野・解説がある", ok)
    missing = [f["src"] for q in ALL for f in q["f"] if not os.path.exists(os.path.join(ROOT, f["src"]))]
    ck.check("図の画像ファイルがすべて存在する", not missing, missing[:5])
    sw = open(os.path.join(ROOT, "sw.js"), encoding="utf-8").read()
    ck.check("オフライン用キャッシュ一覧に全データ・全図が入っている", all(f"data/{e}.json" in sw for e in exams) and all(f["src"] in sw for q in ALL for f in q["f"]))

with Browser() as b:
    # ---------- 起動 ----------
    with ck.step("起動"):
        b.open(URL, seed={KEY: blank()})
        b.pump(0.5)
        ck.check("出題画面が表示される", b.exists("[data-act=start]"))
        ck.check(f"収録数 {len(ALL)} 問と表示", f"収録 {len(ALL)} 問" in text(b))
        ck.check("間違えた問題・見直しは 0 問なので押せない", b.js("document.querySelector('[data-mode=wrong]').disabled && document.querySelector('[data-mode=marks]').disabled"))
        b.screenshot(os.path.join(OUT, "01_home.png"))

    # ---------- ランダム出題の配分 ----------
    with ck.step("ランダム配分"):
        res = b.js("""(()=>{ S.settings.count = 40; const r = []; for(let k=0;k<30;k++){ const s = buildSet('random'); r.push(s.map(q=>q.g)); } S.settings.count = 20; return r; })()""")
        ck.check("40 問ちょうど出る", all(len(r) == 40 for r in res))
        W = [0] * 23
        for q in ALL: W[q["g"]] += 1
        tot = sum(W)
        worst = 0
        for r in res:
            for g in range(23):
                exp = 40 * W[g] / tot
                worst = max(worst, abs(r.count(g) - exp))
        ck.check("各分野の出題数が出題割合どおり（誤差 1 問未満）", worst < 1.0001, f"最大誤差 {worst:.2f}")
        uniq = b.js("(()=>{ const s = buildSet('random'); return new Set(s.map(q=>q.id)).size; })()")
        ck.check("同じ問題が重複しない", uniq == 20)

    with ck.step("優先順位"):
        # 全問正解済み（古い順に時刻）にして、一部だけ未回答・不正解にする
        ans = {}
        for i, qid in enumerate(IDS): ans[qid] = {"n": 1, "c": 1, "last": 1, "t": 1000 + i}
        g0 = [q["id"] for q in ALL if q["g"] == 10]  # セキュリティ
        unans = g0[:2]; wrong = g0[2:4]
        for qid in unans: del ans[qid]
        for qid in wrong: ans[qid] = {"n": 1, "c": 0, "last": 0, "t": 99999999}
        b.js(f"S = {json.dumps(blank(ans=ans), ensure_ascii=False)}; save(); render();")
        picked = b.js("(()=>{ S.settings.genres=[10]; S.settings.count=10; const s = buildSet('genre').map(q=>q.id); S.settings.count=20; S.settings.genres=[]; return s; })()")
        ck.check("分野指定でその分野の問題だけ出る", all(BYID[i]["g"] == 10 for i in picked), picked)
        ck.check("未回答の問題が必ず選ばれる", all(u in picked for u in unans))
        ck.check("前回不正解の問題が必ず選ばれる", all(w in picked for w in wrong))
        sec_ok = sorted([q["id"] for q in ALL if q["g"] == 10 and q["id"] not in unans + wrong], key=lambda i: ans[i]["t"])
        rest = [i for i in picked if i not in unans + wrong]
        ck.check("正解済みは前に解いたのが古い順に選ばれる", set(rest) == set(sec_ok[:len(rest)]))
        b.js(f"S = {json.dumps(blank(), ensure_ascii=False)}; save(); render();")

    # ---------- 解く ----------
    with ck.step("解答の流れ"):
        b.tap_el("[data-count='10']")
        b.tap_el("[data-act=start]")
        ck.check("問題画面に切り替わり、下のタブが隠れる", b.exists("#choices") and not b.js("getComputedStyle(document.querySelector('nav.tabs')).display !== 'none'"))
        ck.check("1 / 10 と表示", "1 / 10" in text(b))
        cur = state(b)["cur"]
        q = BYID[cur["ids"][0]]
        wrong_i = (q["ans"] + 1) % 4
        b.tap_el(f"[data-pick='{wrong_i}']")
        ck.check("間違えると不正解と正解が表示される", "不正解" in text(b) and f"正解は {'アイウエ'[q['ans']]}" in text(b))
        ck.check("選んだ選択肢が赤、正解が緑", b.js(f"document.querySelector('[data-pick=\"{wrong_i}\"]').classList.contains('ng') && document.querySelector('[data-pick=\"{q['ans']}\"]').classList.contains('ok')"))
        s = state(b)
        ck.check("回答が保存される（不正解）", s["ans"][q["id"]]["last"] == 0 and s["ans"][q["id"]]["n"] == 1)
        b.tap_el(f"[data-pick='{q['ans']}']")
        ck.check("回答後に別の選択肢を押しても変わらない", state(b)["ans"][q["id"]]["n"] == 1)
        ck.check("解説は最初は閉じている", not b.js("document.getElementById('expl').classList.contains('open')"))
        b.tap_el("[data-act=expl]")
        ck.check("解説を見るで解説が開く", b.js("document.getElementById('expl').classList.contains('open')") and q["x"][:10].replace("，", "、") in text(b))
        href = b.js("document.querySelector('a[href*=\"ap-siken\"]').href")
        ck.check("過去問道場へのリンクが正しい", href == f"https://www.ap-siken.com/kakomon/{[d for d in DATA if d['exam']==q['id'].split('-')[0]][0]['slug']}/q{q['n']}.html", href)
        b.screenshot(os.path.join(OUT, "02_answered.png"), full=True)
        b.tap_el("[data-act=star]")
        ck.check("☆ で見直しに追加される", q["id"] in state(b)["marks"])
        b.tap_el("[data-act=next]")
        ck.check("次の問題へ進む", "2 / 10" in text(b))
        ck.check("次の問題は画面の一番上から表示", b.js("scrollY") == 0)

    with ck.step("中断と再開"):
        b.reload()
        ck.check("再読み込み後、問題画面のまま続きが出る… または再開ボタン", b.exists("[data-act=resume]") or b.exists("#choices"))
        if b.exists("[data-act=resume]"):
            ck.check("「続きから解く」に 1 / 10 問 回答済み と表示", "1 / 10 問 回答済み" in text(b))
            b.tap_el("[data-act=resume]")
        ck.check("再開すると 2 問目から", "2 / 10" in text(b))
        # 残りを全部正解で解く
        for k in range(9):
            cur = state(b)["cur"]
            q2 = BYID[cur["ids"][cur["i"]]]
            b.tap_el(f"[data-pick='{q2['ans']}']")
            b.tap_el("[data-act=next]")
        ck.check("最後に結果画面が出る", "正答率 90%" in text(b) and "9" in text(b))
        s = state(b)
        ck.check("履歴に 1 件記録される", len(s["history"]) == 1 and s["history"][0]["total"] == 10 and s["history"][0]["correct"] == 9)
        b.screenshot(os.path.join(OUT, "03_result.png"), full=True)
        ck.check("間違えた問題だけもう一度 のボタンがある", b.exists("[data-act=retry]"))
        b.tap_el("[data-act=retry]")
        ck.check("解き直しは 1 問で、さっき間違えた問題", "1 / 1" in text(b) and state(b)["cur"]["ids"] == [q["id"]])
        b.tap_el(f"[data-pick='{q['ans']}']")
        ck.check("正解すると「間違えた問題」から外れる", b.js(f"wrongList().length") == 0)
        b.tap_el("[data-act=next]")
        b.tap_el("[data-act=close]")
        ck.check("結果を閉じると出題画面に戻り、タブが表示される", b.exists("[data-act=start]") and b.js("getComputedStyle(document.querySelector('nav.tabs')).display") != "none")

    with ck.step("間違えた問題モード"):
        ids = IDS[:3]
        ans = {i: {"n": 1, "c": 0, "last": 0, "t": 1} for i in ids}
        ans[IDS[3]] = {"n": 2, "c": 1, "last": 1, "t": 2}
        b.js(f"S = {json.dumps(blank(ans=ans), ensure_ascii=False)}; save(); ui.mode='random'; render();")
        ck.check("前回不正解の数が表示される", "前回まちがえた問題 3 問" in text(b))
        b.tap_el("[data-mode=wrong]")
        b.tap_el("[data-act=start]")
        ck.check("前回不正解の 3 問だけ出題", sorted(state(b)["cur"]["ids"]) == sorted(ids))
        b.tap_el("[data-act=quit]")
        ck.check("未回答で閉じると確認なしで出題画面に戻る", b.exists("[data-act=start]"))

    with ck.step("分野選択シート"):
        b.js(f"S = {json.dumps(blank(), ensure_ascii=False)}; save(); ui.mode='random'; render();")
        b.tap_el("[data-mode=genre]")
        ck.check("分野未選択なら選択シートが自動で開く", b.exists("#sheet"))
        ck.check("シート表示中は背面が固定される", b.js("document.body.style.position") == "fixed")
        b.tap_el("[data-big=M]")
        ck.check("「すべて選ぶ」でマネジメント系が選ばれる", b.js("document.querySelectorAll('.gitem.on').length") == len({q['g'] for q in ALL if 13 <= q['g'] <= 15}))
        b.screenshot(os.path.join(OUT, "04_sheet.png"))
        b.tap_el("[data-act=gdone]")
        ck.check("決定でシートが閉じ、背面の固定が解除", not b.exists("#sheet") and b.js("document.body.style.position") == "")
        ck.check("選んだ分野がチップで表示される", "プロジェクトマネジメント" in text(b))
        b.tap_el("[data-act=start]")
        cur = state(b)["cur"]
        ck.check("マネジメント系だけが出題される", all(13 <= BYID[i]["g"] <= 15 for i in cur["ids"]) and len(cur["ids"]) == 20)
        b.tap_el("[data-act=quit]")
        # 背景タップで閉じる
        b.tap_el("[data-act=pickgenre]")
        b.pump(0.5)
        b.tap(195, 40)
        ck.check("シートの外側をタップすると閉じる", not b.exists("#sheet"))

    with ck.step("図"):
        fq = next((q for q in ALL if q["f"]), None)
        if fq:
            b.js(f"startQuiz(['{fq['id']}'], 'single')")
            b.pump(0.6)
            ck.check("図が表示され、読み込めている", b.js("[...document.querySelectorAll('.fig img')].every(i => i.complete && i.naturalWidth > 0)"))
            b.screenshot(os.path.join(OUT, "05_figure.png"), full=True)
            b.tap_el("[data-fig='0']")
            ck.check("図をタップすると拡大表示", b.exists("#viewer"))
            b.tap_el("#viewer .close")
            ck.check("拡大表示を閉じられる", not b.exists("#viewer") and b.js("document.body.style.position") == "")
            b.tap_el("[data-act=quit]")

    with ck.step("記録・見直し・設定"):
        ans = {IDS[0]: {"n": 2, "c": 1, "last": 1, "t": 5}, IDS[1]: {"n": 1, "c": 0, "last": 0, "t": 6}}
        hist = [{"t": 1700000000000, "mode": "random", "total": 20, "correct": 15}]
        b.js(f"S = {json.dumps(blank(ans=ans, history=hist, marks={IDS[5]: 1}), ensure_ascii=False)}; save(); render();")
        b.tap_el("[data-tab=stats]")
        t = text(b)
        ck.check("記録：解いた問題数と正答率", "33%" in t and "解いた問題" in t)
        ck.check("記録：分野ごとの正答率が出る", "テクノロジ系" in t and "ストラテジ系" in t)
        ck.check("記録：履歴が出る", "15/20 問" in t and "75%" in t)
        b.screenshot(os.path.join(OUT, "06_stats.png"), full=True)
        b.tap_el("[data-tab=marks]")
        ck.check("見直し：印を付けた問題が一覧に出る", b.js("document.querySelectorAll('.qitem').length") == 1)
        b.tap_el(f"[data-open='{IDS[5]}']")
        ck.check("見直し：タップでその問題を解ける", state(b)["cur"]["ids"] == [IDS[5]] and b.exists("#choices"))
        b.tap_el("[data-act=quit]")
        b.tap_el("[data-tab=marks]")
        b.tap_el(f"[data-unstar='{IDS[5]}']")
        ck.check("見直し：★で一覧から外せる", IDS[5] not in state(b)["marks"] and "まだありません" in text(b))
        b.tap_el("[data-tab=settings]")
        ck.check("設定：出典の表示がある", "情報処理推進機構" in text(b))
        b.screenshot(os.path.join(OUT, "07_settings.png"), full=True)

    with ck.step("バックアップ"):
        backup = blank(ans={IDS[7]: {"n": 3, "c": 3, "last": 1, "t": 9}}, marks={IDS[8]: 1})
        b.js("window.confirm = () => true")
        b.js(f"doImport(new File([{json.dumps(json.dumps(backup))}], 'b.json', {{type:'application/json'}}))")
        b.pump(0.6)
        s = state(b)
        ck.check("読み込みで記録が置き換わる", IDS[7] in s["ans"] and IDS[0] not in s["ans"] and IDS[8] in s["marks"])
        b.js("doImport(new File(['{\"foo\":1}'], 'x.json'))"); b.pump(0.5)
        ck.check("関係ないファイルは読み込まない", IDS[7] in state(b)["ans"])
        exported = b.js("JSON.stringify(S)")
        ck.check("書き出し内容は読み込める形式", b.js(f"valid({exported})"))
        b.js("window.confirm = () => true")
        b.tap_el("[data-act=reset]")
        ck.check("リセットで記録が消える", state(b)["ans"] == {})

    with ck.step("保存データ"):
        b.js(f"localStorage.setItem('{KEY}', '{{壊れたデータ')"); b.reload()
        ck.check("壊れた保存データでも起動する", b.exists("[data-act=start]"))
        b.js(f"localStorage.setItem('{KEY}', JSON.stringify({{version:1, ans:{{}}, marks:{{}}, history:[]}}))"); b.reload()
        ck.check("settings の無い古い形式でも起動する", b.exists("[data-act=start]") and "20 問" in text(b))

    with ck.step("スクロール"):
        b.js(f"startQuiz({json.dumps(IDS[:1])}, 'single')")
        long_q = max(ALL, key=lambda q: len(q["q"]) + sum(len(c) for c in q["c"]))
        b.js(f"S.cur.ids=['{long_q['id']}']; renderQuiz();")
        h = b.js("document.documentElement.scrollHeight")
        b.swipe(200, 700, 200, 200)
        ck.check("長い問題を指でスクロールできる", h <= 844 or b.js("scrollY") > 50, f"h={h} y={b.js('scrollY')}")
        b.tap_el("[data-act=quit]")

    with ck.step("記号の表示"):
        ov = next((q for q in ALL if "̅" in q["q"] + "".join(q["c"])), None)
        if ov:
            b.js(f"startQuiz(['{ov['id']}'], 'single')"); b.pump(0.3)
            ck.check("否定の上線が CSS の上線で表示される", b.js("document.querySelectorAll('#quiz .ov').length > 0 && !document.getElementById('quiz').innerText.includes('\\u0305')"))
            b.tap_el("[data-act=quit]")
        sb = next((q for q in ALL if "_A" in q["q"]), None)
        if sb:
            b.js(f"startQuiz(['{sb['id']}'], 'single')"); b.pump(0.3)
            ck.check("α_A のような下付き文字が小さく表示される", b.js("document.querySelectorAll('#qtext sub').length > 0 && !document.getElementById('qtext').innerText.includes('_A')"))
            b.tap_el("[data-act=quit]")

    with ck.step("オフライン"):
        b.pump(1.5)
        ready = b.js("navigator.serviceWorker && navigator.serviceWorker.controller ? 1 : 0")
        if not ready:
            b.reload(); b.pump(1.5)
        ck.check("Service Worker が有効になる", b.js("navigator.serviceWorker.controller ? 1 : 0") == 1)
        b.cmd("Network.enable")
        b.cmd("Network.emulateNetworkConditions", offline=True, latency=0, downloadThroughput=-1, uploadThroughput=-1)
        b.reload(); b.pump(1.0)
        ck.check("電波なしでも起動して全問読み込める", f"収録 {len(ALL)} 問" in text(b))
        fq = next(q for q in ALL if q["f"])
        b.js(f"startQuiz(['{fq['id']}'], 'single')"); b.pump(0.8)
        ck.check("電波なしでも図が表示される", b.js("[...document.querySelectorAll('.fig img')].every(i => i.complete && i.naturalWidth > 0)"))
        b.tap_el("[data-act=quit]")
        b.cmd("Network.emulateNetworkConditions", offline=False, latency=0, downloadThroughput=-1, uploadThroughput=-1)

    ck.check("JS エラーなし", not b.errors, b.errors)

print("shots:", OUT)
sys.exit(ck.summary())
