import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
import numpy as np

# --- 配置与样式 ---
plt.rcParams['font.sans-serif'] = ['SimHei', 'Segoe UI Emoji', 'Microsoft YaHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

STYLE = {
    'bg_color': "#3A3939",       # 主背景（深色）
    'card_color': "#454444",     # 卡片背景（比主背景稍亮）
    'text_white': '#FFFFFF',
    'text_gray': '#AAAAAA',
    'accent_green': '#00FF7F',   # 荧光绿
    'accent_yellow': '#FFD700',  # 金色
    'rose_light': '#00FF7F',
    'rose_dark': '#2E8B57',
    'rose_dim': '#3A5A4A'        # 暗绿色（用于低值扇区）
}

def create_daily_summary():
    # 1. 设置透明背景的图表
    fig = plt.figure(figsize=(14, 8.5))
    fig.patch.set_alpha(0.0) # 透明图表背景

    # 2. 绘制带圆角的主背景
    ax_bg = fig.add_axes([0, 0, 1, 1], zorder=-1)
    ax_bg.set_axis_off()
    ax_bg.set_xlim(0, 1)
    ax_bg.set_ylim(0, 1)
    
    bg_rect = patches.FancyBboxPatch(
        (0.0, 0.0), 1.0, 1.0,
        boxstyle="Round,pad=0,rounding_size=0.05",
        linewidth=0,
        facecolor=STYLE['bg_color'],
        transform=ax_bg.transAxes,
        mutation_scale=1
    )
    ax_bg.add_patch(bg_rect)

    # 3. 布局网格
    gs = gridspec.GridSpec(3, 1, height_ratios=[1.2, 4, 1.2], hspace=0.25)
    gs.update(left=0.05, right=0.95, top=0.92, bottom=0.08)

    # --- 顶部横幅 ---
    ax_top = fig.add_subplot(gs[0])
    draw_top_banner(ax_top)

    # --- 中间部分 ---
    gs_mid = gridspec.GridSpecFromSubplotSpec(1, 4, subplot_spec=gs[1], 
                                            width_ratios=[1, 1, 1, 2.2], wspace=0.15)
    
    ax_c1 = fig.add_subplot(gs_mid[0])
    draw_metric_card(ax_c1, "专注时长", "6.2h", "↑ +1.2h", value_fontsize=35, fontweight='heavy')

    ax_c2 = fig.add_subplot(gs_mid[1])
    draw_metric_card(ax_c2, "最佳时段", "14-16点", "效率峰值", value_fontsize=35)

    ax_c3 = fig.add_subplot(gs_mid[2])
    draw_metric_card(ax_c3, "健康提醒", "响应3次", "休息达标✓", value_fontsize=35)

    ax_rose = fig.add_subplot(gs_mid[3], projection='polar')
    draw_rose_chart(ax_rose)

    # --- 底部洞察 ---
    ax_bot = fig.add_subplot(gs[2])
    draw_bottom_insights(ax_bot)

    # 保存
    import os
    output_dir = os.path.join(os.getcwd(), 'assets')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'daily_summary_report.png')
    plt.savefig(output_path, dpi=150, transparent=True)
    print(f"图表生成成功: {output_path}")

def clean_axis(ax):
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

def draw_rounded_panel(ax, rect_style=None):
    if rect_style is None:
        rect_style = dict(facecolor=STYLE['card_color'], edgecolor='none')
    
    panel = patches.FancyBboxPatch(
        (0, 0), 1, 1,
        boxstyle="Round,pad=-0.005,rounding_size=0.1",
        transform=ax.transAxes,
        mutation_scale=1,
        **rect_style
    )
    ax.add_patch(panel)

def draw_top_banner(ax):
    clean_axis(ax)
    draw_rounded_panel(ax)
    
    ax.text(0.31, 0.7, "🏆", 
            color=STYLE['accent_yellow'], fontsize=25, fontweight='heavy', 
            fontname='Segoe UI Emoji', ha='center', va='center')
    
    ax.text(0.53, 0.7, "今日达成 \"深度工作者\" 称号！", 
            color=STYLE['accent_yellow'], fontsize=25, fontweight='bold', 
            ha='center', va='center')
    
    ax.text(0.5, 0.40, "累计专注 6.2小时 | 效率比昨日提升 15%", 
            color=STYLE['text_white'], fontsize=20, 
            ha='center', va='center')
   # 按钮
    draw_button(ax, 0.35, 0.1, 0.14, 0.1, "[ 分享按钮 ]", color=STYLE['accent_green'])
    draw_button(ax, 0.51, 0.1, 0.14, 0.1, "[ 查看详情 ]", color=STYLE['text_gray'])

def draw_button(ax, x, y, width, height, text, color):
    """绘制圆角矩形按钮"""
    # 绘制按钮背景
    # 转换为数据坐标
    # 注意：这里我们简单用 text 绘制，或者用 FancyBboxPatch
    # 为了简单和对齐，我们直接用 text 的 bbox 参数
    
    # 使用 FancyBboxPatch 绘制背景
    # x, y 是左下角
    btn = patches.FancyBboxPatch(
        (x, y), width, height,
        boxstyle="Round,pad=0.02,rounding_size=0.04",
        linewidth=0,
        facecolor='#444444', # 按钮深色背景
        transform=ax.transAxes,
        mutation_scale=1,
        zorder=1
    )
    ax.add_patch(btn)
    
    # 绘制文本
    ax.text(x + width/2, y + height/2, text, 
            color=color, fontsize=10, fontweight='bold',
            ha='center', va='center', zorder=2)

def draw_metric_card(ax, title, value, sub, value_fontsize=24, fontweight='bold'):
    clean_axis(ax)
    draw_rounded_panel(ax)
    
    ax.text(0.5, 0.8, title, color=STYLE['text_gray'], fontsize=12, ha='center', va='center')
    ax.text(0.5, 0.5, value, color=STYLE['accent_green'], fontsize=value_fontsize, fontweight=fontweight, ha='center', va='center')
    
    if '✓' in sub:
        ax.text(0.45, 0.2, "休息达标", color=STYLE['accent_green'], fontsize=10, ha='center', va='center')
        ax.text(0.65, 0.2, "✓", color=STYLE['accent_green'], fontsize=10, fontname='Segoe UI Emoji', ha='center', va='center')
    else:
        ax.text(0.5, 0.2, sub, color=STYLE['accent_green'] if '+' in sub else STYLE['text_gray'], 
                fontsize=10, ha='center', va='center')

def draw_bottom_insights(ax):
    clean_axis(ax)
    draw_rounded_panel(ax)
    
    ax.text(0.04, 0.75, "💡", color=STYLE['accent_yellow'], fontsize=20, 
            fontname='Segoe UI Emoji', fontweight='bold', ha='left', va='center')
    ax.text(0.07, 0.75, "你的洞察:", color=STYLE['accent_yellow'], fontsize=20, fontweight='bold', ha='left', va='center')

    ax.text(0.05, 0.50, "•", color=STYLE['text_white'], fontsize=11, fontname='Segoe UI Emoji', ha='left', va='center')
    ax.text(0.08, 0.50, "上午10:00-11:00是代码高产期，建议安排重要任务", color=STYLE['text_white'], fontsize=11, ha='left', va='center')
    
    ax.text(0.05, 0.25, "•", color=STYLE['text_white'], fontsize=11, fontname='Segoe UI Emoji', ha='left', va='center')
    ax.text(0.08, 0.25, "连续工作52分钟时效率下降，下次45分钟时主动休息", color=STYLE['text_white'], fontsize=11, ha='left', va='center')

def draw_rose_chart(ax):
    ax.set_facecolor('none')
    
    # 模拟参考图的数据分布 (顺时针方向，从12点开始)
    # 我们需要调整角度，使它们对应时钟位置
    # Matplotlib polar 默认 0 度在 3 点钟方向，逆时针旋转
    # 我们需要手动映射
    
    # 定义6个主要扇区 (每个60度)
    # 为了产生间隙，我们让 width < 60度 (例如 50度)
    N = 6
    width = np.deg2rad(50) # 扇区宽度
    gap = np.deg2rad(10)   # 间隙
    
    # 角度设置：从 12点钟 (90度) 开始，顺时针 (-theta)
    # 为了方便，我们直接指定每个扇区的起始角度
    # 扇区1: 1-3点 (High) -> 30度到90度 (在polar里是 60度到0度?)
    # 让我们简单点，均匀分布6个，然后旋转整个图表让它看起来像
    
    # 设定6个扇区的中心角度 (0, 60, 120, 180, 240, 300)
    theta = np.linspace(0.0, 2 * np.pi, N, endpoint=False)
    
    # 调整 theta 让第一个扇区在右上方
    # theta += np.deg2rad(30)
    
    # 半径数据 (模拟图中的长短)
    # 顺序：右，右上，左上，左，左下，右下 (逆时针)
    # 参考图顺时针：
    # 1 (12-2点): 长 (Bright)
    # 2 (2-4点): 短 (Dim) -- 看起来像是内圈
    # 3 (4-6点): 长 (Bright)
    # 4 (6-8点): 中 (Bright)
    # 5 (8-10点): 短 (Dim) -- 看起来像是内圈
    # 6 (10-12点): 中 (Bright)
    
    # 映射到 matplotlib (逆时针, 0是3点钟)
    # 0度 (3点): 对应扇区2的一部分?
    # 让我们直接定义每个条的 (theta, radius, color)
    
    bars_data = [
        # (角度-弧度, 半径, 颜色)
        # 1. 右上 (12点-2点) -> 60度到90度附近 -> 75度中心
        (np.deg2rad(75), 4, STYLE['rose_light']),
        
        # 2. 右下 (2点-4点) -> 0度附近 (3点) -> 315度 (-45) 到 45度
        # 图中3点钟位置似乎是一个凹陷
        (np.deg2rad(15), 2.5, STYLE['rose_dim']), # 偏上一点
        (np.deg2rad(345), 2.5, STYLE['rose_dim']), # 偏下一点
        
        # 3. 右下/底 (4点-6点) -> 270度到330度 -> 300度中心 (-60)
        (np.deg2rad(285), 4.2, STYLE['rose_light']),
        
        # 4. 左下 (6点-8点) -> 210度到270度 -> 240度中心
        (np.deg2rad(225), 3.0, STYLE['rose_light']),
        
        # 5. 左上 (8点-10点) -> 150度到210度 -> 180度中心
        (np.deg2rad(165), 2.0, STYLE['rose_dim']), # 暗色，短
        
        # 6. 左上/顶 (10点-12点) -> 90度到150度 -> 120度中心
        (np.deg2rad(105), 3.5, STYLE['rose_light']),
    ]
    
    # 重新定义均匀的6个扇区来匹配整体感，更加整洁
    radii = [4.0, 3.5, 2.0, 3.0, 4.2, 2.5] 
    colors = [STYLE['rose_light'], STYLE['rose_light'], STYLE['rose_dim'], 
              STYLE['rose_light'], STYLE['rose_light'], STYLE['rose_dim']]
    
    # 旋转一下让它对齐
    ax.set_theta_offset(np.pi / 2) # 0度在12点方向
    ax.set_theta_direction(-1)     # 顺时针
    
    # 绘制扇区
    # bottom=1.5 制造中间的空洞 -> 增加到 1.6 以扩大中心圆
    ax.bar(theta, radii, width=width, bottom=1.6, color=colors, alpha=0.9, zorder=2)
    
    # 移除轴线
    ax.set_yticklabels([])
    ax.set_xticklabels([])
    ax.grid(False)
    ax.spines['polar'].set_visible(False)
    
    # 中心圆 (背景)
    # 增大填充半径到 1.6
    ax.fill_between(np.linspace(0, 2*np.pi, 100), 0, 1.6, color='#3A5A4A', alpha=0.3, zorder=1)
    
    # 中心标签
    # 字体加大 fontsize=16
    ax.text(0, 0, "有效产出\n78%", ha='center', va='center', color=STYLE['text_white'], fontsize=16, fontweight='bold', zorder=3)

if __name__ == "__main__":
    create_daily_summary()
