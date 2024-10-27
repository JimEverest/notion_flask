# app/notion_parser.py

from notion_client import Client
from bs4 import BeautifulSoup
import json

# 加载配置
config = {}
with open('app/config/config.json') as config_file:
    config = json.load(config_file)

# 初始化 Notion 客户端
notion = Client(auth=config['notion_token'])

def get_page_ids():
    pages = config.get("pages", [])
    page_ids = [page.get("page_id") for page in pages if page.get("page_id")]
    return page_ids

page_ids = get_page_ids()

def get_page_title(page_id):
    try:
        page = notion.pages.retrieve(page_id=page_id)
        properties = page.get('properties', {})
        title_property = properties.get('title', {}).get('title', [])
        page_title = ''.join([t['plain_text'] for t in title_property]) if title_property else 'Untitled'
        return page_title
    except Exception as e:
        print(f"Error fetching title for page {page_id}: {e}")
        return 'Untitled'

def get_page_tree():
    pages = []
    for root_page_id in page_ids:
        page_title = get_page_title(root_page_id)
        root_page = {
            'id': root_page_id,
            'name': page_title,
            'has_children': True  # 假设根页面都有子页面
        }
        pages.append(root_page)
    return pages


# def get_page_tree():
#     def fetch_children(page_id):
#         try:
#             children = notion.blocks.children.list(block_id=page_id)['results']
#         except Exception as e:
#             print(f"Error fetching children for page {page_id}: {e}")
#             return []
#         pages = []
#         for child in children:
#             if child['type'] == 'child_page':
#                 page = {
#                     'id': child['id'],
#                     'name': child['child_page']['title'],
#                     'children': fetch_children(child['id'])
#                 }
#                 pages.append(page)
#         return pages

#     page_tree = []
#     for root_page_id in page_ids:
#         page_title = get_page_title(root_page_id)
#         root_page = {
#             'id': root_page_id,
#             'name': page_title,
#             'children': fetch_children(root_page_id)
#         }
#         page_tree.append(root_page)
#     return page_tree

def get_block_content(block_id):
    content = ''
    try:
        children = notion.blocks.children.list(block_id=block_id)['results']
        for block in children:
            content += parse_block(block)
    except Exception as e:
        content += f'<p>[Error fetching block content: {e}]</p>'
    return content

def parse_block(block):
    block_type = block['type']
    block_id = block['id']
    content = ''

    if block_type == 'paragraph':
        text = rich_text_to_html(block['paragraph']['rich_text'])
        content += f'<p data-notion-block-type="paragraph" data-notion-block-id="{block_id}">{text}</p>'

    elif block_type == 'heading_1':
        text = rich_text_to_html(block['heading_1']['rich_text'])
        content += f'<h1 data-notion-block-type="heading_1" data-notion-block-id="{block_id}">{text}</h1>'

    elif block_type == 'heading_2':
        text = rich_text_to_html(block['heading_2']['rich_text'])
        content += f'<h2 data-notion-block-type="heading_2" data-notion-block-id="{block_id}">{text}</h2>'

    elif block_type == 'heading_3':
        text = rich_text_to_html(block['heading_3']['rich_text'])
        content += f'<h3 data-notion-block-type="heading_3" data-notion-block-id="{block_id}">{text}</h3>'

    elif block_type == 'bulleted_list_item':
        text = rich_text_to_html(block['bulleted_list_item']['rich_text'])
        content += f'<ul data-notion-block-type="bulleted_list" data-notion-block-id="{block_id}"><li>{text}</li></ul>'

    elif block_type == 'numbered_list_item':
        text = rich_text_to_html(block['numbered_list_item']['rich_text'])
        content += f'<ol data-notion-block-type="numbered_list" data-notion-block-id="{block_id}"><li>{text}</li></ol>'

    elif block_type == 'to_do':
        text = rich_text_to_html(block['to_do']['rich_text'])
        checked = block['to_do']['checked']
        checkbox = '<input type="checkbox" disabled' + (' checked' if checked else '') + '>'
        content += f'<div data-notion-block-type="to_do" data-notion-block-id="{block_id}">{checkbox} {text}</div>'

    elif block_type == 'divider':
        content += f'<hr data-notion-block-type="divider" data-notion-block-id="{block_id}"/>'

    elif block_type == 'image':
        image_url = block['image'].get('file', {}).get('url', '') or block['image'].get('external', {}).get('url', '')
        caption = rich_text_to_html(block['image'].get('caption', []))
        content += f'<figure data-notion-block-type="image" data-notion-block-id="{block_id}"><img src="{image_url}" alt="{caption}"/><figcaption>{caption}</figcaption></figure>'

    # elif block_type == 'callout':
    #     text = rich_text_to_html(block['callout']['rich_text'])
    #     icon = block['callout'].get('icon', {}).get('emoji', '')
    #     content += f'<div class="callout" data-notion-block-type="callout" data-notion-block-id="{block_id}">{icon} {text}</div>'

    elif block_type == 'callout':
        text = rich_text_to_html(block['callout']['rich_text'])
        icon = block['callout'].get('icon', {}).get('emoji', '')
        content += f'<div class="callout" data-notion-block-type="callout" data-notion-block-id="{block_id}">{icon} {text}'

        # 处理子块（如果有）
        if block['has_children']:
            children = notion.blocks.children.list(block_id=block_id)['results']
            for child in children:
                content += parse_block(child)
        content += '</div>'
        
    elif block_type == 'code':
        code_text = ''.join([t['plain_text'] for t in block['code']['rich_text']])
        language = block['code'].get('language', '').lower()
        code_text_escaped = code_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        content += f'<pre data-notion-block-type="code" data-notion-block-id="{block_id}"><code class="language-{language}">{code_text_escaped}</code></pre>'

    elif block_type == 'file':
        file_info = block['file']
        file_url = file_info.get('file', {}).get('url', '') or file_info.get('external', {}).get('url', '')
        file_name = file_info.get('name', 'Download File')
        content += f'<p data-notion-block-type="file" data-notion-block-id="{block_id}"><a href="{file_url}" download="{file_name}">{file_name}</a></p>'

    elif block_type == 'bookmark':
        url = block['bookmark']['url']
        caption = rich_text_to_html(block['bookmark'].get('caption', []))
        display_text = caption if caption else url
        content += f'<p data-notion-block-type="bookmark" data-notion-block-id="{block_id}"><a href="{url}">{display_text}</a></p>'

    elif block_type == 'link_preview':
        url = block['link_preview']['url']
        content += f'<p data-notion-block-type="link_preview" data-notion-block-id="{block_id}"><a href="{url}">{url}</a></p>'

    elif block_type == 'link_to_page':
        link_type = block['link_to_page']['type']
        if link_type == 'page_id':
            linked_page_id = block['link_to_page']['page_id']
            page_title = get_page_title(linked_page_id)
            page_url = f"/page/{linked_page_id}"
            content += f'<p data-notion-block-type="link_to_page" data-notion-block-id="{block_id}"><a href="{page_url}">{page_title}</a></p>'
        else:
            content += f'<p data-notion-block-type="link_to_page" data-notion-block-id="{block_id}">[Unsupported link type]</p>'

    elif block_type == 'table':
        table_info = block['table']
        has_column_header = table_info['has_column_header']
        content += f'<table data-notion-block-type="table" data-notion-block-id="{block_id}">'
        table_rows = notion.blocks.children.list(block_id=block_id)['results']
        for idx, row_block in enumerate(table_rows):
            if row_block['type'] == 'table_row':
                cells = row_block['table_row']['cells']
                row_tag = 'th' if has_column_header and idx == 0 else 'td'
                content += '<tr>'
                for cell in cells:
                    cell_content = rich_text_to_html(cell)
                    content += f'<{row_tag}>{cell_content}</{row_tag}>'
                content += '</tr>'
        content += '</table>'

    elif block_type == 'toggle':
        title = rich_text_to_html(block['toggle']['rich_text'])
        content += f'<details data-notion-block-type="toggle" data-notion-block-id="{block_id}"><summary>{title}</summary>'
        if block['has_children']:
            children = notion.blocks.children.list(block_id=block_id)['results']
            for child in children:
                content += parse_block(child)
        content += '</details>'

    elif block_type == 'audio':
        audio_info = block['audio']
        audio_url = audio_info.get('file', {}).get('url', '') or audio_info.get('external', {}).get('url', '')
        content += f'<audio controls data-notion-block-type="audio" data-notion-block-id="{block_id}"><source src="{audio_url}">Your browser does not support the audio element.</audio>'

    elif block_type == 'child_page':
        page_title = block['child_page']['title']
        page_url = f"/page/{block_id}"
        content += f'<p data-notion-block-type="child_page" data-notion-block-id="{block_id}"><a href="{page_url}">{page_title}</a></p>'

    else:
        content += f'<p data-notion-block-type="{block_type}" data-notion-block-id="{block_id}">[Unsupported block type: {block_type}]</p>'

    return content

def rich_text_to_html(rich_text_array):
    html_content = ''
    for text_obj in rich_text_array:
        annotations = text_obj.get('annotations', {})
        plain_text = text_obj.get('plain_text', '')
        href = text_obj.get('href')

        text = plain_text
        if annotations.get('bold'):
            text = f'<strong>{text}</strong>'
        if annotations.get('italic'):
            text = f'<em>{text}</em>'
        if annotations.get('underline'):
            text = f'<u>{text}</u>'
        if annotations.get('strikethrough'):
            text = f'<s>{text}</s>'
        if annotations.get('code'):
            text = f'<code>{text}</code>'
        if href:
            text = f'<a href="{href}">{text}</a>'
        html_content += text
    return html_content

def html_to_notion_blocks(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    blocks = []
    for element in soup.find_all(recursive=False):
        block = element_to_notion_block(element)
        if block:
            blocks.append(block)
    return blocks

def element_to_notion_block(element):
    block_type = element.get('data-notion-block-type', 'paragraph')

    if block_type == 'paragraph':
        return {
            "type": "paragraph",
            "paragraph": {
                "rich_text": html_to_rich_text(element)
            }
        }

    elif block_type == 'heading_1':
        return {
            "type": "heading_1",
            "heading_1": {
                "rich_text": html_to_rich_text(element)
            }
        }

    elif block_type == 'heading_2':
        return {
            "type": "heading_2",
            "heading_2": {
                "rich_text": html_to_rich_text(element)
            }
        }

    elif block_type == 'heading_3':
        return {
            "type": "heading_3",
            "heading_3": {
                "rich_text": html_to_rich_text(element)
            }
        }

    elif block_type == 'bulleted_list':
        return list_element_to_notion_block(element, 'bulleted_list_item')

    elif block_type == 'numbered_list':
        return list_element_to_notion_block(element, 'numbered_list_item')

    elif block_type == 'to_do':
        checkbox = element.find('input', {'type': 'checkbox'})
        checked = checkbox.has_attr('checked') if checkbox else False
        return {
            "type": "to_do",
            "to_do": {
                "rich_text": html_to_rich_text(element),
                "checked": checked
            }
        }

    elif block_type == 'divider':
        return {
            "type": "divider",
            "divider": {}
        }

    elif block_type == 'image':
        img_tag = element.find('img')
        if img_tag:
            image_url = img_tag.get('src')
            caption = element.find('figcaption').get_text() if element.find('figcaption') else ''
            return {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {
                        "url": image_url
                    },
                    "caption": [{
                        "type": "text",
                        "text": {
                            "content": caption
                        }
                    }]
                }
            }

    # elif block_type == 'callout':
    #     text = html_to_rich_text(element)
    #     return {
    #         "type": "callout",
    #         "callout": {
    #             "rich_text": text,
    #             "icon": {
    #                 "type": "emoji",
    #                 "emoji": "ℹ️"
    #             }
    #         }
    #     }

    elif block_type == 'callout':
        text = html_to_rich_text(element)
        block = {
            "type": "callout",
            "callout": {
                "rich_text": text,
                "icon": {
                    "type": "emoji",
                    "emoji": "ℹ️"  # 默认图标，或根据需要调整
                }
            },
            "children": []
        }
        # 处理子元素
        for child_element in element.find_all(recursive=False):
            if child_element.name != 'span' and child_element != element.contents[0]:
                child_block = element_to_notion_block(child_element)
                if child_block:
                    block["children"].append(child_block)
        return block
        
    elif block_type == 'code':
        code_element = element.find('code')
        code_text = code_element.get_text() if code_element else ''
        language_class = code_element.get('class', [])
        language = ''
        if language_class:
            language = language_class[0].replace('language-', '')
        return {
            "type": "code",
            "code": {
                "rich_text": [{
                    "type": "text",
                    "text": {
                        "content": code_text
                    }
                }],
                "language": language
            }
        }

    elif block_type == 'file':
        a_tag = element.find('a')
        file_url = a_tag.get('href') if a_tag else ''
        file_name = a_tag.get_text() if a_tag else ''
        return {
            "type": "file",
            "file": {
                "type": "external",
                "external": {
                    "url": file_url
                },
                "caption": [{
                    "type": "text",
                    "text": {
                        "content": file_name
                    }
                }]
            }
        }

    elif block_type == 'bookmark':
        a_tag = element.find('a')
        url = a_tag.get('href') if a_tag else ''
        caption = a_tag.get_text() if a_tag else ''
        return {
            "type": "bookmark",
            "bookmark": {
                "url": url,
                "caption": [{
                    "type": "text",
                    "text": {
                        "content": caption
                    }
                }]
            }
        }

    elif block_type == 'link_preview':
        a_tag = element.find('a')
        url = a_tag.get('href') if a_tag else ''
        return {
            "type": "link_preview",
            "link_preview": {
                "url": url
            }
        }

    elif block_type == 'link_to_page':
        a_tag = element.find('a')
        page_id = a_tag.get('href').split('/page/')[1] if a_tag else ''
        return {
            "type": "link_to_page",
            "link_to_page": {
                "type": "page_id",
                "page_id": page_id
            }
        }

    elif block_type == 'toggle':
        summary = element.find('summary')
        title_text = summary.get_text() if summary else ''
        block = {
            "type": "toggle",
            "toggle": {
                "rich_text": html_to_rich_text(summary)
            },
            "children": []
        }
        # 处理子元素
        for child_element in element.find_all(recursive=False):
            if child_element != summary:
                child_block = element_to_notion_block(child_element)
                if child_block:
                    block["children"].append(child_block)
        return block

    elif block_type == 'audio':
        source_tag = element.find('source')
        audio_url = source_tag.get('src') if source_tag else ''
        return {
            "type": "audio",
            "audio": {
                "type": "external",
                "external": {
                    "url": audio_url
                }
            }
        }

    elif block_type == 'child_page':
        # Notion API 不允许通过 API 创建子页面，这里返回 None 或根据需求处理
        return None

    else:
        return None

def html_to_rich_text(element):
    rich_text = []
    for content in element.contents:
        if isinstance(content, str):
            if content.strip():
                rich_text.append({
                    "type": "text",
                    "text": {
                        "content": content.strip()
                    }
                })
        elif content.name == 'strong' or content.name == 'b':
            text = content.get_text()
            rich_text.append({
                "type": "text",
                "text": {
                    "content": text
                },
                "annotations": {
                    "bold": True
                }
            })
        elif content.name == 'em' or content.name == 'i':
            text = content.get_text()
            rich_text.append({
                "type": "text",
                "text": {
                    "content": text
                },
                "annotations": {
                    "italic": True
                }
            })
        elif content.name == 'u':
            text = content.get_text()
            rich_text.append({
                "type": "text",
                "text": {
                    "content": text
                },
                "annotations": {
                    "underline": True
                }
            })
        elif content.name == 's':
            text = content.get_text()
            rich_text.append({
                "type": "text",
                "text": {
                    "content": text
                },
                "annotations": {
                    "strikethrough": True
                }
            })
        elif content.name == 'code':
            text = content.get_text()
            rich_text.append({
                "type": "text",
                "text": {
                    "content": text
                },
                "annotations": {
                    "code": True
                }
            })
        elif content.name == 'a':
            text = content.get_text()
            href = content.get('href')
            rich_text.append({
                "type": "text",
                "text": {
                    "content": text,
                    "link": {
                        "url": href
                    }
                }
            })
        else:
            # 递归处理其他标签
            rich_text.extend(html_to_rich_text(content))
    return rich_text

def list_element_to_notion_block(element, list_type):
    items = element.find_all('li', recursive=False)
    blocks = []
    for item in items:
        text = html_to_rich_text(item)
        block = {
            "type": list_type,
            list_type: {
                "rich_text": text
            },
            "children": []
        }
        # 检查是否有嵌套列表
        for child in item.find_all(recursive=False):
            if child.name in ['ul', 'ol']:
                child_blocks = list_element_to_notion_block(
                    child,
                    'bulleted_list_item' if child.name == 'ul' else 'numbered_list_item'
                )
                block['children'].extend(child_blocks)
        blocks.append(block)
    return blocks
