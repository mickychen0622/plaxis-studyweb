# Plaxis2D Simulation

PLAXIS 2D 學習網站（純靜態網頁，從 `index.html` 進入）。以光明抽蓄地下廠房 plan_e 模型為主線，共六章：

| 章 | 檔案 | 內容 | 產生方式 |
|---|---|---|---|
| — | `index.html` | 首頁、章節導覽 | 手寫 |
| 1 | `ch1_principle.html` | Principle of Numerical Simulation：有限元素、Step／Iteration、收斂、ΣMstage、互動迭代實驗室 | 手寫 |
| 2 | `ch2_preprocessing.html` | Input: Pre-Processing：GUI 截圖對照 Command（Commands runner）語法 | 手寫 |
| 3 | `ch3_data.html`、`tables/c1`–`c7.html` | Data Structures：.p2dxdat 檔案、data.db 37 張表 | `tools/build_site.py` |
| 4 | `ch4_postprocessing.html` | Post-Processing：Python 讀取 data.db、作圖（fig_style） | `tools/build_site.py` |
| 5 | `ch5_mohrcoulomb.html` | Material Model – Mohr-Coulomb＋互動元素試驗室 | 手寫 |
| 6 | `ch6_pm4sand.html` | Material Model – PM4Sand＋互動循環單剪試驗室 | 手寫 |

- `assets/common.js`：左側章節導覽（章名清單在 `SITE.chapters`）、深淺色、KaTeX 數學式、程式碼上色（Python／SQL／PLAXIS Command）
- `assets/style.css`：共用樣式；`assets/img/ch1`–`ch6`：各章圖片
- `files/`：`KuanMing_plan_e7.txt`（完整建模指令）、`plx_common.py`（讀取共用開頭）、`fig_style.py`（作圖規範）
- `PLAXIS學習筆記.html`：舊版單頁筆記，內容已併入第 1、5 章，保留備查

## 重新產生第 3、4 章

網頁內容（筆數、查詢結果、Python 執行結果、圖）都是產生器實際查詢 data.db、實際執行範例程式得到的。資料庫以唯讀方式開啟，不會被修改。

```powershell
cd tools
python build_site.py "E:\01地下電廠洞室開挖支撐設計分析\KuanMing_Plaxis2D\KuanMing_plan_e\e5_TC289_NearMesh\e5_TC289_NearMesh.p2dxdat\data.db"
$env:ONLY = "ch4"; python build_site.py "…\data.db"   # 只重建第 4 章（ch3、c1–c7 同理）
```

範例裡寫死的編號（例如區塊 336、K_Steps.ID 40、量測點座標）是以 `e5_TC289_NearMesh` 為準；換成別的模型時，這幾處要跟著改。
