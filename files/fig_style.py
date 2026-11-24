"""結案報告所有圖共用的格式（以圖 4-4 C_kaf 掃描的樣式為準）。

- 圖寬 = 插入 Word 的寬度（width_in(cm)），以 1:1 繪製，各圖的字級才會一致。
- 字型 Times New Roman ＋ 標楷體；座標軸數字與標籤 10 pt、圖例 9 pt。
- 顏色依序使用 黑 → 藍 → 紅（COLORS），第四種以後用灰色；實測一律黑色、OpenSees 藍色、PLAXIS 紅色；
  三案 RPI_A 黑、RPI_B 藍、UCD_6 紅。
- 四邊框線、刻度朝內、上右兩側也有刻度；不畫格線；圖例無外框。
- 中文字串裡不要用 $…$（mathtext 沒有中文字型），下標直接寫 hp0、σ′v0、ru。

用法：import fig_style as S; S.apply(); fig, ax = plt.subplots(figsize=(S.width_in(11), 3.0)); S.frame(ax)
"""
import matplotlib as mpl

BLACK, BLUE, RED, GRAY, LIGHT = "#000000", "#1F5FA8", "#C0392B", "#8C8C8C", "#D9D9D9"
COLORS = [BLACK, BLUE, RED, GRAY]
CASE_COLOR = {"RPI_A": BLACK, "RPI_B": BLUE, "UCD_6": RED}
SRC_COLOR = {"meas": BLACK, "ops": BLUE, "plx": RED}
FS, FS_LEGEND = 10, 9


def width_in(cm):
    return cm / 2.54


def apply():
    mpl.rcParams.update({
        "font.family": ["Times New Roman", "DFKai-SB"], "mathtext.fontset": "stix",
        "axes.unicode_minus": False, "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
        "xtick.labelsize": FS, "ytick.labelsize": FS, "legend.fontsize": FS_LEGEND,
        "axes.linewidth": 0.8, "axes.edgecolor": BLACK, "text.color": BLACK, "axes.labelcolor": BLACK,
        "xtick.color": BLACK, "ytick.color": BLACK, "xtick.direction": "in", "ytick.direction": "in",
        "xtick.top": True, "ytick.right": True, "axes.grid": False,
        "axes.prop_cycle": mpl.cycler(color=COLORS),
        "lines.linewidth": 1.0, "lines.markersize": 4.5,
        "legend.frameon": False, "savefig.dpi": 300, "savefig.facecolor": "white",
        "image.cmap": "Blues",
    })


def frame(ax):
    for s in ax.spines.values():
        s.set_color(BLACK)
        s.set_linewidth(0.8)
    ax.grid(False)
    ax.tick_params(top=True, right=True, direction="in")
