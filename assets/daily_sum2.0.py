import os
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

def draw_daily_sum(save_path=None, show=False):
    # 设置字体，确保支持 Emoji 和中文
    plt.rcParams["font.family"] = ["Segoe UI Emoji", "Microsoft YaHei", "SimHei"]
    
    # 设置画布大小和分辨率 (根据引用图风格，采用宽长方形)
    # dpi=200 保证清晰度
    fig, ax = plt.subplots(figsize=(5.0, 3.2), dpi=200)
    
    # 关闭坐标轴
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    
    # 调整边距
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_position([0, 0, 1, 1])
    
    # 背景透明
    fig.patch.set_alpha(0)
    fig.set_facecolor("none")
    
    # 绘制深色圆角卡片背景
    # 颜色取自引用图背景色 #2b2b2b (深灰)
    bg_color = "#333333" # 稍微亮一点的深灰，增加层次感
    card = FancyBboxPatch(
        (0.02, 0.02), 0.96, 0.96,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=0,
        facecolor=bg_color
    )
    ax.add_patch(card)
    
    # 定义配色
    text_color = "#DDDDDD"       # 浅灰/白
    highlight_color = "#00E676"  # 亮绿色 (引用图风格)
    secondary_text = "#AAAAAA"   # 次要文字颜色
    
    # --- 1. 标题区域 ---
    # 顶部居中标题
    ax.text(0.5, 0.88, "🌟 今天又是努力的一天呢！", 
            color="#F1CB10", fontsize=14, fontweight="bold", 
            ha="center", va="center")
            
    # 分割线 (虚线或细实线)
    ax.plot([0.1, 0.9], [0.80, 0.80], color="#555555", linewidth=1, linestyle="-")
    
    # --- 2. 数据内容区域 ---
    # 定义行高
    start_y = 0.70
    line_gap = 0.12
    left_x = 0.12
    
    # 第一行: 专注时长
    ax.text(left_x, start_y, "专注时长:", color=text_color, fontsize=11, va="center")
    ax.text(left_x + 0.25, start_y, "5.2h", color=highlight_color, fontsize=13, fontweight="bold", va="center")
    ax.text(left_x + 0.45, start_y, "⬆️ +30min", color="#888888", fontsize=10, va="center")
    
    # 第二行: 分心次数
    ax.text(left_x, start_y - line_gap, "分心次数:", color=text_color, fontsize=11, va="center")
    ax.text(left_x + 0.25, start_y - line_gap, "7次", color=highlight_color, fontsize=13, fontweight="bold", va="center")
    ax.text(left_x + 0.45, start_y - line_gap, "😊 每次调整超快", color="#888888", fontsize=10, va="center")
    
    # 第三行: 最长专注
    ax.text(left_x, start_y - line_gap * 2, "最长专注:", color=text_color, fontsize=11, va="center")
    ax.text(left_x + 0.25, start_y - line_gap * 2, "92min", color=highlight_color, fontsize=13, fontweight="bold", va="center")
    ax.text(left_x + 0.45, start_y - line_gap * 2, "💪 心流状态！", color="#888888", fontsize=10, va="center")
    
    # 第四行: 休息达标
    ax.text(left_x, start_y - line_gap * 3, "休息达标:", color=text_color, fontsize=11, va="center")
    ax.text(left_x + 0.25, start_y - line_gap * 3, "85%", color=highlight_color, fontsize=13, fontweight="bold", va="center")
    ax.text(left_x + 0.45, start_y - line_gap * 3, "⭐ 五星好评！", color="#888888", fontsize=10, va="center")
    
    # 分割线
    ax.plot([0.1, 0.9], [0.22, 0.22], color="#555555", linewidth=1, linestyle="-")
    
    # --- 3. 底部按钮区域 ---
    # 模拟按钮样式
    btn_y = 0.12
    
    # 左按钮 [查看详细]
    btn1_x = 0.3
    ax.text(btn1_x, btn_y, "[ 查看详细 ]", color=highlight_color, fontsize=10, 
            ha="center", va="center", fontweight="bold")
            
    # 右按钮 [分享成就]
    btn2_x = 0.7
    ax.text(btn2_x, btn_y, "[ 分享成就 ]", color=highlight_color, fontsize=10, 
            ha="center", va="center", fontweight="bold")

    # 保存路径
    if save_path is None:
        save_path = os.path.join(os.getcwd(), "assets", "daily_sum_card.png")
    
    # 确保目录存在
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    plt.savefig(save_path, dpi=200, bbox_inches="tight", pad_inches=0, transparent=True)
    
    if show:
        plt.show()
    
    plt.close(fig)
    print(f"Daily summary card generated at: {save_path}")

if __name__ == "__main__":
    # 测试生成
    assets_dir = os.path.join(os.getcwd(), "assets")
    if not os.path.exists(assets_dir):
        # 如果当前工作目录不是项目根目录，尝试向上查找
        if os.path.basename(os.getcwd()) == "component":
             assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())), "assets")
    
    path = os.path.join(assets_dir, "daily_sum_card.png")
    draw_daily_sum(save_path=path, show=False)
    try:
        os.startfile(path)
    except Exception:
        pass
