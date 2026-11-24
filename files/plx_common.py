"""PLAXIS data.db 共用開頭：唯讀連線、BLOB 解碼、常用小函式。

用法：把這個檔案放在你的程式旁邊，然後 from plx_common import *
換別的 data.db 時，只要改下面的 DB 路徑。
"""
import sqlite3
import numpy as np

DB = r'E:\01地下電廠洞室開挖支撐設計分析\KuanMing_Plaxis2D\KuanMing_plan_e\e5_TC289_NearMesh\e5_TC289_NearMesh.p2dxdat\data.db'
con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)   # 唯讀開啟，不會改到檔案

# DataInterpretation.ID → numpy 的資料型別（< 代表 little-endian，位元組倒過來存）
DTYPE = {1: '<f4', 2: '<f8', 3: '<u1', 4: '<i1', 5: '<u2', 6: '<i2', 7: '<u4', 8: '<i4',
         9: '<u8', 10: '<i8', 11: '<u1', 12: 'S1', 13: '<u1',
         14: '<i8', 15: '<i8', 16: '<i8', 17: '<i8', 18: '<i8'}

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
