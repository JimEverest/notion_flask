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
    elif 256 <= h <= 290:
        return "purple"
    elif 291 <= h <= 344:
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
