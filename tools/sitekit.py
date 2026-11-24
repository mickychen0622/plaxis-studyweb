"""網頁產生器的共用工具：連線、執行 SQL／Python 範例、輸出 HTML 片段。

build_site.py 匯入這個模組；這裡不寫任何頁面內容。
"""
import contextlib
import html
import io
import os
import sqlite3
import textwrap

import numpy as np

DB = None          # data.db 的完整路徑（由 setup() 設定）
con = None         # 唯讀連線
IMG_DIR = None     # 範例程式存圖的資料夾
HEADER = None      # 每段 Python 範例前面共用的開頭程式
TABLE_PAGE = {}    # 表名 → (頁面檔名, 錨點)，用來產生交叉連結
_CUR_ROOT = '../'  # 目前正在產生的頁面相對根目錄的路徑


def setup(db_path, img_dir):
    global DB, con, IMG_DIR, HEADER
    DB = db_path
    IMG_DIR = img_dir
    con = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    HEADER = common_header(db_path)


def common_header(db_path):
    return textwrap.dedent(f'''\
        import sqlite3
        import numpy as np

        DB = r'{db_path}'
        con = sqlite3.connect(f'file:{{DB}}?mode=ro', uri=True)   # 唯讀開啟，不會改到檔案

        # DataInterpretation.ID → numpy 的資料型別（< 代表 little-endian，位元組倒過來存）
        DTYPE = {{1: '<f4', 2: '<f8', 3: '<u1', 4: '<i1', 5: '<u2', 6: '<i2', 7: '<u4', 8: '<i4',
                 9: '<u8', 10: '<i8', 11: '<u1', 12: 'S1', 13: '<u1',
                 14: '<i8', 15: '<i8', 16: '<i8', 17: '<i8', 18: '<i8'}}

        def decode(data, interp_id, size=1):
            """把 BLOB 依 DataInterpretationID 轉成 numpy 陣列；size = ComponentSize（每點幾個分量）"""
            if data is None:
                return None
            a = np.frombuffer(data, DTYPE[interp_id])
            return a.reshape(-1, size) if size > 1 else a

        # DataLayout.ID：結果數值排在哪裡
        NODAL, INTEGRATION_POINT, MESH_ENTITY, ELEMENT, UNIQUE_NODAL = 1, 2, 3, 4, 5

        def last_step(phase_number):
            """施工階段（I_Phase.Number）最後一個計算步的 K_Steps.ID；完整結果只存在這一步"""
            return con.execute("""SELECT k.ID FROM K_Steps k JOIN I_Phase p ON p.ID = k.I_PhaseID
                                  WHERE p.Number = ? AND p.PhaseTypeID = 1
                                  ORDER BY k.Number DESC LIMIT 1""", (phase_number,)).fetchone()[0]

        def get_result(step_id, entity_id, var_name, layout_id):
            """讀一筆 Result 並解碼；這一步沒有存這個量就回傳 None"""
            row = con.execute("""SELECT r.Data, r.DataInterpretationID, r.ComponentSize
                                 FROM Result r JOIN Variables v ON v.ID = r.VariablesID
                                 WHERE r.K_StepsID = ? AND r.MeshEntityID = ? AND v.Name = ?
                                   AND r.DataLayoutID = ?""",
                              (step_id, entity_id, var_name, layout_id)).fetchone()
            return None if row is None else decode(*row)

        def connectivity(entity_id):
            """MeshEntity.ComponentData → 每列一個元素的節點編號（節點編號從 1 起算）"""
            count, data = con.execute('SELECT ComponentCount, ComponentData FROM MeshEntity WHERE ID = ?',
                                      (entity_id,)).fetchone()
            return np.frombuffer(data, '<u8').reshape(count, -1)

        def unique_nodes(conn):
            """Unique Nodal 結果的節點順序 = 節點在連接表裡第一次出現的順序"""
            flat = conn.ravel()
            _, first = np.unique(flat, return_index=True)
            return flat[np.sort(first)]

        def node_xy():
            """全部節點座標 (N, 2)；節點編號 n 的座標是 node_xy()[n - 1]"""
            data = con.execute('SELECT NodeData FROM Mesh').fetchone()[0]
            return np.frombuffer(data, '<f8').reshape(-1, 2)
        ''')


def set_root(root):
    global _CUR_ROOT
    _CUR_ROOT = root


def esc(s):
    return html.escape(str(s), quote=False)


def q(sql, args=()):
    return con.execute(sql, args).fetchall()


def q1(sql, args=()):
    return con.execute(sql, args).fetchone()[0]


def fmt_int(n):
    return f'{n:,}'


# ---------- 交叉連結 ----------
def T(name, label=None):
    """連到某張表的說明段落"""
    page, anchor = TABLE_PAGE[name]
    return f'<a href="{_CUR_ROOT}tables/{page}#{anchor}"><code>{esc(label or name)}</code></a>'


# ---------- 程式碼與結果 ----------
def codeblock(src, lang='python', title=None):
    src = textwrap.dedent(src).strip('\n')
    t = title or {'python': 'Python', 'sql': 'SQL（sqlite3 終端機或 Python 皆可）', 'bash': '終端機',
                  'plx': 'PLAXIS Command'}[lang]
    cls = f'lang-{lang}' if lang in ('python', 'sql', 'plx') else ''
    return (f'<div class="codeblock"><div class="cb-h"><span class="t">{esc(t)}</span>'
            f'<button class="cb-copy" type="button">複製</button></div>'
            f'<pre><code class="{cls}">{esc(src)}</code></pre></div>')


def outblock(text, title='執行結果'):
    text = text.rstrip('\n')
    return (f'<div class="codeblock out"><div class="cb-h"><span class="t">{esc(title)}</span></div>'
            f'<pre><code>{esc(text)}</code></pre></div>')


def run_py(src, max_lines=40, ns=None):
    """在共用開頭之後執行範例程式，回傳它印出的文字（失敗就讓整個產生器停下來）

    ns：給一個 dict 就在同一個命名空間連續執行（後面的範例可以用前面定義的函式與變數）。
    """
    import sys
    files_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files'))
    if files_dir not in sys.path:
        sys.path.insert(0, files_dir)          # 範例裡 import fig_style 用
    src = textwrap.dedent(src).strip('\n')
    buf = io.StringIO()
    old = os.getcwd()
    os.chdir(IMG_DIR)
    try:
        with contextlib.redirect_stdout(buf):
            if ns is None:
                exec(compile(HEADER + '\n' + src, '<example>', 'exec'), {'__name__': '__example__'})
            else:
                if not ns:
                    ns['__name__'] = '__example__'
                    exec(compile(HEADER, '<header>', 'exec'), ns)
                exec(compile(src, '<example>', 'exec'), ns)
    finally:
        os.chdir(old)
    lines = buf.getvalue().rstrip('\n').split('\n')
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f'…（共 {len(lines)} 行，只列前 {max_lines} 行）']
    return '\n'.join(lines)


def py(src, max_lines=40, show_out=True, ns=None):
    """顯示 Python 範例＋實際執行結果"""
    out = run_py(src, max_lines, ns)
    return codeblock(src, 'python') + (outblock(out) if show_out and out.strip() else '')


def cell(v):
    if isinstance(v, (bytes, bytearray)):
        h = v[:12].hex()
        return f'<td class="blob">x\'{h}{"…" if len(v) > 12 else ""}\'<br><small>{len(v):,} bytes</small></td>'
    if v is None:
        return '<td class="blob">NULL</td>'
    if isinstance(v, float):
        return f'<td class="num">{v:.6g}</td>'
    if isinstance(v, int):
        return f'<td class="num">{v}</td>'
    return f'<td>{esc(v)}</td>'


def result_table(sql, args=(), cls='sample', table_id=None):
    cur = con.execute(sql, args)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    tid = f' id="{table_id}"' if table_id else ''
    h = ''.join(f'<th>{esc(c)}</th>' for c in cols)
    body = ''.join('<tr>' + ''.join(cell(v) for v in r) + '</tr>' for r in rows)
    return f'<table class="data {cls}"{tid}><tr>{h}</tr>{body}</table>', len(rows)


def sql(src, show_out=True, title='查詢結果'):
    """顯示 SQL＋查詢結果表"""
    src = textwrap.dedent(src).strip('\n')
    tbl, n = result_table(src)
    out = (f'<div class="subhead">{esc(title)}（{n} 列）</div><div class="tablewrap">{tbl}</div>') if show_out else ''
    return codeblock(src, 'sql') + out


def sample(table, limit=8, order='ID', where=''):
    w = f' WHERE {where}' if where else ''
    o = f' ORDER BY {order}' if order else ''
    tbl, n = result_table(f'SELECT * FROM "{table}"{w}{o} LIMIT {limit}')
    return f'<div class="tablewrap">{tbl}</div>'


def full_list(table_id, sqltext, filter_hint='輸入關鍵字篩選，例如 Stress'):
    tbl, n = result_table(sqltext, table_id=table_id)
    return (f'<input class="filterbox" type="search" data-target="{table_id}" placeholder="{esc(filter_hint)}">'
            f' <small style="color:var(--muted)">顯示 <b id="{table_id}-n">{n}</b> / {n} 列</small>'
            f'<div class="scrolltbl">{tbl}</div>')


def columns(table, desc, fks=None, blobs=()):
    """欄位表：PRAGMA table_info ＋ 說明"""
    fks = fks or {}
    rows = []
    for cid, name, typ, notnull, dflt, pk in q(f'PRAGMA table_info("{table}")'):
        tags = ''
        if pk:
            tags += '<span class="pk">PK</span>'
        if name in fks:
            tags += '<span class="fk">FK</span>'
        if typ == 'BLOB':
            tags += '<span class="bl">BLOB</span>'
        d = desc.get(name, '')
        if name in fks:
            d = (d + ' ' if d else '') + '→ ' + ' / '.join(T(t) for t in fks[name])
        rows.append(f'<tr><td>{esc(name)}{tags}</td><td>{esc(typ)}{" NOT NULL" if notnull else ""}</td><td>{d}</td></tr>')
    return ('<div class="tablewrap"><table class="data cols"><tr><th>欄位</th><th>型別</th><th>意思</th></tr>'
            + ''.join(rows) + '</table></div>')


def callout(kind, title, body):
    return f'<div class="callout {kind}"><div class="ct">{esc(title)}</div>{body}</div>'


def quiz(question, options, answer, feedback):
    opts = ''.join(f'<button class="opt">{o}</button>' for o in options)
    return (f'<div class="quiz" data-answer="{answer}"><div class="qh">小測驗</div><div class="qq">{question}</div>'
            f'<div class="opts">{opts}</div><div class="fb">{feedback}</div></div>')


def figure(fname, caption):
    return f'<figure class="shot"><img src="{_CUR_ROOT}assets/img/{fname}" alt="{esc(caption)}" loading="lazy"><figcaption>{esc(caption)}</figcaption></figure>'


def meta(table):
    n = q1(f'SELECT COUNT(*) FROM "{table}"')
    ncol = len(q(f'PRAGMA table_info("{table}")'))
    return n, f'<div class="meta"><span>筆數 <b>{fmt_int(n)}</b></span><span>欄位 <b>{ncol}</b></span></div>'


def table_section(num, table, short_desc, body):
    """一張表 = 一個 section；側欄會自動列出"""
    anchor = TABLE_PAGE[table][1]
    _, m = meta(table)
    return (f'<section class="sec" id="{anchor}" data-num="{num}" data-short="{esc(table)}" data-title="{esc(table)}">'
            f'<div class="sec-head"><span class="sec-num">{num}</span><h2>{esc(table)}</h2></div>'
            f'<p class="src">{short_desc}</p>{m}{body}</section>')


# ---------- 頁面外框 ----------
def page(path, *, page_id, root, title, short_title, hero, sections, pager, extra_style=''):
    doc = f'''<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{root}assets/style.css">
<style>{extra_style}</style>
</head>
<body data-page="{page_id}" data-root="{root}" data-title="{esc(short_title)}">

<main>
{hero}
{''.join(sections)}
</main>
<div class="pager-wrap"><nav class="pager">{pager}</nav></div>
<footer class="site">Plaxis2D Simulation · 第 3–4 章範例資料：e5_TC289_NearMesh.p2dxdat · 個人學習筆記</footer>

<script src="{root}assets/common.js"></script>
</body>
</html>
'''
    with open(path, 'w', encoding='utf-8') as f:
        f.write(doc)
