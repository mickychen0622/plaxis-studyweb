"""產生 Plaxis2D Simulation 網站中「由 data.db 產生」的頁面：
第 3 章 ch3_data.html、tables/c1–c7.html、第 4 章 ch4_postprocessing.html。
其餘章節（index、ch1、ch2、ch5、ch6）是手寫的靜態頁，不由這支程式產生。

用法：
    python3 build_site.py  <data.db 的完整路徑>

所有數字、範例輸出都是從 data.db 實際查詢、實際執行得到的；換一個 data.db 重跑就會更新。
資料庫以唯讀方式開啟，不會被修改。
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import sitekit as K  # noqa: E402

CATS = [
    ('c1', '計算結果', ['Result', 'GlobalResult']),
    ('c2', '施工階段', ['I_Phase', 'K_Steps', 'PhaseParameterData']),
    ('c3', '網格', ['Mesh', 'MeshEntity', 'MeshEntityInterconnectivity']),
    ('c4', '材料', ['Material', 'MaterialParameterData']),
    ('c5', '模型物件', ['StagedUserFeature', 'StagedUserFeaturePhasesState', 'StagedUserFeaturePhaseParameterData',
                       'StagedUserFeatureGlobalParameterData', 'StagedUserFeatureRelation']),
    ('c6', '專案資訊', ['Version', 'I_Project', 'ProjectPropertiesData']),
    ('c7', '代碼對照表', ['Variables', 'Quantities', 'VariableStructureType', 'DataLayout', 'DataInterpretation', 'Creator',
                         'MeshComponentType', 'MeshElementType', 'IntegrationMethodType', 'MeshEntityApplication',
                         'InterconnectivityType', 'PhaseType', 'StructureType', 'PhaseParameter',
                         'StagedUserFeatureParameter', 'SUFParameterParentChild', 'StagedUserFeatureRelationType',
                         'MaterialParameter', 'ProjectProperties']),
]
CIRCLED = '①②③④⑤⑥⑦'


def register():
    for cid, _, tables in CATS:
        for t in tables:
            K.TABLE_PAGE[t] = (f'{cid}.html', f't-{t}')
    names = {r[0] for r in K.q("SELECT name FROM sqlite_master WHERE type='table'")}
    covered = set(K.TABLE_PAGE)
    if names != covered:
        raise SystemExit(f'表格分類不完整：少了 {sorted(names - covered)}，多了 {sorted(covered - names)}')


# 全站閱讀順序（與 assets/common.js 的導覽一致）；只有 ch3、tables/c1–c7、ch4 由這支程式產生
SEQ = [('index.html', '首頁'),
       ('ch1_principle.html', '1 · Principle of Numerical Simulation'),
       ('ch2_preprocessing.html', '2 · Input: Pre-Processing'),
       ('ch3_data.html', '3 · Data Structures')] + \
      [(f'tables/{c[0]}.html', f'3 · {CIRCLED[n]} {c[1]}') for n, c in enumerate(CATS)] + \
      [('ch4_postprocessing.html', '4 · Post-Processing'),
       ('ch5_mohrcoulomb.html', '5 · Mohr-Coulomb'),
       ('ch6_pm4sand.html', '6 · PM4Sand')]


def pager_for(path):
    """path = 本頁在 SEQ 裡的檔名，例如 'ch3_data.html'、'tables/c1.html'"""
    i = [p for p, _ in SEQ].index(path)
    root = '../' if path.startswith('tables/') else ''
    prev = f'<a href="{root}{SEQ[i - 1][0]}"><span class="dir">← 上一頁</span>{SEQ[i - 1][1]}</a>' if i > 0 else '<span></span>'
    nxt = (f'<a class="next" href="{root}{SEQ[i + 1][0]}"><span class="dir">下一頁 →</span>{SEQ[i + 1][1]}</a>'
           if i + 1 < len(SEQ) else f'<a class="next" href="{root}index.html"><span class="dir">回到 →</span>首頁</a>')
    return prev + nxt


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    t0 = time.time()
    K.setup(os.path.abspath(sys.argv[1]), os.path.join(SITE, 'assets', 'img'))
    register()
    import pages_a
    import pages_b
    import pages_ch
    builders = [pages_a.build_c1, pages_a.build_c2, pages_a.build_c3,
                pages_b.build_c4, pages_b.build_c5, pages_b.build_c6, pages_b.build_c7]
    only = os.environ.get('ONLY')            # 例如 ONLY=c3 只重建分類 ③；ONLY=ch4 只重建第 4 章
    steps = []
    if not only or only == 'ch3':
        steps.append(('第 3 章總覽', lambda: pages_ch.build_ch3(CATS, pager_for('ch3_data.html'))))
    for i, fn in enumerate(builders):
        if only and only != CATS[i][0]:
            continue
        path = f'tables/{CATS[i][0]}.html'
        steps.append((f'分類 {CIRCLED[i]}', lambda fn=fn, i=i, path=path: fn(CATS[i], pager_for(path))))
    if not only or only == 'ch4':
        steps.append(('第 4 章', lambda: pages_ch.build_ch4(pager_for('ch4_postprocessing.html'))))
    for name, fn in steps:
        t = time.time()
        fn()
        print(f'{name:12s} 完成  {time.time() - t:5.1f} s')
    print(f'全部完成 {time.time() - t0:.1f} s → {SITE}')


if __name__ == '__main__':
    main()
