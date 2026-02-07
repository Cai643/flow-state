import os
from PIL import Image, ImageDraw

# 1. 设置路径
script_dir = os.path.dirname(os.path.abspath(__file__))
img_path = os.path.join(script_dir, "App icon.png") 

if not os.path.exists(img_path):
    print(f"Error: 文件不存在: {img_path}")
    exit(1)

print(f"正在处理图片: {img_path}")
img = Image.open(img_path).convert("RGBA")
width, height = img.size

# 2. 创建遮罩
mask = Image.new('L', (width, height), 0)
draw = ImageDraw.Draw(mask)

# --- 调整圆的大小 ---
# 用户指定使用 0.85
scale_ratio = 0.85

print(f"使用缩放比例: {scale_ratio}")

center_x, center_y = width / 2, height / 2
radius_x = (width / 2) * scale_ratio
radius_y = (height / 2) * scale_ratio

# 计算圆的边界框
bbox = (center_x - radius_x, center_y - radius_y, 
        center_x + radius_x, center_y + radius_y)

# 画圆 (白色表示保留)
draw.ellipse(bbox, fill=255, outline=255)

# 3. 应用遮罩
img.putalpha(mask)

# 4. 关键步骤：裁剪 (Crop)
img = img.crop(bbox)

# 5. 保存预览图
preview_path = os.path.join(script_dir, "preview_final.png")
img.save(preview_path)
print(f"已生成预览图: {preview_path}")

# 6. 保存为 ICO
# 直接覆盖 App icon.ico，这样打包时会自动使用新图标
icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
save_path = os.path.join(script_dir, "App icon.ico")
img.save(save_path, format="ICO", sizes=icon_sizes)

print(f"成功！已生成图标: {save_path}")
print("您可以直接运行 pyinstaller FlowState.spec 进行打包。")
