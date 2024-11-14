import re

def parse_hsl(hsl_str):
    """
    解析 HSL 字符串，返回 (h, s, l)
    支持带或不带分号，并允许各部分有可选空格。
    """
    # 优化后的正则表达式：
    # - \s* 匹配可选的空格
    # - (\d+(?:\.\d+)?) 匹配整数或浮点数
    pattern = r'hsl\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)%\s*,\s*(\d+(?:\.\d+)?)%\s*\)\s*;?'
    
    match = re.match(pattern, hsl_str.strip(), re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid HSL format: {hsl_str}")
    
    h, s, l = match.groups()
    
    # 转换为浮点数，然后根据需要转换为整数
    h = float(h) % 360  # 确保色相在0-359之间
    s = float(s)
    l = float(l)
    
    return h, s, l

def hsl_to_color_name(h, s, l):
    """
    根据 HSL 值映射到指定的颜色名称
    """
    if s < 10:
        return "gray"
    
    if 20 <= h <= 40 and s >= 30 and l <= 50:
        return "brown"
    
    if (0 <= h <= 15) or (345 <= h <= 360):
        return "red"
    elif 16 <= h <= 45:
        return "orange"
    elif 46 <= h <= 65:
        return "yellow"
    elif 66 <= h <= 165:
        return "green"
    elif 166 <= h <= 255:
        return "blue"
    elif 256 <= h <= 310:
        return "purple"
    elif 322 <= h <= 344:
        return "pink"
    else:
        return "default"

def hsl_to_css_color_name_notion(hsl_str):
    """
    将 HSL 字符串转换为指定的 CSS 颜色名称
    """
    try:
        h, s, l = parse_hsl(hsl_str)
        color_name = hsl_to_color_name(h, s, l)
        return color_name
    except Exception as e:
        return "default"


def parse_hex(hex_str):
    """
    解析十六进制颜色字符串，返回 (r, g, b)
    支持 #rgb 和 #rrggbb 格式
    """
    hex_str = hex_str.strip().lower()
    pattern = r'^#([0-9a-f]{3}|[0-9a-f]{6})$'
    match = re.match(pattern, hex_str)
    if not match:
        raise ValueError(f"Invalid hex color format: {hex_str}")
    
    hex_value = match.group(1)
    if len(hex_value) == 3:
        # 扩展为6位
        hex_value = ''.join([c*2 for c in hex_value])
    
    r = int(hex_value[0:2], 16)
    g = int(hex_value[2:4], 16)
    b = int(hex_value[4:6], 16)
    
    return r, g, b


def rgb_to_hsl(r, g, b):
    """
    将 RGB 值转换为 HSL
    r, g, b: 0-255
    返回 h, s, l，其中：
        h: 0-360
        s: 0-100
        l: 0-100
    """
    r /= 255
    g /= 255
    b /= 255
    
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    l = (max_val + min_val) / 2
    
    if max_val == min_val:
        h = s = 0  # 无色
    else:
        d = max_val - min_val
        s = d / (2 - max_val - min_val) if l > 0.5 else d / (max_val + min_val)
        
        if max_val == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif max_val == g:
            h = (b - r) / d + 2
        elif max_val == b:
            h = (r - g) / d + 4
        h /= 6
    
    h_deg = round(h * 360)
    s_pct = round(s * 100)
    l_pct = round(l * 100)
    
    return h_deg % 360, s_pct, l_pct

def hex_to_css_color_name_limited(hex_str):
    """
    将十六进制颜色字符串转换为指定的 CSS 颜色名称
    """
    try:
        r, g, b = parse_hex(hex_str)
        h, s, l = rgb_to_hsl(r, g, b)
        color_name = hsl_to_color_name(h, s, l)
        return color_name
    except Exception:
        return "default"








# # 示例用法
# if __name__ == "__main__":
#     test_cases = [
#         "hsl(150, 75%, 60%);",  # green
#         "hsl(120, 75%, 60%);",  # green
#         "hsl(240, 75%, 60%);",  # blue
#         "hsl(0, 75%, 60%);",    # red
#         "hsl(180, 75%, 60%);",  # blue
#         "hsl(210, 75%, 60%);",  # blue
#         "hsl(0, 0%, 0%);",       # gray
#         "hsl(0, 0%, 30%);",      # gray
#         "hsl(0, 0%, 100%);",     # gray
#         "hsl(30, 50%, 40%);",    # brown
#         "hsl(30, 80%, 50%);",    # orange
#         "hsl(60, 100%, 50%);",   # yellow
#         "hsl(300, 100%, 70%);",  # pink
#         "hsl(270, 50%, 40%);",   # purple
#         "hsl(200, 30%, 20%);",   # blue
#         "hsl(0, 0%, 50%);",      # gray
#         "hsl(360, 100%, 50%);"   # red
#     ]

#     for hsl in test_cases:
#         color_name = hsl_to_css_color_name_notion(hsl)
#         print(f"{hsl} --> {color_name}")
