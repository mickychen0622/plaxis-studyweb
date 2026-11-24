"""第 3 章（Data Structures 總覽頁）與第 4 章（Post-Processing）的頁面內容。

build_site.py 匯入這個模組；各表的分頁在 pages_a.py、pages_b.py。
"""
import os

import sitekit as K

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIRCLED = '①②③④⑤⑥⑦'


# =====================================================================
# 第 3 章：Data Structures
# =====================================================================
def relation_svg():
    """Result 怎麼靠編號串到其他表的示意圖（顏色走 CSS 變數，深淺色都可讀）"""
    def box(x, y, w, title, sub, cls='f-surface', href=None):
        t = (f'<rect x="{x}" y="{y}" width="{w}" height="54" rx="12" class="{cls}" style="stroke:var(--line)"/>'
             f'<text x="{x + w / 2}" y="{y + 23}" text-anchor="middle" class="txt" style="font-weight:600;font-family:var(--font-mono)">{title}</text>'
             f'<text x="{x + w / 2}" y="{y + 42}" text-anchor="middle" class="txt-muted">{sub}</text>')
        return f'<a href="{href}">{t}</a>' if href else t

    def arrow(x1, y1, x2, y2, label=''):
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        lab = f'<text x="{mx + 6}" y="{my - 6}" class="txt-muted" style="font-family:var(--font-mono);font-size:11.5px">{label}</text>' if label else ''
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" style="stroke:var(--gray)" stroke-width="1.5" marker-end="url(#ah)"/>{lab}'

    L = lambda t: f'tables/{K.TABLE_PAGE[t][0]}#{K.TABLE_PAGE[t][1]}'
    s = ['<svg viewBox="0 0 860 400" width="860" role="img" aria-label="Result 與其他表的關聯">',
         '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
         '<path d="M0,0 L10,5 L0,10 z" style="fill:var(--gray)"/></marker></defs>',
         box(330, 20, 200, 'Result', '一包結果數字（BLOB）', 'f-surface', L('Result')),
         box(20, 150, 180, 'K_Steps', '第幾個計算步', href=L('K_Steps')),
         box(20, 290, 180, 'I_Phase', '哪個施工階段', href=L('I_Phase')),
         box(230, 150, 180, 'Variables', '哪一種量', href=L('Variables')),
         box(440, 150, 180, 'MeshEntity', '網格的哪一塊', href=L('MeshEntity')),
         box(440, 290, 180, 'Mesh', '節點座標', href=L('Mesh')),
         box(650, 150, 190, 'DataLayout', '排在節點／積分點', href=L('DataLayout')),
         box(650, 290, 190, 'DataInterpretation', 'Double、Float…', href=L('DataInterpretation')),
         box(230, 290, 180, 'StagedUserFeature', '岩體區塊、邊界', href=L('StagedUserFeature')),
         arrow(370, 74, 110, 148, 'K_StepsID'),
         arrow(110, 204, 110, 288, 'I_PhaseID'),
         arrow(410, 74, 320, 148, 'VariablesID'),
         arrow(450, 74, 530, 148, 'MeshEntityID'),
         arrow(530, 204, 530, 288, '節點編號'),
         arrow(490, 74, 745, 148, 'DataLayoutID'),
         arrow(800, 204, 800, 288, ''),
         arrow(320, 288, 440, 190, 'MeshEntityID'),
         '<text x="808" y="252" class="txt-muted" style="font-family:var(--font-mono);font-size:11.5px">DataInterpretationID</text>',
         '</svg>']
    return '<figure class="diagram">' + ''.join(s) + '<figcaption>點方塊可跳到那張表。箭頭旁是欄位名：Result 自己只存編號，要靠這些編號到其他表查出意思。</figcaption></figure>'


def build_ch3(cats, pager):
    K.set_root('')
    n_tables = K.q1("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    n_nodes = K.q1('SELECT NodeCount FROM Mesh')
    n_tri = K.q1('SELECT SUM(ComponentCount) FROM MeshEntity WHERE MeshComponentTypeID=3 AND MeshEntityApplicationID=1')
    n_main = K.q1('SELECT COUNT(*) FROM I_Phase WHERE PhaseTypeID=1')
    n_steps = K.q1('SELECT COUNT(*) FROM K_Steps k JOIN I_Phase p ON p.ID=k.I_PhaseID WHERE p.PhaseTypeID=1')
    n_res = K.q1('SELECT COUNT(*) FROM Result')
    size_gb = os.path.getsize(K.DB) / 1e9

    Q = {
        'c1': '每一步算出來的位移、應力、孔隙水壓，以及整體收斂資訊。資料量最大。',
        'c2': '施工階段清單、每個階段裡的計算步、每個階段的計算設定。',
        'c3': '節點座標、元素連接，以及網格被切成哪些區塊。',
        'c4': '材料清單與材料參數（c、φ…）。',
        'c5': '岩體區塊與邊界條件；哪個區塊在哪個階段被挖除。',
        'c6': '版本、專案 ID、重力與單位等整體設定。',
        'c7': '「編號 → 名稱」的字典，用來翻譯其他表裡的 ID。',
    }
    cards = []
    for n, (cid, name, tables) in enumerate(cats):
        counts = [K.q1(f'SELECT COUNT(*) FROM "{t}"') for t in tables]
        chips = ''.join(f'<code>{t}</code>' for t in tables)
        cards.append(f'<a class="cat" href="tables/{cid}.html"><div class="no">分類 {CIRCLED[n]} · {len(tables)} 張表 · {K.fmt_int(sum(counts))} 筆</div>'
                     f'<div class="t">{name}</div><p class="q">{Q[cid]}</p><div class="tb">{chips}</div></a>')

    stats = ''.join(f'<div class="stat"><div class="k">{k}</div><div class="v">{v}</div></div>' for k, v in [
        ('檔案大小', f'{size_gb:.2f} GB'), ('資料表', n_tables), ('節點', K.fmt_int(n_nodes)),
        ('15 節點三角形元素', K.fmt_int(n_tri)), ('施工階段（Main）', n_main), ('計算步', K.fmt_int(n_steps)),
        ('Result 筆數', K.fmt_int(n_res))])

    hero = f'''<header class="hero" id="top">
  <div class="eyebrow">Chapter 3</div>
  <h1>Data Structures</h1>
  <p class="lede"><b>PLAXIS 2D 把整個模型和全部計算結果存成一個 SQLite 資料庫 data.db。</b>這一章以 <code>e5_TC289_NearMesh.p2dxdat/data.db</code> 為例，把 {n_tables} 張表分成七類，逐表說明每個欄位的意思，並附上實際能跑的 SQL 查詢與 Python 程式。</p>
  <div class="stats-row">{stats}</div>
  <a class="btn primary" href="tables/c1.html" style="font-size:17px;padding:11px 24px;margin-top:34px;display:inline-block">從 ① 計算結果開始</a>
  <a class="btn" href="ch4_postprocessing.html" style="font-size:17px;padding:11px 24px;margin:34px 0 0 8px;display:inline-block">直接用 Python 讀取（第 4 章）</a>
</header>'''

    sec_files = f'''<section class="sec" id="files" data-num="3.1" data-short="專案資料夾裡的檔案">
  <div class="sec-head"><span class="sec-num">3.1</span><h2>專案資料夾裡的檔案</h2></div>
  <p>存檔後，一個 PLAXIS 專案是 <code>xxx.p2dx</code> 加上同名的 <code>xxx.p2dxdat</code> 資料夾。.p2dx 只是入口，所有東西都在資料夾裡，而且大多是文字檔或 SQLite，可以直接讀。</p>
  <div class="tablewrap"><table class="data">
    <tr><th>檔案</th><th>寫入時機</th><th>內容</th></tr>
    <tr><td><code>xxx.p2dx</code>、<code>data.p2dx</code></td><td>存檔</td><td>純文字的指令紀錄（含 GUI 操作留下的 <code>_set …</code>），可以整理回第 2 章的 Command txt</td></tr>
    <tr><td><code>data.plxml</code></td><td>存檔</td><td>Input 的模型狀態（二進位 XML）：幾何、材料、相位設定</td></tr>
    <tr><td><code>data.opi</code></td><td>存檔</td><td>INI 文字：各相名稱、前一相、計算狀態、起訖步號</td></tr>
    <tr><td><b><code>data.db</code></b></td><td>存檔</td><td><b>SQLite：網格、物件、相位設定與全部計算結果</b>（這一章的主角）</td></tr>
    <tr><td><code>data.meshinput／meshoutput／meshinfo</code></td><td>產生網格</td><td>網格的輸入、節點與元素、網格紀錄（失敗原因寫在 meshinfo）</td></tr>
    <tr><td><code>data.eNN、mNN、mxNN</code></td><td>每相開始</td><td>交給計算核心的模型與材料輸入</td></tr>
    <tr><td><code>log.dNN</code></td><td>每相結束</td><td>結果碼 ErrorCode、錯誤訊息、步數</td></tr>
    <tr><td><code>data.convd.rrNN</code></td><td>每相結束</td><td>收斂紀錄：每步每次迭代的 Global error、塑性／張力點數、最大不平衡力位置</td></tr>
    <tr><td><code>debug.dNN</code></td><td>每相結束</td><td>計算核心紀錄：材料參數、每步 ΣMstage、CSP、計時</td></tr>
    <tr><td><code>data.cxx.rrNN</code></td><td>每相結束</td><td>Curve points（第 2 章選的量測點）逐步資料</td></tr>
  </table></div>
  <h3>data.db 什麼時候才有結果</h3>
  <ol class="steps">
    <li><b>建模存檔</b>：data.db 幾乎是空的，只有網格、物件與相位設定（plan_e 約 24 MB）。</li>
    <li><b>計算中</b>：每相的結果先寫進暫存資料庫（<code>{{GUID}}.db</code>）。</li>
    <li><b>計算後存檔</b>：暫存結果才寫回 data.db，檔案增為 1–3 GB。</li>
  </ol>
  {K.callout('pitfall', '讀取前先確認兩件事', '<p>① <b>計算完要存檔</b>，否則結果不在 data.db。② PLAXIS 開著這個專案時，先把 data.db <b>複製一份</b>再讀；讀取一律用唯讀模式（第 4 章）。</p>')}
  {K.callout('example', '用文字紀錄找問題', '<p>相位失敗時，先看 <code>log.dNN</code> 的 ErrorCode，再看 <code>data.convd.rrNN</code> 後段每步的張力點數與最大不平衡力節點，最後到 data.db 讀那一相最後幾步的位移場，就能定位發散的位置。錯誤碼的意義見第 1 章。</p>')}
</section>'''

    sec_cats = f'''<section class="sec" id="cats" data-num="3.2" data-short="七大分類">
  <div class="sec-head"><span class="sec-num">3.2</span><h2>data.db 的七大分類</h2></div>
  <p>{n_tables} 張表依用途分成七類。每一類一頁，頁內每張表一節：用途、欄位、實際資料、SQL 查詢、Python 程式。</p>
  <div class="cat-grid">{''.join(cards)}</div>
</section>'''

    sec_rel = f'''<section class="sec" id="relation" data-num="3.3" data-short="表怎麼串在一起">
  <div class="sec-head"><span class="sec-num">3.3</span><h2>表怎麼串在一起</h2></div>
  <p>資料庫的核心是 {K.T('Result')}。它的每一列只存「編號＋一包數字」，編號的意思都要去其他表查。讀懂這張圖，就讀懂了大半個資料庫。</p>
  {relation_svg()}
  <p>以「L05 結束時，某個岩體區塊的位移」為例，要依序找出四個編號：</p>
  <ol>
    <li><b>哪一步</b>：在 {K.T('I_Phase')} 找到 L05 的 ID，再到 {K.T('K_Steps')} 找它的最後一步。完整結果只存在每個階段的最後一步。</li>
    <li><b>哪一塊網格</b>：在 {K.T('MeshEntity')} 找到那個岩體區塊（也可以從 {K.T('StagedUserFeature')} 的名稱找）。</li>
    <li><b>哪一種量</b>：在 {K.T('Variables')} 找 <code>Displacement</code>。</li>
    <li><b>排在哪裡</b>：位移排在節點上，所以 {K.T('DataLayout')} 選 <code>Unique Nodal</code>。</li>
  </ol>
  <p>四個編號都有了，就能從 Result 取出 Data，再依 {K.T('DataInterpretation')} 把二進位轉成數字。</p>
  <div class="tablewrap"><table class="data">
    <tr><th>主要結果（Variables.Name）</th><th>DataLayout</th><th>BLOB 內容</th></tr>
    <tr><td>Displacement</td><td>5 Unique Nodal</td><td>float64 (ux, uy)／節點；順序＝連接表中第一次出現的順序</td></tr>
    <tr><td>Effective Stress</td><td>2 Integration Point</td><td>float64 × 4 × 12／三角形：σ′xx、σ′yy、σ′zz、σxy（kPa，壓為負）</td></tr>
    <tr><td>Plastic Point Information、Plastic MC History</td><td>2 Integration Point</td><td>int32 × 12／三角形；整塊都相同時只存 1 個值</td></tr>
    <tr><td>Plate／Embedded beam 內力</td><td>1 Nodal</td><td>float64：N、Q、M</td></tr>
    <tr><td>GlobalResult（另一張表）</td><td>—</td><td>每一步的整體量：SumMStage、CSP、Global Residual Error、塑性點數…</td></tr>
  </table></div>
</section>'''

    sec_key = f'''<section class="sec" id="keys" data-num="3.4" data-short="先記住四件事">
  <div class="sec-head"><span class="sec-num">3.4</span><h2>先記住四件事</h2></div>
  <ul class="pitfalls">
    <li><b>BLOB 不是亂碼</b>查詢工具顯示的 <code>x'cdcc…'</code> 是二進位數字的十六進位寫法。每 8 bytes 是一個 Double，位元組倒過來存（little-endian）。用 Python 的 numpy 一行就能還原。</li>
    <li><b>節點編號從 1 開始</b>連接表與節點群裡的節點編號是 1～{K.fmt_int(n_nodes)}，Python 陣列從 0 開始，所以節點 n 的座標在 <code>xy[n - 1]</code>。</li>
    <li><b>只有最後一步有完整結果</b>這個模型設定每個階段只保存 1 步。中間的計算步只存曲線點附近的小區塊（auxiliary entity），畫雲圖要用每個階段的最後一步；GlobalResult 則每一步都有。</li>
    <li><b>ID 各專案不同</b>同樣是三角形元素，MeshComponentTypeID 在不同專案可能不同；寫程式時用名稱（Description、Name）查，不要寫死數字。</li>
  </ul>
  {K.callout('link', '和 PLAXIS Output 的關係', '<p>PLAXIS Output 畫的雲圖、曲線，資料都來自這個檔案。直接讀 data.db 的好處是可以一次批次取出所有階段、所有區塊的數字，不用在 Output 裡一頁一頁點，也不用再用 getresults 匯出 CSV。</p>')}
</section>'''

    sec_cli = f'''<section class="sec" id="cli" data-num="3.5" data-short="快速查看">
  <div class="sec-head"><span class="sec-num">3.5</span><h2>不寫程式，快速看一眼</h2></div>
  <p>只是想看有哪些表、有幾筆資料，有兩種免寫程式的方法：</p>
  <div class="grid2">
    <div class="card"><h4>DB Browser for SQLite</h4><p>免費的圖形介面工具。用 <b>Open Database Read Only</b> 開啟 data.db，Browse Data 頁可以逐表瀏覽、Execute SQL 頁可以直接下查詢。</p></div>
    <div class="card"><h4>sqlite3 命令列</h4><p>到 sqlite.org 下載 sqlite-tools（Windows 版），解壓後在 PowerShell 執行，加 <code>-readonly</code> 避免改到檔案。</p></div>
  </div>
  {K.codeblock(f"""cd "{os.path.dirname(K.DB)}"
sqlite3.exe -readonly data.db""", 'bash', 'PowerShell')}
  {K.codeblock('''.tables
.headers on
.mode box
SELECT Number, Name FROM I_Phase WHERE PhaseTypeID = 1 ORDER BY Number;
.quit''', 'sql', 'sqlite3 裡面輸入')}
  <p>遇到 BLOB 欄位（Data、NodeData、ComponentData）就要改用 Python，請看 <a href="ch4_postprocessing.html">第 4 章 Post-Processing</a>。</p>
</section>'''

    K.page(os.path.join(SITE, 'ch3_data.html'), page_id='ch3', root='', title='Data Structures · Plaxis2D Simulation',
           short_title='3 · Data Structures', hero=hero, sections=[sec_files, sec_cats, sec_rel, sec_key, sec_cli],
           pager=pager)


# =====================================================================
# 第 4 章：Post-Processing
# =====================================================================
def build_ch4(pager):
    K.set_root('')
    with open(os.path.join(SITE, 'files', 'plx_common.py'), 'w', encoding='utf-8') as f:
        f.write('"""PLAXIS data.db 共用開頭：唯讀連線、BLOB 解碼、常用小函式。\n\n'
                '用法：把這個檔案放在你的程式旁邊，然後 from plx_common import *\n'
                '換別的 data.db 時，只要改下面的 DB 路徑。\n"""\n' + K.HEADER)
    with open(os.path.join(SITE, 'files', 'fig_style.py'), encoding='utf-8') as f:
        fig_style_src = f.read()
    os.makedirs(os.path.join(SITE, 'assets', 'img', 'ch4'), exist_ok=True)
    NS = {}          # 4.6 之後的作圖範例共用同一個命名空間：後面的範例接在前面之後執行

    hero = '''<header class="hero" id="top">
  <div class="eyebrow">Chapter 4</div>
  <h1>Post-Processing</h1>
  <p class="lede"><b>不開 PLAXIS Output，直接用 Python 從 data.db 取出位移、應力與收斂資訊，再畫成可以放進報告的圖。</b>前半段講讀取（連線、BLOB 解碼、共用開頭），後半段講作圖（規範、逐階曲線、收斂歷程、雲圖、塑性範圍）。</p>
  <div class="callout question"><div class="ct">這一章要回答</div><p>怎麼用 Python 把 data.db 裡的結果變成 numpy 陣列？怎麼畫出格式一致、可以直接插進 Word 的圖？</p></div>
</header>'''

    s1 = f'''<section class="sec" id="p1" data-num="4.1" data-short="準備環境">
  <div class="sec-head"><span class="sec-num">4.1</span><h2>準備環境</h2></div>
  <p>需要 Python 3、<code>sqlite3</code>（Python 內建）和 <code>numpy</code>。畫圖再加 <code>matplotlib</code>；想用表格方式整理結果可以裝 <code>pandas</code>。</p>
  {K.codeblock('python -m pip install numpy matplotlib pandas', 'bash', 'PowerShell')}
  {K.callout('pitfall', '先備份、用唯讀開啟', '<p>data.db 是 PLAXIS 的專案檔本體，改壞了模型就打不開。連線時一律用 <code>file:...?mode=ro</code> 唯讀模式，也不要在 PLAXIS 開著這個專案時寫入它。</p>')}
  <p>本章範例都以 <code>e5_TC289_NearMesh</code>（光明地下廠房 plan_e，17 階開挖、無支撐）為例；下方的「執行結果」與圖，都是產生網頁時實際執行範例程式得到的。</p>
</section>'''

    s2 = f'''<section class="sec" id="p2" data-num="4.2" data-short="連線與查詢">
  <div class="sec-head"><span class="sec-num">4.2</span><h2>連線與查詢</h2></div>
  <p>Python 的 sqlite3 和 SQL 查詢一模一樣，差別只是結果會變成 Python 的 list。<code>?</code> 是參數位置，值放在後面的 tuple，不要用字串拼接。</p>
  {K.py("""
rows = con.execute('''SELECT Number, Name FROM I_Phase
                      WHERE PhaseTypeID = ? ORDER BY Number LIMIT 4''', (1,)).fetchall()
for number, name in rows:
    print(number, name)

# 只要一個值：fetchone()[0]
n = con.execute('SELECT COUNT(*) FROM Result').fetchone()[0]
print('Result 共', n, '筆')
""")}
  <p>想用表格方式看，pandas 可以直接把查詢結果變成 DataFrame：</p>
  {K.py("""
import pandas as pd
df = pd.read_sql('SELECT ID, Name, ComponentCount FROM MeshEntity WHERE MeshComponentTypeID = 3 LIMIT 5', con)
print(df.to_string(index=False))
""")}
</section>'''

    s3 = f'''<section class="sec" id="p3" data-num="4.3" data-short="BLOB 解碼原理">
  <div class="sec-head"><span class="sec-num">4.3</span><h2>BLOB 解碼原理</h2></div>
  <p>BLOB 是一串位元組（bytes）。要把它變回數字，只需要知道兩件事：<b>每個數字幾個 bytes、用什麼格式</b>。這兩件事寫在每一列的 <code>DataInterpretationID</code>（見 {K.T('DataInterpretation')}）。</p>
  <h3>手動解一個數字</h3>
  <p>Mesh.NodeData 開頭 8 bytes 是 <code>cdcccccccccc1040</code>。位元組倒過來讀是 <code>4010cccccccccccd</code>，照 IEEE 754 Double 規則就是 4.2：</p>
  {K.py("""
import struct
raw = con.execute('SELECT NodeData FROM Mesh').fetchone()[0]
first8 = raw[:8]
print(first8.hex())                    # 原始位元組
print(struct.unpack('<d', first8)[0])  # '<' = little-endian，'d' = Double
""")}
  <h3>一次解整串：numpy.frombuffer</h3>
  <p>struct 適合解幾個數字；整串幾十萬個數字用 <code>np.frombuffer</code>，速度快很多，而且直接得到陣列。</p>
  {K.py("""
raw = con.execute('SELECT NodeData FROM Mesh').fetchone()[0]
xy = np.frombuffer(raw, dtype='<f8')   # '<f8' = little-endian 8-byte float = Double
print(len(raw), 'bytes →', xy.size, '個 Double')
xy = xy.reshape(-1, 2)                 # 每 2 個一組：(x, y)
print(xy[:3])
""")}
  <div class="tablewrap"><table class="data">
    <tr><th>DataInterpretation</th><th>bytes</th><th>numpy dtype</th><th>這個資料庫裡出現在</th></tr>
    <tr><td>Double</td><td class="num">8</td><td><code>&lt;f8</code></td><td>位移、應力、座標，大部分結果</td></tr>
    <tr><td>Float</td><td class="num">4</td><td><code>&lt;f4</code></td><td>GlobalResult 中間步的整體數值</td></tr>
    <tr><td>SignedInt32</td><td class="num">4</td><td><code>&lt;i4</code></td><td>塑性點旗標、疊代次數</td></tr>
    <tr><td>UnsignedInt64</td><td class="num">8</td><td><code>&lt;u8</code></td><td>節點編號、Global Step Number</td></tr>
    <tr><td>Boolean</td><td class="num">1</td><td><code>&lt;u1</code></td><td>材料與階段設定的開關</td></tr>
    <tr><td>…TableId</td><td class="num">8</td><td><code>&lt;i8</code></td><td>指向另一張表的 ID（列舉值）</td></tr>
  </table></div>
  {K.callout('pitfall', '同一個量，格式可能不同', '<p>GlobalResult 的 SumMStage 在中間步存成 4 bytes 的 Float，在最後一步存成 8 bytes 的 Double。所以<b>不能寫死 <code>&lt;f8</code></b>，每一列都要照它自己的 DataInterpretationID 解碼。下面共用開頭的 <code>decode()</code> 就是做這件事。</p>')}
</section>'''

    s4 = f'''<section class="sec" id="p4" data-num="4.4" data-short="共用開頭">
  <div class="sec-head"><span class="sec-num">4.4</span><h2>共用開頭</h2></div>
  <p>把下面這段存成 <code>plx_common.py</code>（已經放在 <a href="files/plx_common.py">files/plx_common.py</a>），自己的程式寫 <code>from plx_common import *</code> 就能使用。<b>網站上其他所有 Python 範例，都是接在這段後面執行的。</b></p>
  {K.codeblock(K.HEADER, 'python', 'Python · plx_common.py')}
  <div class="tablewrap"><table class="data">
    <tr><th>名稱</th><th>做什麼</th><th>詳見</th></tr>
    <tr><td><code>con</code></td><td>唯讀連線</td><td>4.2</td></tr>
    <tr><td><code>decode(data, interp_id, size)</code></td><td>BLOB → numpy 陣列；size &gt; 1 時每列一個點</td><td>4.3、{K.T('DataInterpretation')}</td></tr>
    <tr><td><code>NODAL … UNIQUE_NODAL</code></td><td>DataLayout 的編號</td><td>{K.T('DataLayout')}</td></tr>
    <tr><td><code>last_step(n)</code></td><td>第 n 個施工階段的最後一步（K_Steps.ID）</td><td>{K.T('K_Steps')}</td></tr>
    <tr><td><code>get_result(step, entity, name, layout)</code></td><td>讀一筆結果並解碼</td><td>{K.T('Result')}</td></tr>
    <tr><td><code>connectivity(entity)</code></td><td>某個網格區塊的元素連接（節點編號，1 起算）</td><td>{K.T('MeshEntity')}</td></tr>
    <tr><td><code>unique_nodes(conn)</code></td><td>Unique Nodal 結果每一列對應的節點編號</td><td>{K.T('Result')}</td></tr>
    <tr><td><code>node_xy()</code></td><td>全部節點座標</td><td>{K.T('Mesh')}</td></tr>
  </table></div>
</section>'''

    s5 = f'''<section class="sec" id="p5" data-num="4.5" data-short="讀一個結果的四步驟">
  <div class="sec-head"><span class="sec-num">4.5</span><h2>讀一個結果的四步驟</h2></div>
  <p>以「L10 結束時，所有岩體區塊的位移」為例，照第 3 章的四個編號依序找：</p>
  {K.py("""
# 1. 哪一步：L10 是 I_Phase.Number = 10
step = last_step(10)

# 2. 哪些網格區塊：這一步還存在、有存位移的岩體區塊（三角形元素群）
ents = [e for (e,) in con.execute('''SELECT ID FROM MeshEntity
         WHERE MeshComponentTypeID = 3 AND MeshEntityApplicationID = 1''')]

# 3 + 4. 哪一種量、排在哪裡：Displacement、Unique Nodal
umax, where = 0, None
for e in ents:
    u = get_result(step, e, 'Displacement', UNIQUE_NODAL)
    if u is None:                       # 已經挖掉的區塊沒有結果
        continue
    ids = unique_nodes(connectivity(e))
    utot = np.hypot(u[:, 0], u[:, 1])
    k = utot.argmax()
    if utot[k] > umax:
        umax, where = utot[k], (e, ids[k])

xy = node_xy()
print('K_Steps.ID =', step)
print(f'最大總位移 {umax*1000:.1f} mm，在區塊 {where[0]} 的節點 {where[1]}，座標 {xy[where[1]-1].round(2)}')
""")}
  <h3>同樣的四步驟，一次跑完所有階段</h3>
  <p>把上面包進迴圈，就能批次檢查每個階段：最大位移、99.9 百分位數、位移超過 0.1 m 的節點數。這是直接讀 data.db 最划算的地方，在 Output 裡要一個階段一個階段點。</p>
  {K.py("""
ents = [e for (e,) in con.execute('SELECT ID FROM MeshEntity WHERE MeshComponentTypeID = 3 AND MeshEntityApplicationID = 1')]
xy = node_xy()
print('階段   最大總位移(mm)  99.9百分位(mm)  >0.1m節點數  最大值位置 (x, y)')
for n in range(1, 18):
    step = last_step(n)
    best, allu = (0, None), []
    for e in ents:
        u = get_result(step, e, 'Displacement', UNIQUE_NODAL)
        if u is None:
            continue
        ut = np.hypot(u[:, 0], u[:, 1])
        allu.append(ut)
        k = ut.argmax()
        if ut[k] > best[0]:
            best = (ut[k], unique_nodes(connectivity(e))[k])
    allu = np.concatenate(allu)
    x, y = xy[best[1] - 1]
    print(f'L{n:02d}  {best[0]*1000:14.1f}  {np.percentile(allu, 99.9)*1000:14.1f}  {(allu > 0.1).sum():11d}   ({x:6.2f}, {y:8.2f})')
""")}
  {K.callout('pitfall', '這個模型從 L11 起有局部異常', '<p>L01～L10 的最大位移在 5～20 mm，合理。L11 起，主廠房右拱腳附近（x ≈ 12.7 m）約 30 個節點的位移達 11 m，L17 右牆腳再多出一群，最大到 214 m；但 99.9 百分位數仍只有 20～50 mm，表示是少數節點的局部數值問題，不是整體行為。畫圖或取最大值前要先排除這些點（4.9）。</p>')}
</section>'''

    s6 = f'''<section class="sec" id="p6" data-num="4.6" data-short="作圖規範">
  <div class="sec-head"><span class="sec-num">4.6</span><h2>作圖規範：fig_style.py</h2></div>
  <p>報告裡的每一張圖用同一套格式，放進 Word 之後字級才會一致。規範寫成一個小模組 <a href="files/fig_style.py">files/fig_style.py</a>，每支畫圖程式開頭 <code>S.apply()</code>、每個座標軸呼叫 <code>S.frame(ax)</code>：</p>
  {K.codeblock(fig_style_src, 'python', 'Python · fig_style.py')}
  <div class="tablewrap"><table class="data">
    <tr><th>項目</th><th>規則</th><th>理由</th></tr>
    <tr><td>圖寬</td><td><code>figsize=(S.width_in(16), …)</code>：圖寬＝插入 Word 的寬度（cm），以同寬插入</td><td>1:1 插入，10 pt 的字在 Word 裡就是 10 pt</td></tr>
    <tr><td>字型</td><td>Times New Roman＋標楷體；座標軸 10 pt、圖例 9 pt</td><td>與報告內文一致</td></tr>
    <tr><td>線條顏色</td><td>黑 → 藍 → 紅，第四條起用灰</td><td>黑白列印仍可分辨；少用顏色</td></tr>
    <tr><td>實測 vs 模擬</td><td>實測：黑色虛線＋空心標記；模擬：藍色實線＋實心標記</td><td>一眼分出資料來源</td></tr>
    <tr><td>框與刻度</td><td>四邊框 0.8 pt、刻度朝內、上右也有刻度；不畫格線</td><td>期刊常見格式</td></tr>
    <tr><td>圖例</td><td>無外框；不可壓到曲線，改放圖頂或獨立一格</td><td>避免遮住資料</td></tr>
    <tr><td>等值圖色階</td><td>總位移 <code>turbo</code>、主應力 <code>jet</code>、塑性點紅色</td><td>場量用彩色色階較易判讀（曲線圖仍用黑藍紅）</td></tr>
    <tr><td>中文與符號</td><td>含中文的字串不要用 <code>$…$</code>；下標直接寫 σ′v0、hp0</td><td>mathtext 沒有中文字型，會變方框</td></tr>
  </table></div>
</section>'''

    s7 = f'''<section class="sec" id="p7" data-num="4.7" data-short="逐階曲線">
  <div class="sec-head"><span class="sec-num">4.7</span><h2>逐階曲線：量測點的相對位移</h2></div>
  <p>第 2 章在拱頂、底板、側牆建了量測點。每一階的最後一步讀出全部節點位移，再取離量測點最近的節點相減，就得到工程上最常看的四條曲線。先寫兩個小函式：</p>
  {K.py("""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import fig_style as S                    # files/fig_style.py，放在自己的程式旁邊
S.apply()

XY = node_xy()
ENTS = [e for (e,) in con.execute('''SELECT ID FROM MeshEntity
         WHERE MeshComponentTypeID = 3 AND MeshEntityApplicationID = 1''')]

def disp_field(step):
    '''這一步全部節點的位移 (N, 2)，單位 m；已挖除、沒有結果的節點是 NaN'''
    u = np.full((len(XY), 2), np.nan)
    for e in ENTS:
        d = get_result(step, e, 'Displacement', UNIQUE_NODAL)
        if d is not None:
            u[unique_nodes(connectivity(e)) - 1] = d
    return u

# 量測點：與第 2 章 point 指令相同的座標
PTS = {'CROWN': (0, -288.3), 'CROWN_REF': (0, -263.3), 'FLOOR': (0, -337.8), 'FLOOR_REF': (0, -362.8),
       'WALL_L': (-12.7, -316.6), 'WALL_R': (12.7, -316.6), 'TR_L': (42.7, -309.2), 'TR_R': (60.5, -309.2)}
NODE = {k: int(np.argmin(np.hypot(XY[:, 0] - x, XY[:, 1] - y))) for k, (x, y) in PTS.items()}   # 0 起算
for k, i in NODE.items():
    print(f'{k:9s} 節點 {i + 1:6d}  離量測點 {np.hypot(*(XY[i] - PTS[k])):.4f} m')
""", ns=NS)}
  <p>因為量測點在建模時就是幾何點，最近節點的距離是 0。接著跑完 17 階：</p>
  {K.py("""
rows = []
for n in range(1, 18):
    u = disp_field(last_step(n)) * 1000                  # mm
    ux = lambda k: u[NODE[k], 0]
    uy = lambda k: u[NODE[k], 1]
    rows.append((n,
                 -(uy('CROWN') - uy('CROWN_REF')),       # 拱頂相對沉陷（向下為正）
                 uy('FLOOR') - uy('FLOOR_REF'),          # 底板相對隆起
                 ux('WALL_L') - ux('WALL_R'),            # 主廠房收斂（兩牆相向為正）
                 ux('TR_L') - ux('TR_R')))               # 主變室收斂
RES = np.array(rows)
print('階段  拱頂沉陷  底板隆起  主廠房收斂  主變室收斂  (mm)')
for r in RES:
    print(f'L{int(r[0]):02d}  {r[1]:8.1f}  {r[2]:8.1f}  {r[3]:10.1f}  {r[4]:10.1f}')
""", ns=NS)}
  {K.py("""
fig, ax = plt.subplots(figsize=(S.width_in(16), S.width_in(7)))
S.frame(ax)
labels = ['拱頂相對沉陷', '底板相對隆起', '主廠房收斂', '主變室收斂']
for j, (lab, mk) in enumerate(zip(labels, 'os^D')):
    ax.plot(RES[:, 0], RES[:, j + 1], '-', marker=mk, label=lab)    # 模擬：實線＋實心標記，顏色依黑藍紅灰
ax.set_xlabel('施工階段')
ax.set_ylabel('相對位移（mm）')
ax.set_xticks(range(1, 18))
ax.set_xticklabels([f'L{n:02d}' for n in range(1, 18)], rotation=90)
ax.set_xlim(0.5, 17.5)
ax.set_ylim(bottom=0)
ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=4)    # 圖例置頂，不壓到曲線
fig.savefig('ch4/curve_phases.png', bbox_inches='tight')
plt.close(fig)
""", ns=NS)}
  {K.figure('ch4/curve_phases.png', '上面程式產生的圖：四個量測量隨施工階段的變化（寬 16 cm）')}
  <p>拱頂沉陷在頭兩階（導坑、擴挖）就幾乎到位；兩牆收斂則要等開挖面通過量測點高程才明顯增加：主廠房 EL.886.4 在 L11 被挖過、主變室 EL.893.8 在 L13–L14 被挖過。</p>
</section>'''

    s8 = f'''<section class="sec" id="p8" data-num="4.8" data-short="收斂歷程">
  <div class="sec-head"><span class="sec-num">4.8</span><h2>收斂歷程：GlobalResult</h2></div>
  <p>{K.T('GlobalResult')} 每一個計算步都有存，所以不開 Output 也能畫出 ΣMstage–步數、CSP–步數，檢查一個相位是怎麼算完（或算不完）的。</p>
  {K.py("""
def global_series(phase_number, var):
    '''某一相每一步的整體量，回傳 (步號, 數值)'''
    rows = con.execute('''SELECT k.Number, g.Data, g.DataInterpretationID, g.ComponentSize
                          FROM GlobalResult g
                          JOIN K_Steps k  ON k.ID = g.K_StepsID
                          JOIN I_Phase p  ON p.ID = k.I_PhaseID
                          JOIN Variables v ON v.ID = g.VariablesID
                          WHERE p.Number = ? AND p.PhaseTypeID = 1 AND v.Name = ?
                          ORDER BY k.Number''', (phase_number, var)).fetchall()
    step = np.array([r[0] for r in rows])
    val = np.array([decode(d, i, s).ravel()[0] for _, d, i, s in rows], dtype=float)
    return step, val

nsteps = {n: len(global_series(n, 'SumMStage')[0]) for n in range(1, 18)}
print('每相步數：', nsteps)
PH = max(nsteps, key=nsteps.get)
print('步數最多的相位：L%02d' % PH)
""", ns=NS)}
  {K.py("""
st, msum = global_series(PH, 'SumMStage')
_, csp = global_series(PH, 'CSP')
_, nit = global_series(PH, 'Number of Iterations')

fig, axs = plt.subplots(3, 1, figsize=(S.width_in(16), S.width_in(12)), sharex=True)
for ax in axs:
    S.frame(ax)
axs[0].plot(st, msum, '-', color=S.BLACK)
axs[0].set_ylabel('ΣMstage')
axs[0].set_ylim(0, 1.05)
axs[1].plot(st, csp, '-', color=S.BLUE)
axs[1].set_ylabel('CSP')
axs[2].plot(st, nit, '-', color=S.RED)
axs[2].set_ylabel('迭代次數')
axs[2].set_xlabel(f'L{PH:02d} 的計算步')
fig.align_ylabels(axs)
fig.savefig('ch4/global_history.png', bbox_inches='tight')
plt.close(fig)
print(f'L{PH:02d}：{len(st)} 步，ΣMstage 最後 {msum[-1]:.3f}，CSP 最小 {csp.min():.3f}，迭代次數最多 {int(nit.max())}')
""", ns=NS)}
  {K.figure('ch4/global_history.png', '步數最多的相位：ΣMstage、CSP（整體勁度參數，1＝彈性、趨近 0＝接近破壞）與每步迭代次數')}
  {K.callout('intuition', '怎麼讀這張圖', '<p>ΣMstage 每一步往上走一點，走到 1.0 這一相才算完成。CSP 往下掉表示塑性區擴大、整體勁度變小；迭代次數多的那幾步，就是塑性區在擴展、自動步長被縮小的地方。CSP 與步長控制的原理見第 1 章。</p>')}
</section>'''

    s9 = f'''<section class="sec" id="p9" data-num="4.9" data-short="雲圖">
  <div class="sec-head"><span class="sec-num">4.9</span><h2>雲圖：總位移與位移向量</h2></div>
  <p>收集每個節點的位移，取元素的三個角點組成三角網格，用 <code>tricontourf</code> 畫等值圖；位移向量先內插到規則網格再畫，箭頭才不會擠成一團。色階上限取 99.9 百分位數，避免少數發散節點吃掉整張圖的顏色。</p>
  {K.py("""
import matplotlib.tri as mtri

def active_tris(step):
    '''這一步還存在的三角形（3 個角點，0 起算）'''
    tris = []
    for e in ENTS:
        if get_result(step, e, 'Displacement', UNIQUE_NODAL) is not None:
            tris.append(connectivity(e)[:, :3] - 1)       # 15 節點三角形的前 3 個是角點
    return np.vstack(tris)

n = 17
step = last_step(n)
u = disp_field(step)
ut = np.hypot(u[:, 0], u[:, 1]) * 1000                   # mm
tri = mtri.Triangulation(XY[:, 0], XY[:, 1], active_tris(step))
vmax = np.ceil(np.nanpercentile(ut, 99.9) / 5) * 5       # 色階上限：99.9 百分位數取整到 5 mm，排除發散節點

fig, ax = plt.subplots(figsize=(S.width_in(16), S.width_in(9)))
S.frame(ax)
cs = ax.tricontourf(tri, np.nan_to_num(ut), levels=np.linspace(0, vmax, 21), cmap='turbo', extend='max')
cb = fig.colorbar(cs, ax=ax, pad=0.02, ticks=np.arange(0, vmax + 1, 10))
cb.set_label('總位移 |u|（mm）')

# 位移向量：內插到 4 m 間距的規則網格
gx, gy = np.meshgrid(np.arange(-30, 81, 4.0), np.arange(-360, -264, 4.0))
fx = mtri.LinearTriInterpolator(tri, np.nan_to_num(u[:, 0]))(gx, gy)
fy = mtri.LinearTriInterpolator(tri, np.nan_to_num(u[:, 1]))(gx, gy)
ax.quiver(gx, gy, fx, fy, color='white', scale=0.6, width=0.0025)

ax.set_xlim(-30, 80); ax.set_ylim(-360, -265); ax.set_aspect('equal')
ax.set_xlabel('x（m）'); ax.set_ylabel('y（m）')
fig.savefig('ch4/contour_L17.png', bbox_inches='tight')
plt.close(fig)
print(f'L{n}：三角形 {tri.triangles.shape[0]:,} 個；|u| 99.9 百分位 {np.nanpercentile(ut, 99.9):.1f} mm；最大 {np.nanmax(ut):.0f} mm（發散節點）')
""", ns=NS)}
  {K.figure('ch4/contour_L17.png', 'L17 結束時的總位移（turbo 色階）與位移向量；色階上限為 99.9 百分位數')}
  <p>要比較不同相位，把 <code>levels</code> 固定成同一組（例如 0～60 mm），不要每張圖各自取上限，否則顏色無法互相比較。</p>
</section>'''

    s10 = f'''<section class="sec" id="p10" data-num="4.10" data-short="塑性範圍">
  <div class="sec-head"><span class="sec-num">4.10</span><h2>塑性範圍：哪裡曾經降伏</h2></div>
  <p><code>Plastic MC History</code> 是每個積分點的歷程旗標（int32，每個三角形 12 個）：曾經到達 MC 降伏面就不為 0，之後卸載也不會歸零，適合用來畫「曾降伏範圍」。data.db 沒有存積分點座標，這裡用元素形心代表整個元素：只要 12 個點中有一個降伏就標紅。</p>
  {K.py("""
def plastic_elements(step, var='Plastic MC History'):
    '''回傳 (形心 x, y, 是否曾降伏)；整塊都相同時 BLOB 只存 1 個值'''
    cx, cy, flag = [], [], []
    for e in ENTS:
        d = get_result(step, e, var, INTEGRATION_POINT)
        if d is None:
            continue
        conn = connectivity(e)
        f = np.broadcast_to(d, (len(conn) * 12,)) if d.size == 1 else d
        flag.append((f.reshape(-1, 12) != 0).any(axis=1))
        c = XY[conn[:, :3] - 1].mean(axis=1)
        cx.append(c[:, 0]); cy.append(c[:, 1])
    return np.concatenate(cx), np.concatenate(cy), np.concatenate(flag)

px, py_, pf = plastic_elements(step)
fig, ax = plt.subplots(figsize=(S.width_in(16), S.width_in(9)))
S.frame(ax)
ax.triplot(tri, color=S.LIGHT, lw=0.2)                    # 淺灰：還存在的網格
ax.plot(px[pf], py_[pf], 's', color='r', ms=1.2, mec='none', label='曾降伏（MC）')
ax.set_xlim(-30, 80); ax.set_ylim(-360, -265); ax.set_aspect('equal')
ax.set_xlabel('x（m）'); ax.set_ylabel('y（m）')
ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.0), markerscale=4)
fig.savefig('ch4/plastic_L17.png', bbox_inches='tight')
plt.close(fig)
print(f'L17：元素 {pf.size:,} 個，曾降伏 {pf.sum():,} 個（{pf.mean() * 100:.1f} %）')
""", ns=NS)}
  {K.figure('ch4/plastic_L17.png', 'L17 結束時曾經降伏的元素（紅）：主廠房左側的楔形帶與岩柱中的 X 形剪切帶')}
  {K.callout('pitfall', '旗標的意義先對照 Output', '<p>PLAXIS 沒有公開塑性旗標的代碼表。<code>Plastic Point Information</code> 是「這一步」的狀態（1 MC、2 張力截斷…為推定），<code>Plastic MC History</code>、<code>Plastic Tension History</code> 是歷程。第一次使用時，挑一個相位和 Output 的 Plastic points 圖對照一次。</p>')}
</section>'''

    s11 = f'''<section class="sec" id="p11" data-num="4.11" data-short="匯出表格">
  <div class="sec-head"><span class="sec-num">4.11</span><h2>匯出成表格</h2></div>
  <p>報告的表格、和其他程式（例如 OpenSees 結果）的比較，最方便的格式是 CSV。用 pandas 加上欄名後輸出；編碼用 <code>utf-8-sig</code>，Excel 直接開中文才不會亂碼。</p>
  {K.py("""
import pandas as pd
df = pd.DataFrame(RES[:, 1:], columns=['拱頂相對沉陷_mm', '底板相對隆起_mm', '主廠房收斂_mm', '主變室收斂_mm'],
                  index=[f'L{n:02d}' for n in range(1, 18)]).round(2)
df.index.name = '階段'
df.to_csv('ch4/phases.csv', encoding='utf-8-sig')
print(df.tail(5).to_string())
""", ns=NS)}
</section>'''

    s12 = f'''<section class="sec" id="p12" data-num="4.12" data-short="常見錯誤與效能">
  <div class="sec-head"><span class="sec-num">4.12</span><h2>常見錯誤與效能</h2></div>
  <ul class="pitfalls">
    <li><b>節點座標錯位</b>忘了節點編號從 1 起算，用 <code>xy[n]</code> 而不是 <code>xy[n - 1]</code>，結果每個點都偏到隔壁節點。</li>
    <li><b>位移對錯節點</b>Unique Nodal 的順序不是節點編號由小到大，而是連接表中第一次出現的順序。用 <code>np.unique(conn)</code> 排序會錯配（實測相鄰區塊共用節點差到 2.6 mm）。</li>
    <li><b>查詢很慢</b>Result 有 568 萬列。WHERE 一定要先給 <code>K_StepsID</code>（有索引 K_StepsID, MeshEntityID, VariablesID）。只用變數名稱查，會掃過整張 3 GB 的表。</li>
    <li><b>buffer size must be a multiple</b>用錯 dtype，例如把 4 bytes 的 Float 當 8 bytes 的 Double 解。改用 <code>decode(data, DataInterpretationID)</code>。</li>
    <li><b>中間步找不到結果</b>中間步只存曲線點的小區塊，整個區塊的結果只在每個階段最後一步。</li>
    <li><b>跨相位比較應力</b>被停用的元素在後續相位不輸出，積分點的順序會變；比較應力要依座標配對，不能照順序相減。</li>
    <li><b>圖上的中文變方框</b>含中文的字串用了 <code>$…$</code>，或沒有先 <code>S.apply()</code> 設定標楷體。</li>
    <li><b>中文路徑</b>路徑含空白、中文沒問題，但連線字串要用 <code>file:{{路徑}}?mode=ro</code> 加 <code>uri=True</code>。</li>
  </ul>
</section>'''

    K.page(os.path.join(SITE, 'ch4_postprocessing.html'), page_id='ch4', root='', title='Post-Processing · Plaxis2D Simulation',
           short_title='4 · Post-Processing', hero=hero,
           sections=[s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12], pager=pager)
