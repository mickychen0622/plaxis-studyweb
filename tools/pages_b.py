"""分類 ④ 材料、⑤ 模型物件、⑥ 專案資訊、⑦ 代碼對照表"""
import sitekit as K
from sitekit import T, py, sql, columns, callout, quiz, figure, table_section, full_list, esc
from pages_a import cat_hero, write_cat, PY_NOTE


# =====================================================================
# ④ 材料
# =====================================================================
def build_c4(cat, pager):
    K.set_root('../')
    hero = cat_hero(cat, 3, '材料清單與材料參數。',
                    '<code>Material</code> 列出材料，<code>MaterialParameterData</code> 存每個材料的參數值（凝聚力、摩擦角…）。這個模型只有一種岩體材料 Rock_MC_e5（Mohr-Coulomb），其餘是它的副本。',
                    'Rock_MC_e5 的 c、φ 存在哪裡？為什麼有 21 筆材料？',
                    PY_NOTE)

    cols = columns('Material', {
        'ID': '流水號',
        'Name': '材料名稱（PLAXIS 材料庫裡的名稱）',
        'IdentificationGUID': '材料的唯一識別碼',
        'I_ProjectID': '所屬專案',
        'ParentMaterialID': '如果是副本，指向原始材料；原始材料為 NULL',
    }, fks={'I_ProjectID': ['I_Project'], 'ParentMaterialID': ['Material']})
    body = f'''
  <p>材料清單。21 筆裡真正不同的只有兩種：<b>Rock_MC_e5</b>（ID 1，原始材料）與 <b>NULL MATERIAL</b>（ID 3，邊界條件等不需要材料的物件用）。其餘 19 筆都是 Rock_MC_e5 的副本，ParentMaterialID = 1。</p>
  {cols}
  {K.sample('Material', 6)}
  <h3>副本是給各施工階段用的</h3>
  <p>岩體區塊在每個階段使用哪個材料，記在 {T('StagedUserFeaturePhasesState')} 的 MaterialID。PLAXIS 為不同階段建立材料副本：</p>
  {sql("""
SELECT p.Number AS 階段, p.Name AS 名稱,
       GROUP_CONCAT(DISTINCT s.MaterialID) AS 岩體區塊用的MaterialID
FROM StagedUserFeaturePhasesState s
JOIN StagedUserFeature f ON f.ID = s.StagedUserFeatureID
JOIN I_Phase p           ON p.ID = s.I_PhaseID
WHERE f.StructureTypeID = 1 AND p.PhaseTypeID = 1
GROUP BY p.ID ORDER BY p.Number;""")}
  <h3>Python：確認副本的參數和原件一樣</h3>
  {py("""
base = dict(con.execute('SELECT MaterialParameterID, Data FROM MaterialParameterData WHERE MaterialID = 1'))
copies = [m for (m,) in con.execute('SELECT ID FROM Material WHERE ParentMaterialID = 1')]
diff = []
for m in copies:
    d = dict(con.execute('SELECT MaterialParameterID, Data FROM MaterialParameterData WHERE MaterialID = ?', (m,)))
    if d != base:
        diff.append(m)
print('Rock_MC_e5 副本', len(copies), '個；參數和原件不同的副本：', diff or '沒有')
""")}
'''
    s_mat = table_section('4.1', 'Material', '材料清單：原始材料與各階段用的副本', body)

    cols = columns('MaterialParameterData', {
        'ID': '流水號',
        'MaterialID': '哪個材料',
        'MaterialParameterID': '哪個參數',
        'DataInterpretationID': '數值格式（Double、Boolean、UnsignedInt64…）',
        'Data': '參數值（二進位）',
    }, fks={'MaterialID': ['Material'], 'MaterialParameterID': ['MaterialParameter'],
            'DataInterpretationID': ['DataInterpretation']})
    body = f'''
  <p>每個材料一列一個參數，每個材料 28 列。內容是計算核心需要的一組參數：材料模型的旗標（Is HoekBrown…）、凝聚力、摩擦角的 sin 值、初始孔隙比…</p>
  {cols}
  <h3>Python：讀出 Rock_MC_e5 的參數</h3>
  {py("""
import math
rows = con.execute('''SELECT p.Description, d.DataInterpretationID, d.Data
                      FROM MaterialParameterData d JOIN MaterialParameter p ON p.ID = d.MaterialParameterID
                      WHERE d.MaterialID = 1 ORDER BY d.ID''').fetchall()
for name, di, data in rows:
    v = decode(data, di)[0]
    if name.startswith('Is ') and v == 0:     # 沒用到的材料模型旗標略過
        continue
    print(f'{name:30s} {v}')

sinphi = dict((n, decode(d, di)[0]) for n, di, d in rows)['SinPhi Friction Angle']
print(f'→ 摩擦角 φ = asin({sinphi:.4f}) = {math.degrees(math.asin(sinphi)):.1f}°')
""")}
  {callout('pitfall', 'E、ν、γ 不在這張表', '<p>這張表沒有楊氏模數、柏松比、單位重。楊氏模數以計算結果的形式存在 Result（變數 Young&#39;s Modulus，積分點），例如區塊 336 在 L01 是 15,000,000 kPa = 15 GPa。要完整的材料參數，請以 PLAXIS Input 的材料視窗或專案的建模腳本為準。</p>')}
'''
    s_mpd = table_section('4.2', 'MaterialParameterData', '材料參數值：c、sinφ、孔隙比、材料模型旗標', body)
    write_cat(cat, 3, hero, [s_mat, s_mpd], pager)


# =====================================================================
# ⑤ 模型物件
# =====================================================================
def build_c5(cat, pager):
    K.set_root('../')
    hero = cat_hero(cat, 4, '模型物件＝PLAXIS 裡可以「在某個階段開或關」的東西。',
                    '岩體區塊、邊界條件、固定條件都是 StagedUserFeature。這一類記錄它們是什麼、每個階段開或關、用哪個材料、各階段的參數，以及積分點座標。<b>開挖順序就藏在這裡。</b>',
                    '每個施工階段挖掉了哪些岩體區塊？積分點的座標在哪裡？',
                    PY_NOTE)

    # StagedUserFeature
    cols = columns('StagedUserFeature', {
        'ID': '流水號',
        'Name': '物件名稱，例如 Soil_1_…（岩體區塊）、GWFlowBaseBC_…（地下水邊界）',
        'IdentificationGUID': '唯一識別碼',
        'MeshEntityID': '這個物件對應的網格區塊',
        'StructureTypeID': '物件種類：Soil、Fixity、Viscous Boundary…',
    }, fks={'MeshEntityID': ['MeshEntity'], 'StructureTypeID': ['StructureType']})
    body = f'''
  <p>模型中每一個「可分階段啟用」的物件。它把 PLAXIS 裡看到的物件（岩體多邊形、邊界條件）對應到 {T('MeshEntity')} 的網格區塊。</p>
  {cols}
  <h3>這個模型有哪些物件</h3>
  {sql("""
SELECT t.Description AS 物件種類, COUNT(*) AS 個數, MIN(f.Name) AS 名稱例子
FROM StagedUserFeature f JOIN StructureType t ON t.ID = f.StructureTypeID
GROUP BY t.ID ORDER BY 2 DESC;""")}
  <p>只有岩體（Soil）與各種邊界條件，<b>沒有 Plate、Anchor、Embedded Beam 等結構元素</b>。也就是說，這個 e5 模型沒有用結構元素模擬支撐。</p>
  <h3>岩體區塊與網格區塊的對應</h3>
  {sql("""
SELECT f.ID, f.Name, f.MeshEntityID, m.ComponentCount AS 元素數
FROM StagedUserFeature f JOIN MeshEntity m ON m.ID = f.MeshEntityID
WHERE f.StructureTypeID = 1
ORDER BY f.ID LIMIT 8;""")}
'''
    s_suf = table_section('5.1', 'StagedUserFeature', '模型物件清單：岩體區塊、邊界條件，以及它們對應的網格區塊', body)

    # StagedUserFeaturePhasesState
    cols = columns('StagedUserFeaturePhasesState', {
        'ID': '流水號；下一張表用它指回來',
        'IsEnabled': '1 = 這個階段啟用；0 = 關閉（岩體區塊就是被挖除）',
        'StagedUserFeatureID': '哪個物件',
        'MaterialID': '這個階段用的材料',
        'I_PhaseID': '哪個階段',
    }, fks={'StagedUserFeatureID': ['StagedUserFeature'], 'MaterialID': ['Material'], 'I_PhaseID': ['I_Phase']})
    body = f'''
  <p>「物件 × 階段」的狀態表：每個物件在每個階段是開是關、用哪個材料。對應 PLAXIS Staged construction 畫面裡把區塊切成灰色（關閉）的操作。</p>
  {cols}
  <h3>每個階段還剩幾個岩體區塊</h3>
  {sql("""
SELECT p.Number AS 階段, p.Name AS 名稱,
       SUM(s.IsEnabled) AS 啟用的岩體區塊, COUNT(*) - SUM(s.IsEnabled) AS 已挖除
FROM StagedUserFeaturePhasesState s
JOIN StagedUserFeature f ON f.ID = s.StagedUserFeatureID
JOIN I_Phase p           ON p.ID = s.I_PhaseID
WHERE f.StructureTypeID = 1 AND p.PhaseTypeID = 1
GROUP BY p.ID ORDER BY p.Number;""")}
  <h3>Python：找出開挖順序並畫圖</h3>
  {py("""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

phases = con.execute('SELECT ID, Number FROM I_Phase WHERE PhaseTypeID = 1 ORDER BY Number').fetchall()
removed = {}                                   # 網格區塊 ID → 在第幾階段被挖除
for pid, num in phases:
    for (ent,) in con.execute('''SELECT f.MeshEntityID FROM StagedUserFeaturePhasesState s
                                 JOIN StagedUserFeature f ON f.ID = s.StagedUserFeatureID
                                 WHERE s.I_PhaseID = ? AND f.StructureTypeID = 1 AND s.IsEnabled = 0''', (pid,)):
        removed.setdefault(ent, num)           # 只記第一次被關掉的階段
for num in sorted(set(removed.values())):
    print(f'L{num:02d} 挖除的網格區塊：', sorted(e for e, n in removed.items() if n == num))

xy = node_xy()
tris, vals = [], []
for e, num in removed.items():
    t = connectivity(e)[:, :3] - 1
    tris.append(t)
    vals.append(np.full(len(t), num))
tris, vals = np.vstack(tris), np.concatenate(vals)

fig, ax = plt.subplots(figsize=(10, 6.5))
tc = ax.tripcolor(xy[:, 0], xy[:, 1], tris, facecolors=vals, cmap='viridis', vmin=1, vmax=17)
for e, num in removed.items():
    c = xy[connectivity(e)[:, :3] - 1].reshape(-1, 2).mean(axis=0)
    ax.text(c[0], c[1], f'L{num:02d}', ha='center', va='center', fontsize=7,
            bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.7))
fig.colorbar(tc, ax=ax, label='Excavated in phase')
ax.set_xlim(-18, 66); ax.set_ylim(-342, -284)          # 只看洞室範圍
ax.set_aspect('equal'); ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)')
ax.set_title('Excavation sequence')
fig.savefig('excavation.png', dpi=150, bbox_inches='tight')
""")}
  {figure('excavation.png', '上面程式產生的圖：每個岩體區塊在哪個階段被挖除（左側主廠房、右側主變室）')}
'''
    s_state = table_section('5.2', 'StagedUserFeaturePhasesState', '每個物件在每個階段開或關、用哪個材料：開挖順序就在這裡', body)

    # StagedUserFeaturePhaseParameterData
    cols = columns('StagedUserFeaturePhaseParameterData', {
        'ID': '流水號',
        'ComponentSize': '分量數',
        'CreatorID': '由哪個程式寫入',
        'StagedUserFeaturePhasesStateID': '哪個「物件 × 階段」',
        'StagedUserFeatureParameterID': '哪個參數',
        'DataLayoutID': '數值排在哪裡（可為 NULL）',
        'DataInterpretationID': '數值格式；<code>StagedUserFeatureParameterTableId</code> 表示值是 StagedUserFeatureParameter 的 ID',
        'ParentParameterDataID': '指向同表另一列，用來分組',
        'Data': '參數值（二進位）',
    }, fks={'CreatorID': ['Creator'], 'StagedUserFeaturePhasesStateID': ['StagedUserFeaturePhasesState'],
            'StagedUserFeatureParameterID': ['StagedUserFeatureParameter'], 'DataLayoutID': ['DataLayout'],
            'DataInterpretationID': ['DataInterpretation'], 'ParentParameterDataID': ['StagedUserFeaturePhaseParameterData']})
    body = f'''
  <p>物件在某個階段的參數：水壓條件、水頭、應力釋放（Deconfinement）、是否套用強度折減…。它不直接記錄階段，而是透過 StagedUserFeaturePhasesStateID 指到「物件 × 階段」那一列。</p>
  {cols}
  <h3>Python：讀區塊 336 在 L01 的參數</h3>
  {py("""
ent = 336
pid = con.execute('SELECT ID FROM I_Phase WHERE Number = 1 AND PhaseTypeID = 1').fetchone()[0]
names = dict(con.execute('SELECT ID, Description FROM StagedUserFeatureParameter'))
rows = con.execute('''SELECT d.StagedUserFeatureParameterID, d.DataInterpretationID, d.ComponentSize, d.Data
                      FROM StagedUserFeaturePhaseParameterData d
                      JOIN StagedUserFeaturePhasesState s ON s.ID = d.StagedUserFeaturePhasesStateID
                      JOIN StagedUserFeature f            ON f.ID = s.StagedUserFeatureID
                      WHERE f.MeshEntityID = ? AND s.I_PhaseID = ?''', (ent, pid)).fetchall()
for ppid, di, cs, data in rows:
    v = decode(data, di, cs)
    if v is None:
        shown = '（群組，無值）'
    elif di == 16:                                  # StagedUserFeatureParameterTableId → 選項名稱
        shown = names[int(v.ravel()[0])]
    elif v.size > 6:
        shown = f'{v.size} 個值，例如 {np.round(v.ravel()[:3], 2).tolist()}'
    else:
        shown = np.round(v.ravel(), 4).tolist()
    print(f'{names[ppid]:28s} {shown}')
""")}
  <p>Head = −647.8 m 就是 {T('Result')} 提到的地下水位設定；Deconfinement = −1 表示沒有使用應力釋放（β 法）。</p>
'''
    s_ppd = table_section('5.3', 'StagedUserFeaturePhaseParameterData', '物件在各階段的參數：水壓條件、水頭、應力釋放…', body)

    # StagedUserFeatureGlobalParameterData
    cols = columns('StagedUserFeatureGlobalParameterData', {
        'ID': '流水號',
        'ComponentSize': '分量數：座標為 2（x, y），元素值為 1',
        'CreatorID': '由哪個程式寫入',
        'StagedUserFeatureID': '哪個物件',
        'StagedUserFeatureParameterID': '哪個參數；本檔全部是 StressPoints',
        'DataLayoutID': '數值排在哪裡',
        'DataInterpretationID': '數值格式',
        'ParentParameterDataID': '分組用',
        'Data': '數值（二進位）',
    }, fks={'CreatorID': ['Creator'], 'StagedUserFeatureID': ['StagedUserFeature'],
            'StagedUserFeatureParameterID': ['StagedUserFeatureParameter'], 'DataLayoutID': ['DataLayout'],
            'DataInterpretationID': ['DataInterpretation'], 'ParentParameterDataID': ['StagedUserFeatureGlobalParameterData']})
    body = f'''
  <p>和上一張表一樣存物件參數，但<b>不分階段</b>。本檔 64 列全部是 32 個岩體區塊的 <b>StressPoints</b>（應力點，即積分點），每個區塊兩列：</p>
  <ul>
    <li>ComponentSize 2：每個積分點的 (x, y)，共「元素數 × 12」點，順序和 Result 裡 Integration Point 的資料一致。</li>
    <li>ComponentSize 1：每個元素一個值，數值等於元素面積的 2 倍（即三角形座標轉換的 Jacobian 行列式）。</li>
  </ul>
  {cols}
  <h3>Python：取出積分點座標並驗證</h3>
  {py("""
ent = 336
suf = con.execute('SELECT ID FROM StagedUserFeature WHERE MeshEntityID = ?', (ent,)).fetchone()[0]
rows = con.execute('''SELECT ComponentSize, DataLayoutID, DataInterpretationID, Data
                      FROM StagedUserFeatureGlobalParameterData WHERE StagedUserFeatureID = ?''', (suf,)).fetchall()
arr = {cs: decode(data, di, cs) for cs, dl, di, data in rows}
pts, w = arr[2], arr[1]
conn = connectivity(ent)
print('元素', len(conn), '個；積分點座標', pts.shape, '；每元素值', w.shape)

# 每元素值 ÷ 元素面積
xy = node_xy()
a, b, c = (xy[conn[:, i] - 1] for i in range(3))
area = 0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1]))
print('每元素值 / 元素面積：最小', (w / area).min().round(6), '最大', (w / area).max().round(6))

# 第 1 個元素的 12 個積分點都落在第 1 個元素裡（用重心座標檢查）
T = np.array([[a[0, 0] - c[0, 0], b[0, 0] - c[0, 0]], [a[0, 1] - c[0, 1], b[0, 1] - c[0, 1]]])
lam = np.linalg.solve(T, (pts[:12] - c[0]).T)
print('第 1 個元素的 12 個積分點都在元素內：', bool(np.all(lam > 0) and np.all(lam.sum(0) < 1)))
""")}
  {callout('link', '用途', '<p>想把應力畫成雲圖或沿某條線取值，就需要積分點座標。搭配方式見 ' + T('Result') + ' 的「讀積分點應力」範例。</p>')}
'''
    s_gpd = table_section('5.4', 'StagedUserFeatureGlobalParameterData', '不分階段的物件參數；本檔是岩體區塊的積分點座標（StressPoints）', body)

    cols = columns('StagedUserFeatureRelation', {
        'ID': '流水號',
        'I_PhaseID': '哪個階段',
        'SourceStagedUserFeatureID': '來源物件',
        'TargetStagedUserFeatureID': '目標物件',
        'StagedUserFeatureRelationTypeID': '關係種類；只有 Rigid Slave Of（剛體從屬）',
    }, fks={'I_PhaseID': ['I_Phase'], 'SourceStagedUserFeatureID': ['StagedUserFeature'],
            'TargetStagedUserFeatureID': ['StagedUserFeature'], 'StagedUserFeatureRelationTypeID': ['StagedUserFeatureRelationType']})
    body = f'''
  <p>物件之間在某個階段的關係，例如把一群物件設成剛體（Rigid body）時，記錄「誰是誰的從屬」。<b>這個模型沒有使用剛體，所以是空表。</b>其他有剛體的專案才會有資料。</p>
  {cols}
  {sql("SELECT COUNT(*) AS 筆數 FROM StagedUserFeatureRelation;")}
'''
    s_rel = table_section('5.5', 'StagedUserFeatureRelation', '物件之間的關係（剛體從屬）；本檔為空', body)
    write_cat(cat, 4, hero, [s_suf, s_state, s_ppd, s_gpd, s_rel], pager)


# =====================================================================
# ⑥ 專案資訊
# =====================================================================
def build_c6(cat, pager):
    K.set_root('../')
    hero = cat_hero(cat, 5, '整個專案只有一份的資訊。',
                    '資料庫格式版本、專案識別碼，以及重力、水的單位重、單位、分析類型等整體設定。',
                    '這個資料庫用什麼單位？分析類型是平面應變嗎？',
                    PY_NOTE)

    cols = columns('Version', {'ID': '只有 1 筆', 'Major': '主版本', 'Minor': '次版本', 'Patch': '修訂版', 'Date': '日期'})
    body = f'''
  <p>資料庫<b>格式</b>的版本（不是 PLAXIS 軟體版本）。寫程式時可以先讀它，格式改版時提醒自己檢查解碼方式。</p>
  {cols}
  {K.sample('Version', 1)}
'''
    s_ver = table_section('6.1', 'Version', '資料庫格式版本', body)

    cols = columns('I_Project', {'ID': '只有 1 筆，其他表的 I_ProjectID 都指向它', 'IdentificationGUID': '專案的唯一識別碼'})
    body = f'''
  <p>專案本身，只有一筆。I_Phase、Mesh、Material、ProjectPropertiesData 都用 I_ProjectID 指向它。</p>
  {cols}
  {K.sample('I_Project', 1)}
'''
    s_proj = table_section('6.2', 'I_Project', '專案識別碼', body)

    cols = columns('ProjectPropertiesData', {
        'ID': '流水號',
        'ProjectPropertiesID': '哪個設定項目',
        'I_ProjectID': '所屬專案',
        'DataInterpretationID': '數值格式；<code>ProjectPropertiesTableId</code> 表示值是 ProjectProperties 的 ID',
        'Data': '設定值（二進位）',
    }, fks={'ProjectPropertiesID': ['ProjectProperties'], 'I_ProjectID': ['I_Project'],
            'DataInterpretationID': ['DataInterpretation']})
    body = f'''
  <p>專案的整體設定，對應 PLAXIS「Project properties」視窗：重力、水的單位重、模型範圍、單位、分析類型、元素類型…</p>
  {cols}
  <h3>Python：讀出全部設定</h3>
  {py("""
names = dict(con.execute('SELECT ID, Description FROM ProjectProperties'))
for pid, di, data in con.execute('SELECT ProjectPropertiesID, DataInterpretationID, Data FROM ProjectPropertiesData ORDER BY ID'):
    v = decode(data, di)
    if di == 17:                                   # ProjectPropertiesTableId → 選項名稱
        v = names[int(v[0])]
    elif v is not None:
        v = v[0] if len(v) == 1 else v.tolist()
    print(f'{names[pid]:52s} {v}')
""", max_lines=40)}
  <h3>單位怎麼看</h3>
  <div class="tablewrap"><table class="data">
    <tr><th>設定</th><th>值</th><th>意思</th></tr>
    <tr><td>Length Unit Factor</td><td class="num">1</td><td>長度單位 m</td></tr>
    <tr><td>Force Unit Factor</td><td class="num">1000</td><td>力的單位 = 1000 N = kN，所以應力是 kN/m² = kPa</td></tr>
    <tr><td>Time Unit Factor</td><td class="num">86400</td><td>時間單位 = 86400 s = day</td></tr>
    <tr><td>Mass Unit Factor</td><td class="num">1000</td><td>質量單位 = 1000 kg = t</td></tr>
    <tr><td>Contour Min / Max</td><td>(−315, −637.8) ～ (360, 0)</td><td>模型範圍（m）</td></tr>
    <tr><td>Analysis Type</td><td>Plane Strain</td><td>平面應變分析</td></tr>
    <tr><td>Soil Element Type</td><td>Fifteen-Noded Triangle</td><td>15 節點三角形元素，每元素 12 個積分點</td></tr>
  </table></div>
'''
    s_ppd = table_section('6.3', 'ProjectPropertiesData', '專案整體設定：重力、單位、分析類型、元素類型', body)
    write_cat(cat, 5, hero, [s_ver, s_proj, s_ppd], pager)


# =====================================================================
# ⑦ 代碼對照表
# =====================================================================
def lookup_section(num, table, short, intro, coldesc, listing_sql=None, fks=None, filterable=False, hint='輸入關鍵字篩選', extra=''):
    cols = columns(table, coldesc, fks=fks)
    listing_sql = listing_sql or f'SELECT * FROM "{table}" ORDER BY ID'
    if filterable:
        listing = full_list(f'list-{table}', listing_sql, hint)
    else:
        tbl, _ = K.result_table(listing_sql)
        listing = f'<div class="tablewrap">{tbl}</div>'
    body = f'<p>{intro}</p>{cols}<div class="subhead">全部內容</div>{listing}{extra}'
    return table_section(num, table, short, body)


def build_c7(cat, pager):
    K.set_root('../')
    hero = cat_hero(cat, 6, '這一類全是「編號 → 名稱」的字典。',
                    '其他表為了省空間只存編號，意思要到這裡查。它們幾乎不用單獨讀，而是在 JOIN 時把編號翻成文字。內容由 PLAXIS 固定寫入，大部分和模型無關。',
                    'Result 裡的 VariablesID = 某個數字，是什麼量？DataInterpretationID 怎麼對到 numpy 型別？',
                    PY_NOTE + '<p class="src" style="margin-top:2px">分成四組：結果相關（7.1–7.6）、網格相關（7.7–7.11）、階段與物件（7.12–7.17）、材料與專案（7.18–7.19）。</p>')
    S = []

    # ---- 結果相關 ----
    used = K.q('SELECT DISTINCT VariablesID FROM Result')
    S.append(lookup_section('7.1', 'Variables', '結果變數名稱：Displacement、Effective Stress…（508 種）',
        f'PLAXIS 所有可能輸出的量，共 508 種；這個檔案的 Result 實際用到 {len(used)} 種。Result、GlobalResult 的 VariablesID 都指向這裡。',
        {'ID': '編號', 'Name': '變數名稱（讀結果時用的就是這個字串）', 'Origin': '來源，幾乎都是 Core', 'QuantitiesID': '物理量（決定單位）'},
        'SELECT v.ID, v.Name, v.Origin, q.Name AS 物理量 FROM Variables v JOIN Quantities q ON q.ID = v.QuantitiesID ORDER BY v.ID',
        fks={'QuantitiesID': ['Quantities']}, filterable=True, hint='輸入關鍵字篩選，例如 Stress、Displacement',
        extra=f'''<h3>這個檔案實際用到哪些變數</h3>
  {sql("""
SELECT v.Name AS 變數, q.Name AS 物理量, COUNT(*) AS Result筆數
FROM Result r
JOIN Variables v  ON v.ID = r.VariablesID
JOIN Quantities q ON q.ID = v.QuantitiesID
GROUP BY v.ID ORDER BY 3 DESC;""")}
  {callout('pitfall', '這個查詢很慢', '<p>它沒有指定 K_StepsID，必須掃過整張 Result（約 5 秒以上）。只查一次沒關係，寫在迴圈裡就會很慢。</p>')}'''))

    S.append(lookup_section('7.2', 'Quantities', '物理量與因次：長度、力、應力…（88 種）',
        '每個變數屬於哪種物理量，以及它的因次（長度、質量、時間…的次方）。可以用來判斷單位：例如 Stress 的因次是 M¹L⁻¹T⁻²。',
        {'ID': '編號', 'Name': '物理量名稱', 'LengthDimension': '長度的次方', 'MassDimension': '質量的次方', 'TimeDimension': '時間的次方',
         'TemperatureDimension': '溫度的次方', 'ElectricCurrentDimension': '電流的次方', 'AmountOfSubstanceDimension': '物質量的次方',
         'LuminousIntensityDimension': '光強度的次方'},
        filterable=True, hint='輸入關鍵字篩選，例如 Pressure'))

    S.append(lookup_section('7.3', 'VariableStructureType', '變數 × 物件種類：哪些變數適用於哪種物件',
        '多對多的對照：某個變數適用於哪些物件種類（例如 Effective Stress 適用於 Soil）。一般讀結果用不到。',
        {'ID': '編號', 'VariablesID': '變數', 'StructureTypeID': '物件種類'},
        '''SELECT x.ID, v.Name AS 變數, s.Description AS 物件種類
           FROM VariableStructureType x JOIN Variables v ON v.ID = x.VariablesID JOIN StructureType s ON s.ID = x.StructureTypeID ORDER BY x.ID''',
        fks={'VariablesID': ['Variables'], 'StructureTypeID': ['StructureType']}, filterable=True, hint='輸入關鍵字篩選，例如 Plate'))

    S.append(lookup_section('7.4', 'DataLayout', '結果數值排在哪裡：節點、積分點、整塊…',
        f'Result 的 Data 裡每個數字屬於哪個點。各種排列的詳細規則與本檔筆數，見 {T("Result")} 的「五種 DataLayout」。',
        {'ID': '編號（共用開頭定義成 NODAL=1、INTEGRATION_POINT=2、MESH_ENTITY=3、ELEMENT=4、UNIQUE_NODAL=5）', 'Description': '名稱'}))

    DT = {1: '<f4', 2: '<f8', 3: '<u1', 4: '<i1', 5: '<u2', 6: '<i2', 7: '<u4', 8: '<i4', 9: '<u8', 10: '<i8',
          11: '<u1', 12: 'S1', 13: '<u1', 14: '<i8', 15: '<i8', 16: '<i8', 17: '<i8', 18: '<i8'}
    rows = K.q('SELECT ID, Description, Size FROM DataInterpretation ORDER BY ID')
    tbl = ('<div class="tablewrap"><table class="data"><tr><th>ID</th><th>Description</th><th>Size (bytes)</th><th>numpy dtype（共用開頭的 DTYPE）</th></tr>'
           + ''.join(f'<tr><td class="num">{i}</td><td>{esc(d)}</td><td class="num">{s}</td><td><code>{esc(DT[i])}</code></td></tr>' for i, d, s in rows)
           + '</table></div>')
    cols = columns('DataInterpretation', {'ID': '編號；各表的 DataInterpretationID 指向這裡', 'Description': '格式名稱', 'Size': '每個數字幾 bytes'})
    S.append(table_section('7.5', 'DataInterpretation', 'BLOB 的數字格式：Double、Float、Int…', f'''
  <p><b>解碼 BLOB 最重要的一張表。</b>每一個存 BLOB 的列都帶一個 DataInterpretationID，告訴你每個數字幾 bytes、什麼格式。ID 14～18 的「…TableId」是 8 bytes 整數，值是另一張表的 ID（列舉值）。</p>
  {cols}{tbl}
  {callout('example', '為什麼 dtype 前面有 &lt;', '<p><code>&lt;</code> 表示 little-endian：位元組由低位到高位存放，所以在十六進位字串裡看起來是「倒過來」的。Intel／Apple Silicon 電腦都是這種順序。</p>')}'''))

    S.append(lookup_section('7.6', 'Creator', '資料由哪個程式寫入：Input、Kernel、Mesher…',
        '每筆結果與網格區塊由哪個 PLAXIS 元件產生。Result 幾乎都是 2（Kernel，計算核心）；MeshEntity 是 1（Input）或 3（Mesher）。',
        {'ID': '編號', 'Description': '程式名稱'}))

    # ---- 網格相關 ----
    S.append(lookup_section('7.7', 'MeshComponentType', '網格元件種類：節點、線、三角形',
        '網格區塊的元件種類，並指定每種元件預設的元素類型與積分方法。三角形 → 元素類型 8（Triangle、order 4 = 15 節點）＋積分方法 4（Gauss order 6 = 12 個積分點）。',
        {'ID': '編號', 'Description': '名稱', 'MeshElementTypeID': '元素類型', 'IntegrationMethodTypeID': '積分方法'},
        '''SELECT c.ID, c.Description, c.MeshElementTypeID, e.Description || ' (order ' || e.ElementOrder || ')' AS 元素類型,
                  c.IntegrationMethodTypeID, i.Description || ' (order ' || i.IntegrationOrder || ')' AS 積分方法
           FROM MeshComponentType c JOIN MeshElementType e ON e.ID = c.MeshElementTypeID
           JOIN IntegrationMethodType i ON i.ID = c.IntegrationMethodTypeID ORDER BY c.ID''',
        fks={'MeshElementTypeID': ['MeshElementType'], 'IntegrationMethodTypeID': ['IntegrationMethodType']}))

    S.append(lookup_section('7.8', 'MeshElementType', '元素類型與階數：Triangle order 4 = 15 節點…',
        'PLAXIS 支援的元素類型。ElementOrder 是插值階數：三角形 order 2 = 6 節點、order 4 = 15 節點；線 order 4 = 5 節點。',
        {'ID': '編號', 'Description': '元素形狀', 'ElementOrder': '插值階數（−1 = 不適用）'}))

    S.append(lookup_section('7.9', 'IntegrationMethodType', '數值積分方法與階數',
        '元素數值積分的方法。15 節點三角形用 Gauss order 6，每個元素 12 個積分點（應力點）。',
        {'ID': '編號', 'Description': '方法名稱', 'IntegrationOrder': '積分階數'}))

    S.append(lookup_section('7.10', 'MeshEntityApplication', '網格區塊的用途：完整區塊、部分節點、輔助元素…',
        '網格區塊是完整的一塊，還是從別的區塊挑出來的一部分。讀岩體結果用 1（FullElement）；中間步的曲線點結果在 4（AuxiliaryElement）。',
        {'ID': '編號', 'Description': '名稱'}))

    S.append(lookup_section('7.11', 'InterconnectivityType', '網格區塊之間的關係種類',
        f'{T("MeshEntityInterconnectivity")} 用的關係名稱。讀法是「來源 是 目標 的 …」，例如 10 Is Part Of：輔助元素是母區塊的一部分。',
        {'ID': '編號', 'Description': '關係名稱'}))

    # ---- 階段與物件 ----
    S.append(lookup_section('7.12', 'PhaseType', '階段類型：Main、Initial Condition…',
        '讀計算結果時只看 1（Main）。4（Initial Condition）是每個階段的初始狀態副本，5（Unstaged）是 PLAXIS 內部用的。',
        {'ID': '編號', 'Description': '名稱'}))

    S.append(lookup_section('7.13', 'StructureType', '物件種類：Soil、Plate、Anchor、Fixity…',
        '模型物件的種類。最後一欄是這個檔案裡各種物件的個數；0 表示這個模型沒用到。',
        {'ID': '編號', 'Description': '名稱'},
        '''SELECT t.ID, t.Description, (SELECT COUNT(*) FROM StagedUserFeature f WHERE f.StructureTypeID = t.ID) AS 本檔物件數
           FROM StructureType t ORDER BY t.ID'''))

    S.append(lookup_section('7.14', 'PhaseParameter', '階段參數名稱，也兼作選項名稱（211 筆）',
        f'{T("PhaseParameterData")} 的參數名稱。同一張表也存選項值的名稱：例如 69 = Plastic Calculation，是「Deformation Calculation Type」的一個選項。',
        {'ID': '編號', 'Description': '名稱'}, filterable=True, hint='輸入關鍵字篩選，例如 Calculation'))

    S.append(lookup_section('7.15', 'StagedUserFeatureParameter', '物件參數名稱，也兼作選項名稱（156 筆）',
        f'{T("StagedUserFeaturePhaseParameterData")} 與 {T("StagedUserFeatureGlobalParameterData")} 的參數名稱，同樣兼作選項名稱（例如 Water Condition 的選項）。',
        {'ID': '編號', 'Description': '名稱'}, filterable=True, hint='輸入關鍵字篩選，例如 Water'))

    S.append(lookup_section('7.16', 'SUFParameterParentChild', '物件參數的上下層關係',
        '物件參數之間的父子關係：某個參數底下包含哪些子參數。',
        {'ID': '編號', 'ParentSUFParameterID': '上層參數', 'ChildSUFParameterID': '下層參數'},
        '''SELECT x.ID, x.ParentSUFParameterID, p.Description AS 上層參數, x.ChildSUFParameterID, c.Description AS 下層參數
           FROM SUFParameterParentChild x JOIN StagedUserFeatureParameter p ON p.ID = x.ParentSUFParameterID
           JOIN StagedUserFeatureParameter c ON c.ID = x.ChildSUFParameterID ORDER BY x.ID''',
        fks={'ParentSUFParameterID': ['StagedUserFeatureParameter'], 'ChildSUFParameterID': ['StagedUserFeatureParameter']}))

    S.append(lookup_section('7.17', 'StagedUserFeatureRelationType', '物件關係種類（只有剛體從屬）',
        f'{T("StagedUserFeatureRelation")} 用的關係種類，只有一種。',
        {'ID': '編號', 'Description': '名稱'}))

    # ---- 材料與專案 ----
    S.append(lookup_section('7.18', 'MaterialParameter', '材料參數名稱（39 種）',
        f'{T("MaterialParameterData")} 的參數名稱：材料模型旗標、凝聚力、sinφ、Hoek-Brown 參數…',
        {'ID': '編號', 'Description': '名稱'}))

    S.append(lookup_section('7.19', 'ProjectProperties', '專案設定項目名稱，也兼作選項名稱（43 筆）',
        f'{T("ProjectPropertiesData")} 的設定名稱；Analysis Type Plane Strain 等選項也在這裡。',
        {'ID': '編號', 'Description': '名稱'}, filterable=True, hint='輸入關鍵字篩選，例如 Unit'))

    write_cat(cat, 6, hero, S, pager)
