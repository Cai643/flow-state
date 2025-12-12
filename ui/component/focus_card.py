import os
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def draw_card2(focus_pct=72, delta_pct=8, streak_minutes=45, rest_minutes=5, save_path=None, show=False):
    plt.rcParams["font.family"] = ["Segoe UI Emoji", "Microsoft YaHei", "SimHei"]
    # 修改处：减小 figsize (尺寸)，增加 dpi (清晰度)
    fig, ax = plt.subplots(figsize=(2.3, 1.5), dpi=400)
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_position([0, 0, 1, 1])
    fig.patch.set_alpha(0)
    fig.set_facecolor("none")
    card = FancyBboxPatch((0.03, 0.06), 0.94, 0.88, boxstyle="round,pad=0.03,rounding_size=0.08", linewidth=0, facecolor="#2b2b2b")
    ax.add_patch(card)
    green = "#00E676"
    text = "#DDDDDD"
    y1, y2, y3 = 0.72, 0.49, 0.26
    lx = 0.08
    rx = 0.62
    ax.text(lx, y1, "🎯 今日专注度", color=text, fontsize=8, va="center")
    ax.text(rx, y1, f"{focus_pct}%", color=green, fontsize=9, fontweight="bold", va="center")
    ax.text(rx + 0.15, y1, f"↑{delta_pct}%", color="#00E676", fontsize=9, va="center")
    ax.text(lx, y2, "🌱 连续专注", color=text, fontsize=8, va="center")
    ax.text(rx, y2, f"{streak_minutes}分钟", color=text, fontsize=9, fontweight="bold", va="center")
    ax.text(lx, y3, "💡 建议:", color="#FFFFFE", fontsize=8, va="center")
    ax.text(lx + 0.52, y3, "休息", color=text, fontsize=9, va="center")
    ax.text(lx + 0.65, y3, f"{rest_minutes}分钟", color=green, fontsize=9, fontweight="bold", va="center")
    if save_path is None:
        save_path = os.path.join(os.getcwd(), "assets", "focus_card.png")
    
    # 确保目录存在
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    plt.savefig(save_path, dpi=150, bbox_inches="tight", pad_inches=0, transparent=True)
    if show:
        plt.show()


if __name__ == "__main__":
    path = os.path.join(os.getcwd(), "assets", "focus_card.png")
    draw_card2(save_path=path, show=False)
    try:
        os.startfile(path)
    except Exception:
        pass

