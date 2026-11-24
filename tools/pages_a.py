"""分類 ① 計算結果、② 施工階段、③ 網格"""
import os

import sitekit as K
from sitekit import T, py, sql, columns, callout, quiz, figure, table_section

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIRCLED = '①②③④⑤⑥⑦'


def cat_hero(cat, n, lede_b, lede, question, notes=''):
    cid, name, tables = cat
    chips = ''.join(f'<a href="#t-{t}">{t}<small>{K.fmt_int(K.q1(f"SELECT COUNT(*) FROM \"{t}\""))} 筆</small></a>' for t in tables)
    return f'''<header class="hero" id="top">
  <div class="eyebrow">Chapter 3 · 分類 {CIRCLED[n]} · {len(tables)} 張表</div>
  <h1>{name}</h1>
  <p class="lede"><b>{lede_b}</b>{lede}</p>
  <div class="callout question"><div class="ct">這一類要回答</div><p>{question}</p></div>
  <h3>這一類的表</h3>
  <div class="tchips" style="justify-content:center">{chips}</div>
  {notes}
</header>'''


def write_cat(cat, n, hero, sections, pager):
    cid, name, _ = cat
    K.page(os.path.join(SITE, 'tables', f'{cid}.html'), page_id=cid, root='../',
           title=f'{CIRCLED[n]} {name} · Data Structures · Plaxis2D Simulation', short_title=f'3 · {CIRCLED[n]} {name}',
           hero=hero, sections=sections, pager=pager)


PY_NOTE = '<p class="src" style="margin-top:6px">Python 範例都接在 <a href="../ch4_postprocessing.html#p4">共用開頭</a> 之後執行；下方「執行結果」是實際跑出來的輸出。</p>'


# =====================================================================
# ① 計算結果
# =====================================================================
def build_c1(cat, pager):
    K.set_root('../')
    step_l01 = K.q1('''SELECT k.ID FROM K_Steps k JOIN I_Phase p ON p.ID=k.I_PhaseID
                       WHERE p.Number=1 AND p.PhaseTypeID=1 ORDER BY k.Number DESC LIMIT 1''')
    layout_counts = dict(K.q('SELECT DataLayoutID, COUNT(*) FROM Result GROUP BY 1'))
    n_res = K.q1('SELECT COUNT(*) FROM Result')

    hero = cat_hero(cat, 0, '每算完一步，PLAXIS 就把那一步的結果寫進這兩張表。',
                    '<code>Result</code> 存「每一塊網格」的位移、應力、孔隙水壓；<code>GlobalResult</code> 存「整個模型」的收斂資訊，例如 ΣMstage、疊代次數。檔案 3 GB 幾乎都在這裡。',
                    'L10 開挖結束時，洞室周圍的位移和應力是多少？要從哪裡讀、怎麼解碼？',
                    PY_NOTE)

    # ---------------- Result ----------------
    cols = columns('Result', {
        'ID': '流水號',
        'ComponentSize': '每個點有幾個分量。位移 2（u<sub>x</sub>, u<sub>y</sub>）、有效應力 4（σ<sub>xx</sub>, σ<sub>yy</sub>, σ<sub>zz</sub>, σ<sub>xy</sub>）、純量 1',
        'CreatorID': '由哪個程式寫入，幾乎都是 2 = Kernel（計算核心）',
        'MeshEntityID': '這包數字屬於網格的哪一塊',
        'K_StepsID': '哪一個計算步；再經 K_Steps 對到施工階段',
        'VariablesID': '哪一種量（位移、應力…）',
        'DataLayoutID': '數字排在哪裡：節點、積分點，或整塊一個值',
        'DataInterpretationID': '數字格式：Double、Float、SignedInt32…',
        'Data': '真正的數值，二進位。長度 = 筆數 × ComponentSize × 每個數字的 bytes',
    }, fks={'CreatorID': ['Creator'], 'MeshEntityID': ['MeshEntity'], 'K_StepsID': ['K_Steps'], 'VariablesID': ['Variables'],
            'DataLayoutID': ['DataLayout'], 'DataInterpretationID': ['DataInterpretation']})

    lay = lambda i: K.fmt_int(layout_counts.get(i, 0))
    layout_tbl = f'''<div class="tablewrap"><table class="data">
  <tr><th>DataLayout</th><th>本檔筆數</th><th>一包 Data 裡有幾個點</th><th>排列順序</th><th>典型的量</th></tr>
  <tr><td><b>Unique Nodal</b>（5）</td><td class="num">{lay(5)}</td><td>這一塊的不重複節點數</td><td>節點在連接表中<b>第一次出現的順序</b>（不是編號大小）</td><td>Displacement、Phase Displacement</td></tr>
  <tr><td><b>Integration Point</b>（2）</td><td class="num">{lay(2)}</td><td>元素數 × 12</td><td>第 1 個元素的 12 個積分點，接著第 2 個元素…；座標見 {T('StagedUserFeatureGlobalParameterData')}</td><td>Effective Stress、Plastic Point Information</td></tr>
  <tr><td><b>Mesh Entity</b>（3）</td><td class="num">{lay(3)}</td><td>1</td><td>整塊一個值</td><td>Volume Change、Cluster Info</td></tr>
  <tr><td><b>Nodal</b>（1）</td><td class="num">{lay(1)}</td><td>元素數 × 每元素節點數</td><td>逐元素、逐節點；共用節點會重複出現</td><td>Water Pressure（邊界線）</td></tr>
  <tr><td><b>Element</b>（4）</td><td class="num">{lay(4)}</td><td>元件數</td><td>每個元件一個值</td><td>Prescribed Displacement（固定節點群）</td></tr>
</table></div>'''

    body = f'''
  <p>PLAXIS 每算完一步就往這張表寫入一批列。<b>每一列 = 「哪一步 × 網格的哪一塊 × 哪一種量 × 排在哪裡」的一包數字</b>。全部 {K.fmt_int(n_res)} 列、約 3 GB，是整個檔案的主體。</p>
  {cols}
  <h3>一筆結果由四個編號決定</h3>
  <p>先看某一步、某一塊網格存了哪些量。下面的 <code>{step_l01}</code> 是 L01 的最後一步（見 {T('K_Steps')}），<code>336</code> 是緊鄰主廠房頂拱的一個岩體區塊（見 {T('MeshEntity')}）。</p>
  {sql(f"""
SELECT v.Name AS 變數, dl.Description AS 排列位置, r.ComponentSize AS 分量數,
       di.Description AS 格式, length(r.Data) AS bytes
FROM Result r
JOIN Variables v           ON v.ID  = r.VariablesID
JOIN DataLayout dl         ON dl.ID = r.DataLayoutID
JOIN DataInterpretation di ON di.ID = r.DataInterpretationID
WHERE r.K_StepsID = {step_l01} AND r.MeshEntityID = 336
ORDER BY dl.ID, v.Name;""")}
  {callout('intuition', '查詢一定先給 K_StepsID', '<p>Result 的索引是 <code>(K_StepsID, MeshEntityID, VariablesID)</code>，條件從 K_StepsID 開始給，查詢在毫秒內完成；只用 VariablesID 或變數名稱查，SQLite 會掃過整張 3 GB 的表，要好幾秒到幾分鐘。</p>')}

  <h3>Data 裡的數字怎麼排：五種 DataLayout</h3>
  <p>解碼前要知道 Data 裡的數字各屬於哪個點。這由 <code>DataLayoutID</code> 決定：</p>
  {layout_tbl}
  {callout('pitfall', '只有 1 筆，代表整塊同一個值', '<p>Integration Point 的量，如果 Data 只有 8 bytes（1 個 Double），表示整個區塊每個積分點都是同一個值，例如 Young&#39;s Modulus、Cohesion。讀的時候要把它當成常數，不要以為資料不見。</p>')}

  <h3>Python：讀位移（Unique Nodal）並對到節點座標</h3>
  {py("""
step = last_step(1)                      # L01 最後一步
ent = 336                                # 岩體區塊（MeshEntity.ID）
u = get_result(step, ent, 'Displacement', UNIQUE_NODAL)   # (n, 2)：ux, uy，單位 m
ids = unique_nodes(connectivity(ent))    # 這 n 列各屬於哪個節點
xy = node_xy()[ids - 1]                  # 節點編號從 1 起算，所以 -1

print('K_Steps.ID =', step, '，位移陣列形狀', u.shape, '，節點數', len(ids))
k = np.argmax(np.hypot(u[:, 0], u[:, 1]))
print(f'最大位移在節點 {ids[k]}，座標 ({xy[k, 0]:.2f}, {xy[k, 1]:.2f})')
print(f'ux = {u[k, 0] * 1000:.2f} mm，uy = {u[k, 1] * 1000:.2f} mm')
""")}

  <h3>Python：讀積分點應力，並配上積分點座標</h3>
  {py("""
step, ent = last_step(1), 336
s = get_result(step, ent, 'Effective Stress', INTEGRATION_POINT)     # (元素數×12, 4)

# 積分點座標存在 StagedUserFeatureGlobalParameterData（StressPoints），用同一個區塊去找
row = con.execute('''SELECT g.Data, g.DataInterpretationID, g.ComponentSize
                     FROM StagedUserFeatureGlobalParameterData g
                     JOIN StagedUserFeature f ON f.ID = g.StagedUserFeatureID
                     WHERE f.MeshEntityID = ? AND g.ComponentSize = 2''', (ent,)).fetchone()
pts = decode(*row)                                                  # (元素數×12, 2)

print('應力', s.shape, '；座標', pts.shape)
print('      x         y      σxx      σyy      σzz      σxy   (kPa，壓為負)')
for (x, y), (sxx, syy, szz, sxy) in list(zip(pts, s))[:5]:
    print(f'{x:7.2f} {y:9.2f} {sxx:8.1f} {syy:8.1f} {szz:8.1f} {sxy:8.1f}')
""")}
  {callout('example', '應力分量順序怎麼確認的', '<p>Effective Stress 的 4 個分量依序是 σ<sub>xx</sub>、σ<sub>yy</sub>、σ<sub>zz</sub>、σ<sub>xy</sub>。驗證方法：初始階段 Ph0 用 K0 程序產生地應力，剪應力應為 0；實測第 4 個分量在 Ph0 全部等於 0，且第 1、3 分量與第 2 分量的比值固定（0.485、0.356，即 K0）。</p>')}

  <h3>哪些步有完整結果</h3>
  <p>這個模型每個階段只保存最後一步（階段設定 Maximum Number Of Steps Saved = 1，見 {T('PhaseParameterData')}）。中間的計算步只存「曲線點」所在的單一元素（auxiliary entity），用來畫荷載-位移曲線：</p>
  {sql(f"""
SELECT k.Number AS 階段內第幾步, COUNT(*) AS 結果筆數,
       COUNT(DISTINCT r.MeshEntityID) AS 區塊數
FROM Result r JOIN K_Steps k ON k.ID = r.K_StepsID
WHERE k.I_PhaseID = 4 AND k.Number >= 33          -- I_PhaseID 4 = L01
GROUP BY k.Number;""")}

  <h3>單位與符號</h3>
  <ul>
    <li>單位由 {T('ProjectPropertiesData')} 的 Unit Factor 決定：長度 m、力 kN、時間 day，所以應力是 kPa、位移是 m。</li>
    <li>應力<b>壓為負、拉為正</b>（土壤力學習慣相反，畫圖時常要加負號）。</li>
    <li>本模型的地下水頭設在 −647.8 m，低於模型底部 −637.8 m，全區都在水位以上。Steady Pore Pressure 為正值，代表吸力；計算設定 Ignore Suction = 1，所以它不影響有效應力。</li>
  </ul>
  {quiz('想讀「L05 結束時，區塊 336 的 σ<sub>yy</sub>」，下列哪個組合是對的？',
        ['K_StepsID = 5、Displacement、Unique Nodal，取第 2 欄',
         'K_StepsID = last_step(5)、Effective Stress、Integration Point，取第 2 欄（索引 1）',
         'K_StepsID = last_step(5)、Effective Stress、Mesh Entity，取第 4 欄'],
        1, 'K_StepsID 是全檔流水號，不是階段編號，要用 last_step(5) 換算；應力在積分點上（Integration Point），4 個分量依序 σxx、σyy、σzz、σxy，σyy 是第 2 欄，Python 索引 1。')}
'''
    s_result = table_section('1.1', 'Result', '每一步、每一塊網格的計算結果：位移、應力、孔隙水壓…', body)

    # ---------------- GlobalResult ----------------
    cols = columns('GlobalResult', {
        'ID': '流水號',
        'ComponentSize': '分量數，大多是 1',
        'CreatorID': '由哪個程式寫入',
        'K_StepsID': '哪一個計算步',
        'VariablesID': '哪一種整體量，例如 SumMStage、Number of Iterations',
        'DataInterpretationID': '數字格式。<b>同一個量在中間步是 Float、在最後一步是 Double</b>',
        'Data': '數值（二進位）',
    }, fks={'CreatorID': ['Creator'], 'K_StepsID': ['K_Steps'], 'VariablesID': ['Variables'],
            'DataInterpretationID': ['DataInterpretation']})
    body = f'''
  <p>和 Result 很像，但<b>不分網格區塊</b>：每一步存一組描述「整個模型」的數字，例如這一步的 ΣMstage（施工進度 0→1）、疊代次數、整體誤差、塑性點數。對應 PLAXIS 計算視窗裡看到的那些數字。</p>
  {cols}
  <h3>每一步存了哪些整體量</h3>
  {sql(f"""
SELECT v.Name AS 變數, g.ComponentSize AS 分量數, di.Description AS 格式
FROM GlobalResult g
JOIN Variables v           ON v.ID  = g.VariablesID
JOIN DataInterpretation di ON di.ID = g.DataInterpretationID
WHERE g.K_StepsID = {step_l01}
ORDER BY v.Name;""")}
  <h3>同一個量，中間步與最後一步格式不同</h3>
  {sql("""
SELECT k.Number AS 第幾步, di.Description AS 格式, length(g.Data) AS bytes, hex(g.Data) AS 原始資料
FROM GlobalResult g
JOIN K_Steps k             ON k.ID  = g.K_StepsID
JOIN Variables v           ON v.ID  = g.VariablesID
JOIN DataInterpretation di ON di.ID = g.DataInterpretationID
WHERE k.I_PhaseID = 4 AND v.Name = 'SumMStage' AND k.Number IN (1, 2, 36);""")}
  <p>第 1 步的 <code>CDCCCC3D</code> 是 Float 0.1（4 bytes），第 36 步的 <code>000000000000F03F</code> 是 Double 1.0（8 bytes）。用共用開頭的 <code>decode()</code> 照 DataInterpretationID 解碼，兩種都能正確讀出。</p>
  <h3>Python：各施工階段結束時的整體資訊</h3>
  {py("""
want = ['Global Step Number', 'SumMStage', 'Number of Iterations', 'Max Absolute Phase Displacement']
phases = [n for (n,) in con.execute('SELECT Number FROM I_Phase WHERE PhaseTypeID = 1 AND Number >= 1 ORDER BY Number')]

print('階段  總步號  ΣMstage  最後一步疊代  階段最大位移(mm)')
for num in phases:
    step = last_step(num)
    val = {}
    for name, data, di, cs in con.execute('''SELECT v.Name, g.Data, g.DataInterpretationID, g.ComponentSize
                                             FROM GlobalResult g JOIN Variables v ON v.ID = g.VariablesID
                                             WHERE g.K_StepsID = ?''', (step,)).fetchall():
        if name in want:
            val[name] = decode(data, di, cs)[0]
    print(f'L{num:02d}  {val["Global Step Number"]:6d}  {val["SumMStage"]:7.3f}  {val["Number of Iterations"]:10d}'
          f'  {val["Max Absolute Phase Displacement"] * 1000:14.2f}')
""")}
  <p>「總步號」是跨階段累計的步數（L02 = 36 + 146 = 182）。L11 與 L17 的階段最大位移異常大，原因是少數節點的局部數值問題，詳見 <a href="../ch4_postprocessing.html#p5">第 4 章 4.5</a>。</p>
  {callout('link', '分量數大於 1 的量', '<p>Number of Plastic Points 等量有 6 個分量、Soil Material Values 有 200 個分量。資料庫裡沒有說明各分量的意義，使用前請先對照 PLAXIS Output 的數值確認。</p>')}
'''
    s_global = table_section('1.2', 'GlobalResult', '每一步「整個模型」的數字：ΣMstage、疊代次數、誤差、塑性點數…', body)

    write_cat(cat, 0, hero, [s_result, s_global], pager)


# =====================================================================
# ② 施工階段
# =====================================================================
def build_c2(cat, pager):
    K.set_root('../')
    n_main = K.q1('SELECT COUNT(*) FROM I_Phase WHERE PhaseTypeID=1')
    hero = cat_hero(cat, 1, '施工階段（Phase）與計算步（Step）是讀結果的時間座標。',
                    '<code>I_Phase</code> 是階段清單，<code>K_Steps</code> 是每個階段裡的計算步，<code>PhaseParameterData</code> 是每個階段的計算設定。Result 用的 K_StepsID 要從這裡換算。',
                    f'這個模型有幾個施工階段？「L05 結束時」對應到哪一個 K_StepsID？',
                    PY_NOTE)

    # ---------------- I_Phase ----------------
    cols = columns('I_Phase', {
        'ID': '流水號（其他表用這個）',
        'Number': 'PLAXIS 畫面上的階段編號：初始階段 0、L01 = 1 … L17 = 17；Unstaged = −1',
        'Name': '階段名稱（PLAXIS 裡輸入的 ID）',
        'ParentPhaseID': '從哪一個階段接續（Start from phase）；初始階段為 NULL',
        'I_ProjectID': '所屬專案',
        'PhaseTypeID': '1 = Main（真正的施工階段）、4 = Initial Condition、5 = Unstaged',
    }, fks={'ParentPhaseID': ['I_Phase'], 'I_ProjectID': ['I_Project'], 'PhaseTypeID': ['PhaseType']})
    body = f'''
  <p>施工階段清單。37 筆裡<b>只有 {n_main} 筆是真正的施工階段</b>（PhaseTypeID = 1：Ph0 地應力平衡＋L01～L17 開挖），其餘是 PLAXIS 內部用的副本。</p>
  {cols}
  <h3>37 筆的組成</h3>
  {sql("""
SELECT t.Description AS 階段類型, COUNT(*) AS 筆數,
       MIN(p.Number) AS 最小Number, MAX(p.Number) AS 最大Number
FROM I_Phase p JOIN PhaseType t ON t.ID = p.PhaseTypeID
GROUP BY t.ID;""")}
  <p>Initial Condition 是每個 Main 階段的「初始狀態」副本，ParentPhaseID 指回對應的 Main 階段，只有 1 個 Number = 0 的計算步，存邊界水頭、固定條件等起始資料。讀計算結果時用 <code>PhaseTypeID = 1</code> 篩掉它們即可。</p>
  <h3>真正的施工階段</h3>
  {sql("""
SELECT p.ID, p.Number, p.Name, p.ParentPhaseID,
       (SELECT COUNT(*) FROM K_Steps k WHERE k.I_PhaseID = p.ID) AS 計算步數
FROM I_Phase p
WHERE p.PhaseTypeID = 1
ORDER BY p.Number;""")}
  <h3>Python：沿著 ParentPhaseID 走出施工順序</h3>
  {py("""
info = {pid: (num, name, parent)
        for pid, num, name, parent in con.execute('SELECT ID, Number, Name, ParentPhaseID FROM I_Phase')}

pid = con.execute('SELECT ID FROM I_Phase WHERE Number = 17 AND PhaseTypeID = 1').fetchone()[0]
chain = []
while pid is not None:                   # 從 L17 一路往回找到初始階段
    num, name, parent = info[pid]
    chain.append(f'{num:2d}  {name}')
    pid = parent
print('\\n'.join(reversed(chain)))
""")}
  {quiz(f'I_Phase 有 37 筆，這個模型真正的施工階段有幾個？',
        ['37 個', '36 個（扣掉 Unstaged）', f'{n_main} 個（PhaseTypeID = 1）'], 2,
        f'只有 PhaseTypeID = 1（Main）是施工階段：Ph0 加 L01～L17 共 {n_main} 個。另外 18 筆是 Initial Condition 副本，1 筆是 Unstaged。')}
'''
    s_phase = table_section('2.1', 'I_Phase', '施工階段清單：編號、名稱、從哪個階段接續', body)

    # ---------------- K_Steps ----------------
    cols = columns('K_Steps', {
        'ID': '<b>全檔唯一的步編號</b>；Result、GlobalResult 用的就是它',
        'Number': '這個階段裡的第幾步，每個階段從 1 重新起算（Initial Condition、Unstaged 為 0）',
        'I_PhaseID': '屬於哪個施工階段',
    }, fks={'I_PhaseID': ['I_Phase']})
    body = f'''
  <p>每個施工階段裡的計算步（PLAXIS 計算視窗裡的 Step）。PLAXIS 用荷載增量把一個階段分成很多小步，每一步都在這裡留一列。</p>
  {cols}
  {callout('pitfall', 'ID 和 Number 不一樣', '<p>Number 是「階段內第幾步」，每個階段都從 1 開始；ID 是整個檔案的流水號。Result 的 K_StepsID 對的是 <b>ID</b>。L01 的第 36 步，ID 是 40。</p>')}
  <h3>每個階段的最後一步</h3>
  <p>完整結果只存在每個階段的最後一步，所以最常用的查詢就是找出它的 ID：</p>
  {sql("""
SELECT p.Number AS 階段, p.Name AS 名稱, MAX(k.Number) AS 步數,
       (SELECT k2.ID FROM K_Steps k2 WHERE k2.I_PhaseID = p.ID
         ORDER BY k2.Number DESC LIMIT 1) AS 最後一步的ID
FROM I_Phase p JOIN K_Steps k ON k.I_PhaseID = p.ID
WHERE p.PhaseTypeID = 1
GROUP BY p.ID ORDER BY p.Number;""")}
  <h3>Python：last_step() 怎麼寫</h3>
  <p>共用開頭的 <code>last_step()</code> 就是把上面的查詢包成函式：</p>
  {py("""
for n in (0, 1, 2, 17):
    print(f'階段 {n:2d} 的最後一步：K_Steps.ID = {last_step(n)}')

# 看 L02 的步：Number 從 1 開始，ID 接著 L01 之後
pid = con.execute('SELECT ID FROM I_Phase WHERE Number = 2 AND PhaseTypeID = 1').fetchone()[0]
rows = con.execute('SELECT ID, Number FROM K_Steps WHERE I_PhaseID = ? ORDER BY Number', (pid,)).fetchall()
print('L02 前三步 (ID, Number)：', rows[:3], '… 最後一步：', rows[-1])
""")}
'''
    s_steps = table_section('2.2', 'K_Steps', '每個施工階段裡的計算步；Result 用的 K_StepsID 就是這裡的 ID', body)

    # ---------------- PhaseParameterData ----------------
    cols = columns('PhaseParameterData', {
        'ID': '流水號',
        'PhaseParameterID': '參數名稱',
        'CreatorID': '由哪個程式寫入',
        'ParentParameterDataID': '指向<b>同一張表</b>的另一列，用來分組，例如屬於「Deformation Calculation Data」群組',
        'I_PhaseID': '哪個施工階段',
        'DataInterpretationID': '數值格式；<code>PhaseParameterTableId</code> 表示值是 PhaseParameter 的 ID（列舉值）',
        'Data': '參數值（二進位）；群組列本身為 NULL',
    }, fks={'PhaseParameterID': ['PhaseParameter'], 'CreatorID': ['Creator'], 'ParentParameterDataID': ['PhaseParameterData'],
            'I_PhaseID': ['I_Phase'], 'DataInterpretationID': ['DataInterpretation']})
    body = f'''
  <p>每個施工階段的計算設定，對應 PLAXIS「Phases」視窗裡的選項：計算類型、荷載輸入方式、最大步數、容許誤差、是否忽略吸力…。每個 Main 階段約 112 列。</p>
  {cols}
  <h3>值是編號時：列舉值</h3>
  <p>像「計算類型」這種選項，Data 存的不是文字而是編號，格式標成 <code>PhaseParameterTableId</code>，數字就是 {T('PhaseParameter')} 的 ID。例如 69 = Plastic Calculation、83 = Staged Construction Loading Type。PhaseParameter 同時當「參數名稱表」與「選項名稱表」用。</p>
  <h3>同名參數出現多次：看群組</h3>
  {sql("""
SELECT p.Description AS 參數, g.Description AS 所屬群組, di.Description AS 格式, hex(d.Data) AS 原始資料
FROM PhaseParameterData d
JOIN PhaseParameter p           ON p.ID  = d.PhaseParameterID
LEFT JOIN PhaseParameterData pd ON pd.ID = d.ParentParameterDataID
LEFT JOIN PhaseParameter g      ON g.ID  = pd.PhaseParameterID
LEFT JOIN DataInterpretation di ON di.ID = d.DataInterpretationID
WHERE d.I_PhaseID = 4 AND p.Description LIKE 'Maximum Number Of%';""")}
  <p>同一個「Maximum Number Of Steps」分屬變形、孔隙水壓、熱計算三個群組。<code>FFFFFFFFFFFFFFFF</code> 是 UnsignedInt64 的最大值 18446744073709551615，PLAXIS 用它表示「未設定」（Double 參數則用 −1）。這個模型只做變形計算，看 Deformation Calculation Data 群組即可。</p>
  <h3>Python：讀出 L01 的變形計算設定</h3>
  {py("""
pid = con.execute('SELECT ID FROM I_Phase WHERE Number = 1 AND PhaseTypeID = 1').fetchone()[0]
names = dict(con.execute('SELECT ID, Description FROM PhaseParameter'))   # 參數名稱，也是列舉值名稱
rows = con.execute('''SELECT ID, PhaseParameterID, ParentParameterDataID, DataInterpretationID, Data
                      FROM PhaseParameterData WHERE I_PhaseID = ?''', (pid,)).fetchall()
group = {rid: names[ppid] for rid, ppid, *_ in rows}         # 本階段每一列的名稱，用來認群組

for rid, ppid, parent, di, data in rows:
    if data is None or group.get(parent) != 'Deformation Calculation Data':
        continue
    v = decode(data, di)[0]
    if di == 14:                       # PhaseParameterTableId → 換成選項名稱
        v = names[int(v)]
    print(f'{names[ppid]:38s} {v}')
""")}
'''
    s_ppd = table_section('2.3', 'PhaseParameterData', '每個施工階段的計算設定：計算類型、步數上限、容許誤差…', body)

    write_cat(cat, 1, hero, [s_phase, s_steps, s_ppd], pager)


# =====================================================================
# ③ 網格
# =====================================================================
def build_c3(cat, pager):
    K.set_root('../')
    n_nodes = K.q1('SELECT NodeCount FROM Mesh')
    hero = cat_hero(cat, 2, '網格分三層：節點座標、網格區塊、區塊之間的關係。',
                    '<code>Mesh</code> 存全部節點的座標；<code>MeshEntity</code> 把元素分成一塊一塊（岩體區塊、邊界線、監測點…），每塊記錄它的元素用了哪些節點；<code>MeshEntityInterconnectivity</code> 記錄區塊之間的從屬關係。',
                    'Result 裡的一包位移，各屬於哪個節點、座標在哪裡？',
                    PY_NOTE)

    # ---------------- Mesh ----------------
    cols = columns('Mesh', {
        'ID': '只有 1 筆',
        'Dimension': '維度：2（x, y）',
        'NodeCount': f'節點總數：{K.fmt_int(n_nodes)}',
        'I_ProjectID': '所屬專案',
        'NodeData': '全部節點座標：NodeCount × Dimension 個 Double，依序 x1, y1, x2, y2, …',
    }, fks={'I_ProjectID': ['I_Project']})
    body = f'''
  <p>整個模型的節點座標表，只有一列。在 sqlite3 用 <code>SELECT * FROM Mesh</code> 看到的那串 <code>x'cdcccccccccc1040…'</code> 就是 NodeData：每 16 個十六進位字元（8 bytes）是一個 Double，依序是節點 1 的 x、節點 1 的 y、節點 2 的 x…</p>
  {cols}
  <h3>Python：還原節點座標</h3>
  {py("""
count, dim, data = con.execute('SELECT NodeCount, Dimension, NodeData FROM Mesh').fetchone()
xy = np.frombuffer(data, '<f8').reshape(count, dim)
print('節點數', count, '，陣列形狀', xy.shape, '，資料長度', len(data), 'bytes')
print('x 範圍', xy[:, 0].min(), '～', xy[:, 0].max(), ' m')
print('y 範圍', xy[:, 1].min(), '～', xy[:, 1].max(), ' m')

# 節點編號 n 的座標 = xy[n - 1]（編號從 1 開始）
for name, cd in con.execute("SELECT Name, ComponentData FROM MeshEntity WHERE Name IN ('UserPoint#001', 'UserPoint#003')"):
    n = int(np.frombuffer(cd, '<u8')[0])
    print(f'{name}：節點 {n}，座標 {xy[n - 1]}')
""")}
  {callout('pitfall', '節點編號從 1 開始', f'<p>其他表裡的節點編號範圍是 1～{K.fmt_int(n_nodes)}（實測：所有三角形用到的節點編號最小 1、最大 {K.fmt_int(n_nodes)}，恰好等於節點數）。Python 陣列從 0 開始，所以要 <code>xy[n - 1]</code>。少減 1，座標就會錯到隔壁節點。</p>')}
'''
    s_mesh = table_section('3.1', 'Mesh', f'整個模型的節點座標（{K.fmt_int(n_nodes)} 個節點）', body)

    # ---------------- MeshEntity ----------------
    cols = columns('MeshEntity', {
        'ID': '流水號；Result 的 MeshEntityID 指的就是它',
        'Name': '名稱，例如 BoreholePolygon_…（岩體區塊）、BoundaryLine_…（邊界線）、UserPoint#…（監測點）',
        'ComponentCount': '元件數：區塊有幾個元素，或節點群有幾個節點',
        'Hash': 'PLAXIS 內部的雜湊值，用來比對網格是否變過',
        'CreatorID': '1 = Input（使用者建的）、3 = Mesher（網格產生器建的）',
        'MeshID': '所屬網格',
        'MeshComponentTypeID': '元件種類：1 節點、2 線、3 三角形',
        'MeshEntityApplicationID': '用途：1 完整區塊、2 部分節點、4 輔助元素…',
        'ParentMeshEntityID': '本檔全部是 NULL；從屬關係改記在 MeshEntityInterconnectivity',
        'ComponentData': '元件內容（二進位）：通常是節點編號，見下表',
    }, fks={'CreatorID': ['Creator'], 'MeshID': ['Mesh'], 'MeshComponentTypeID': ['MeshComponentType'],
            'MeshEntityApplicationID': ['MeshEntityApplication'], 'ParentMeshEntityID': ['MeshEntity']})
    body = f'''
  <p>網格被切成一塊一塊，每塊就是一個 MeshEntity。最重要的是 <b>32 個岩體區塊</b>（三角形、完整區塊），計算結果幾乎都掛在它們身上。每塊的 ComponentData 記錄它的元素用了哪些節點（連接表）。</p>
  {cols}
  <h3>有哪幾種區塊</h3>
  {sql("""
SELECT c.Description AS 元件, a.Description AS 用途, COUNT(*) AS 區塊數,
       SUM(m.ComponentCount) AS 元件總數, MIN(m.Name) AS 名稱例子
FROM MeshEntity m
JOIN MeshComponentType c     ON c.ID = m.MeshComponentTypeID
JOIN MeshEntityApplication a ON a.ID = m.MeshEntityApplicationID
GROUP BY c.ID, a.ID ORDER BY c.ID, a.ID;""")}
  <h3>ComponentData 怎麼解</h3>
  <div class="tablewrap"><table class="data">
    <tr><th>區塊種類</th><th>每個元件幾 bytes</th><th>內容</th></tr>
    <tr><td>三角形・完整區塊（岩體）</td><td class="num">120</td><td>15 個 UInt64 節點編號（15 節點三角形）；<b>前 3 個是角點</b>，其餘是邊上與內部節點</td></tr>
    <tr><td>線・完整區塊（邊界線）</td><td class="num">40</td><td>5 個 UInt64 節點編號（5 節點線元素，配合 15 節點三角形的邊）</td></tr>
    <tr><td>節點・完整區塊（監測點、固定節點）</td><td class="num">8</td><td>1 個 UInt64 節點編號</td></tr>
    <tr><td>輔助元素（auxiliary entity）</td><td class="num">8</td><td>1 個 UInt64：<b>母區塊裡第幾個元素（0 起算）</b>，母區塊見 MeshEntityInterconnectivity</td></tr>
    <tr><td>部分節點（CN_…，曲線點）</td><td class="num">16</td><td>2 個 UInt64，指向母區塊裡的位置；一般讀結果用不到</td></tr>
  </table></div>
  <h3>Python：讀一個岩體區塊的元素</h3>
  {py("""
conn = connectivity(336)
xy = node_xy()
print('區塊 336：', conn.shape[0], '個元素，每個元素', conn.shape[1], '個節點')
print('第 1 個元素的節點編號：', conn[0].tolist())
print('三個角點座標：')
print(xy[conn[0, :3] - 1])

# 線元素與輔助元素
cnt, cd = con.execute("SELECT ComponentCount, ComponentData FROM MeshEntity WHERE Name = 'BoundaryLine_145'").fetchone()
print('BoundaryLine_145 前兩個線元素：', np.frombuffer(cd, '<u8').reshape(cnt, -1)[:2].tolist())
for name, cd in con.execute('''SELECT Name, ComponentData FROM MeshEntity
                               WHERE MeshEntityApplicationID = 4 AND MeshComponentTypeID = 3 LIMIT 2'''):
    print(name, '→ 母區塊裡的元素索引', np.frombuffer(cd, '<u8').tolist())
""")}
  <h3>Python：把網格畫出來</h3>
  {py("""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

xy = node_xy()
ents = [e for (e,) in con.execute('SELECT ID FROM MeshEntity WHERE MeshComponentTypeID = 3 AND MeshEntityApplicationID = 1')]
fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
for ax in axes:
    for e in ents:
        tri = connectivity(e)[:, :3] - 1          # 取 3 個角點，換成 0 起算
        ax.triplot(xy[:, 0], xy[:, 1], tri, lw=0.12, color='0.3')
    ax.set_aspect('equal')
axes[1].set_xlim(-30, 80); axes[1].set_ylim(-350, -275)
axes[0].set_title('Whole model'); axes[1].set_title('Around the caverns')
fig.savefig('mesh.png', dpi=150, bbox_inches='tight')
print('畫了', len(ents), '個岩體區塊、', sum(len(connectivity(e)) for e in ents), '個元素')
""")}
  {figure('mesh.png', '上面程式產生的圖：左為全模型，右為洞室附近（只畫元素角點連線）')}
'''
    s_ent = table_section('3.2', 'MeshEntity', '網格區塊：岩體區塊、邊界線、監測點，以及各自的元素連接', body)

    # ---------------- MeshEntityInterconnectivity ----------------
    cols = columns('MeshEntityInterconnectivity', {
        'ID': '流水號',
        'SourceInterconnectivityID': '來源區塊',
        'TargetInterconnectivityID': '目標區塊',
        'InterconnectivityTypeID': '關係種類；讀法是「來源 是 目標 的 …」',
    }, fks={'SourceInterconnectivityID': ['MeshEntity'], 'TargetInterconnectivityID': ['MeshEntity'],
            'InterconnectivityTypeID': ['InterconnectivityType']})
    body = f'''
  <p>記錄網格區塊之間的關係，例如「這條邊界線是那個岩體區塊的外側面」「這個輔助元素是那個區塊的一部分」。欄位名雖然叫 InterconnectivityID，存的其實是 {T('MeshEntity')} 的 ID。</p>
  {cols}
  <h3>有哪些關係</h3>
  {sql("""
SELECT t.Description AS 關係, COUNT(*) AS 筆數,
       (SELECT s.Name || '  →  ' || g.Name
          FROM MeshEntityInterconnectivity y
          JOIN MeshEntity s ON s.ID = y.SourceInterconnectivityID
          JOIN MeshEntity g ON g.ID = y.TargetInterconnectivityID
         WHERE y.InterconnectivityTypeID = t.ID LIMIT 1) AS 例子_來源到目標
FROM MeshEntityInterconnectivity x
JOIN InterconnectivityType t ON t.ID = x.InterconnectivityTypeID
GROUP BY t.ID ORDER BY 2 DESC;""")}
  <h3>Python：從曲線點的輔助元素找回母區塊與座標</h3>
  <p>中間計算步只存輔助元素的結果（見 {T('Result')}）。要知道那個元素在哪裡，就靠「Is Part Of」（ID 10）找母區塊，再用元素索引取節點：</p>
  {py("""
# 找出有最多計算步結果的輔助元素（三角形）
def n_steps(e):
    return con.execute('''SELECT COUNT(*) FROM Result r JOIN Variables v ON v.ID = r.VariablesID
                          WHERE r.MeshEntityID = ? AND v.Name = 'Displacement' ''', (e,)).fetchone()[0]
aux = [e for (e,) in con.execute('SELECT ID FROM MeshEntity WHERE MeshEntityApplicationID = 4 AND MeshComponentTypeID = 3')]
aux_id = max(aux, key=n_steps)
aux_name, cd = con.execute('SELECT Name, ComponentData FROM MeshEntity WHERE ID = ?', (aux_id,)).fetchone()

parent = con.execute('''SELECT TargetInterconnectivityID FROM MeshEntityInterconnectivity
                        WHERE SourceInterconnectivityID = ? AND InterconnectivityTypeID = 10''', (aux_id,)).fetchone()[0]
k = int(np.frombuffer(cd, '<u8')[0])               # 母區塊裡第 k 個元素（0 起算）
nodes = connectivity(parent)[k]
print(aux_name)
print('→ 母區塊', parent, '的第', k, '個元素，角點座標', node_xy()[nodes[:3] - 1].round(2).tolist())

# 這個輔助元素在每一步都有位移 → 可畫成荷載-位移曲線（MeshEntityID 有索引，查詢很快）
steps = con.execute('''SELECT r.K_StepsID, p.Number, k.Number FROM Result r
                       JOIN Variables v ON v.ID = r.VariablesID
                       JOIN K_Steps k   ON k.ID = r.K_StepsID
                       JOIN I_Phase p   ON p.ID = k.I_PhaseID
                       WHERE r.MeshEntityID = ? AND v.Name = 'Displacement' ORDER BY r.K_StepsID''', (aux_id,)).fetchall()
print('有位移結果的計算步：', len(steps), '步（階段', sorted({ph for _, ph, _ in steps}), '）')
for sid, ph, kn in steps[:3] + steps[-2:]:
    u = get_result(sid, aux_id, 'Displacement', UNIQUE_NODAL)
    print(f'  階段 {ph} 第 {kn:2d} 步：第 1 個節點 uy = {u[0, 1] * 1000:8.3f} mm')
""")}
'''
    s_ic = table_section('3.3', 'MeshEntityInterconnectivity', '網格區塊之間的關係：誰是誰的面、誰是誰的一部分', body)

    write_cat(cat, 2, hero, [s_mesh, s_ent, s_ic], pager)
