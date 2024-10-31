# app/notion_parser.py

from notion_client import Client
from bs4 import BeautifulSoup, NavigableString, Tag
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
        # 处理子块
        if block['has_children']:
            children = notion.blocks.children.list(block_id=block_id)['results']
            for child in children:
                content += parse_block(child)

    elif block_type == 'heading_1':
        text = rich_text_to_html(block['heading_1']['rich_text'])
        content += f'<h1 data-notion-block-type="heading_1" data-notion-block-id="{block_id}">{text}</h1>'
        if block['has_children']:
            children = notion.blocks.children.list(block_id=block_id)['results']
            for child in children:
                content += parse_block(child)

    elif block_type == 'heading_2':
        text = rich_text_to_html(block['heading_2']['rich_text'])
        content += f'<h2 data-notion-block-type="heading_2" data-notion-block-id="{block_id}">{text}</h2>'
        if block['has_children']:
            children = notion.blocks.children.list(block_id=block_id)['results']
            for child in children:
                content += parse_block(child)

    elif block_type == 'heading_3':
        text = rich_text_to_html(block['heading_3']['rich_text'])
        content += f'<h3 data-notion-block-type="heading_3" data-notion-block-id="{block_id}">{text}</h3>'
        if block['has_children']:
            children = notion.blocks.children.list(block_id=block_id)['results']
            for child in children:
                content += parse_block(child)

    elif block_type == 'bulleted_list_item':
        text = rich_text_to_html(block['bulleted_list_item']['rich_text'])
        content += f'<ul data-notion-block-type="bulleted_list" data-notion-block-id="{block_id}"><li>{text}'
        # 处理子块
        if block['has_children']:
            content += '<ul>'
            children = notion.blocks.children.list(block_id=block_id)['results']
            for child in children:
                content += parse_block(child)
            content += '</ul>'
        content += '</li></ul>'

    elif block_type == 'numbered_list_item':
        text = rich_text_to_html(block['numbered_list_item']['rich_text'])
        content += f'<ol data-notion-block-type="numbered_list" data-notion-block-id="{block_id}"><li>{text}'
        # 处理子块
        if block['has_children']:
            content += '<ol>'
            children = notion.blocks.children.list(block_id=block_id)['results']
            for child in children:
                content += parse_block(child)
            content += '</ol>'
        content += '</li></ol>'

    elif block_type == 'to_do':
        # 获取任务内容和完成状态
        text = rich_text_to_html(block['to_do']['rich_text'])
        checked = block['to_do']['checked']
        # 构建 CKEditor 的待办事项 HTML
        checkbox = f'<input type="checkbox" tabindex="-1" {"checked" if checked else ""}>'
        # 包装为 CKEditor 的待办事项格式
        content += f'''
        <ul class="todo-list" data-notion-block-type="to_do" data-notion-block-id="{block_id}">
            <li>
                <span class="todo-list__label">
                    <span contenteditable="false">{checkbox}</span>
                    <span class="todo-list__label__description">{text}</span>
                </span>
            </li>
        </ul>
        '''
        # 处理子块（如果有）
        if block['has_children']:
            children = notion.blocks.children.list(block_id=block_id)['results']
            for child in children:
                content += parse_block(child)

    elif block_type == 'divider':
        content += f'<hr data-notion-block-type="divider" data-notion-block-id="{block_id}"/>'

    elif block_type == 'image':
        image_url = block['image'].get('file', {}).get('url', '') or block['image'].get('external', {}).get('url', '')
        caption = rich_text_to_html(block['image'].get('caption', []))
        content += f'<figure data-notion-block-type="image" data-notion-block-id="{block_id}"><img src="{image_url}" alt="{caption}"/><figcaption>{caption}</figcaption></figure>'

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
        # 处理子块
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

    elif block_type == 'quote':
        text = rich_text_to_html(block['quote']['rich_text'])
        content += f'<blockquote data-notion-block-type="quote" data-notion-block-id="{block_id}">{text}</blockquote>'
        # 处理子块
        if block['has_children']:
            children = notion.blocks.children.list(block_id=block_id)['results']
            for child in children:
                content += parse_block(child)

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
    elements=soup.find_all(recursive=False)
    for element in soup.find_all(recursive=False):
        block = element_to_notion_block(element)
        
        # Check if block is a list
        if isinstance(block, list):
            for item in block:
                if isinstance(item, dict) and 'type' in item:  # Ensure each item in list has 'type'
                    blocks.append(item)
        
        # Check if block is an object with 'type' attribute
        elif isinstance(block, dict) and 'type' in block:
            blocks.append(block)
    
    return blocks

# def html_to_notion_blocks(html_content):
#     soup = BeautifulSoup(html_content, 'html.parser')
#     blocks = []
#     for element in soup.contents:
#         block = element_to_notion_block(element)
#         if block:
#             if isinstance(block, list):
#                 blocks.extend(block)
#             else:
#                 blocks.append(block)
#     return blocks
    

# def element_to_notion_block(element):
#     block_type = element.get('data-notion-block-type', 'paragraph')

#     if block_type == 'paragraph':
#         block = {
#             "type": "paragraph",
#             "paragraph": {
#                 "rich_text": html_to_rich_text(element)
#             }
#         }
#         # 处理子元素
#         children = []
#         for child_element in element.find_all(recursive=False):
#             child_block = element_to_notion_block(child_element)
#             if child_block:
#                 children.append(child_block)
#         if children:
#             block['has_children'] = True
#             block['children'] = children
#         return block

#     elif block_type == 'heading_1':
#         return {
#             "type": "heading_1",
#             "heading_1": {
#                 "rich_text": html_to_rich_text(element)
#             }
#         }

#     elif block_type == 'heading_2':
#         return {
#             "type": "heading_2",
#             "heading_2": {
#                 "rich_text": html_to_rich_text(element)
#             }
#         }

#     elif block_type == 'heading_3':
#         return {
#             "type": "heading_3",
#             "heading_3": {
#                 "rich_text": html_to_rich_text(element)
#             }
#         }

#     # elif block_type == 'bulleted_list':
#     #     return list_element_to_notion_block(element, 'bulleted_list_item')
#     elif block_type == 'bulleted_list':
#         items = element.find_all('li', recursive=False)
#         blocks = []
#         for item in items:
#             block = {
#                 "type": "bulleted_list_item",
#                 "bulleted_list_item": {
#                     "rich_text": html_to_rich_text(item)
#                 }
#             }
#             # 处理子元素
#             children_elements = item.find_all(['ul', 'ol'], recursive=False)
#             if children_elements:
#                 block['has_children'] = True
#                 block['children'] = []
#                 for child_element in children_elements:
#                     child_blocks = element_to_notion_block(child_element)
#                     if child_blocks:
#                         block['children'].extend(child_blocks)
#             blocks.append(block)
#         return blocks

#     elif block_type == 'numbered_list':
#         return list_element_to_notion_block(element, 'numbered_list_item')

#     elif element.name == 'ul' and 'todo-list' in element.get('class', []):
#         # Handle to-do list
#         blocks = []
#         for li in element.find_all('li', recursive=False):
#             label_span = li.find('label', class_='todo-list__label')
#             if label_span:
#                 # Retrieve the checkbox input
#                 checkbox_input = label_span.find('input', type='checkbox')
#                 checked = checkbox_input.has_attr('checked') if checkbox_input else False

#                 # Remove the checkbox container to isolate the description
#                 checkbox_container = label_span.find('span', contenteditable='false')
#                 if checkbox_container:
#                     checkbox_container.extract()

#                 # Now, label_span should contain the description text
#                 # We can collect all the remaining contents as the description
#                 description_html = ''
#                 for content in label_span.contents:
#                     description_html += str(content)

#                 # Create a temporary element to pass to html_to_rich_text
#                 from bs4 import BeautifulSoup
#                 temp_element = BeautifulSoup(description_html, 'html.parser')

#                 text = html_to_rich_text(temp_element)

#                 block = {
#                     "object": "block",
#                     "has_children": False,
#                     "archived": False,
#                     "in_trash": False,
#                     'type': 'to_do',
#                     'to_do': {
#                         'rich_text': text,
#                         'checked': checked
#                     }
#                 }

#                 # If the original element has data-notion-block-id, add it to the block
#                 block_id = element.get('data-notion-block-id')
#                 if block_id:
#                     block['id'] = block_id

#                 blocks.append(block)
#         return blocks




#     elif block_type == 'divider':
#         return {
#             "type": "divider",
#             "divider": {}
#         }

#     elif block_type == 'image':
#         img_tag = element.find('img')
#         if img_tag:
#             image_url = img_tag.get('src')
#             caption = element.find('figcaption').get_text() if element.find('figcaption') else ''
#             return {
#                 "type": "image",
#                 "image": {
#                     "type": "external",
#                     "external": {
#                         "url": image_url
#                     },
#                     "caption": [{
#                         "type": "text",
#                         "text": {
#                             "content": caption
#                         }
#                     }]
#                 }
#             }

#     elif block_type == 'callout':
#         text = html_to_rich_text(element)
#         block = {
#             "type": "callout",
#             "callout": {
#                 "rich_text": text,
#                 "icon": {
#                     "type": "emoji",
#                     "emoji": "ℹ️"  # 默认图标，或根据需要调整
#                 }
#             },
#             "children": []
#         }
#         # 处理子元素
#         for child_element in element.find_all(recursive=False):
#             if child_element.name != 'span' and child_element != element.contents[0]:
#                 child_block = element_to_notion_block(child_element)
#                 if child_block:
#                     block["children"].append(child_block)
#         return block
        
#     elif block_type == 'code':
#         code_element = element.find('code')
#         code_text = code_element.get_text() if code_element else ''
#         language_class = code_element.get('class', [])
#         language = ''
#         if language_class:
#             language = language_class[0].replace('language-', '')
#         return {
#             "type": "code",
#             "code": {
#                 "rich_text": [{
#                     "type": "text",
#                     "text": {
#                         "content": code_text
#                     }
#                 }],
#                 "language": language
#             }
#         }

#     elif block_type == 'file':
#         a_tag = element.find('a')
#         file_url = a_tag.get('href') if a_tag else ''
#         file_name = a_tag.get_text() if a_tag else ''
#         return {
#             "type": "file",
#             "file": {
#                 "type": "external",
#                 "external": {
#                     "url": file_url
#                 },
#                 "caption": [{
#                     "type": "text",
#                     "text": {
#                         "content": file_name
#                     }
#                 }]
#             }
#         }

#     elif block_type == 'bookmark':
#         a_tag = element.find('a')
#         url = a_tag.get('href') if a_tag else ''
#         caption = a_tag.get_text() if a_tag else ''
#         return {
#             "type": "bookmark",
#             "bookmark": {
#                 "url": url,
#                 "caption": [{
#                     "type": "text",
#                     "text": {
#                         "content": caption
#                     }
#                 }]
#             }
#         }

#     elif block_type == 'link_preview':
#         a_tag = element.find('a')
#         url = a_tag.get('href') if a_tag else ''
#         return {
#             "type": "link_preview",
#             "link_preview": {
#                 "url": url
#             }
#         }

#     elif block_type == 'link_to_page':
#         a_tag = element.find('a')
#         page_id = a_tag.get('href').split('/page/')[1] if a_tag else ''
#         return {
#             "type": "link_to_page",
#             "link_to_page": {
#                 "type": "page_id",
#                 "page_id": page_id
#             }
#         }

#     elif block_type == 'toggle':
#         summary = element.find('summary')
#         title_text = summary.get_text() if summary else ''
#         block = {
#             "type": "toggle",
#             "toggle": {
#                 "rich_text": html_to_rich_text(summary)
#             },
#             "children": []
#         }
#         # 处理子元素
#         for child_element in element.find_all(recursive=False):
#             if child_element != summary:
#                 child_block = element_to_notion_block(child_element)
#                 if child_block:
#                     block["children"].append(child_block)
#         return block

#     elif block_type == 'audio':
#         source_tag = element.find('source')
#         audio_url = source_tag.get('src') if source_tag else ''
#         return {
#             "type": "audio",
#             "audio": {
#                 "type": "external",
#                 "external": {
#                     "url": audio_url
#                 }
#             }
#         }

#     elif block_type == 'child_page':
#         # Notion API 如何 创建子页面？？？ TBC
#         return None

#     else:
#         return None




def element_to_notion_block(element):
    # 初始化 block_type
    block_type = element.get('data-notion-block-type')

    # 如果没有 data-notion-block-type，根据元素类型和类名判断 block_type
    if not block_type:
        if element.name == 'p':
            block_type = 'paragraph'
        elif element.name == 'h1':
            block_type = 'heading_1'
        elif element.name == 'h2':
            block_type = 'heading_2'
        elif element.name == 'h3':
            block_type = 'heading_3'
        elif element.name == 'ul' and 'todo-list' in element.get('class', []):
            block_type = 'to_do'
        elif element.name == 'ul':
            block_type = 'bulleted_list'
        elif element.name == 'ol':
            block_type = 'numbered_list'
        elif element.name == 'hr':
            block_type = 'divider'
        elif element.name == 'pre' and element.find('code'):
            block_type = 'code'
        elif element.name == 'figure':
            if element.find('img'):
                block_type = 'image'
            elif element.find('table'):
                block_type = 'table'
            else:
                block_type = 'unsupported'
        elif element.name == 'blockquote':
            block_type = 'quote'
        elif element.name == 'table':
            block_type = 'table'
        else:
            block_type = 'unsupported'

    # 开始根据 block_type 构建对应的 Notion 块
    if block_type == 'paragraph':
        block = {
            "type": "paragraph",
            "paragraph": {
                "rich_text": html_to_rich_text(element),
                "color": "default"
            }
        }
        block_id = element.get('data-notion-block-id')
        if block_id:
            block['id'] = block_id
        return block

    elif block_type in ['heading_1', 'heading_2', 'heading_3']:
        block = {
            "type": block_type,
            block_type: {
                "rich_text": html_to_rich_text(element),
                "color": "default",
                "is_toggleable": False
            }
        }
        block_id = element.get('data-notion-block-id')
        if block_id:
            block['id'] = block_id
        return block

    elif block_type == 'to_do':
        blocks = []
        for li in element.find_all('li', recursive=False):
            label = li.find('label', class_='todo-list__label')
            if label:
                checkbox_input = label.find('input', type='checkbox')
                checked = checkbox_input.has_attr('checked') if checkbox_input else False
                description_span = label.find('span', class_='todo-list__label__description')
                text = html_to_rich_text2(description_span)
                block = {
                    "type": "to_do",
                    "to_do": {
                        "rich_text": text,
                        "checked": checked,
                        "color": "default"
                    }
                }
                block_id = li.get('data-notion-block-id')
                if block_id:
                    block['id'] = block_id
                # 处理子任务（嵌套的 to_do_list）
                sub_list = li.find('ul', class_='todo-list', recursive=False)
                if sub_list:
                    children_blocks = element_to_notion_block(sub_list)
                    if children_blocks:
                        block['has_children'] = True
                        block['children'] = children_blocks
                blocks.append(block)
        return blocks

    elif block_type in ['bulleted_list', 'numbered_list']:
        list_type = 'bulleted_list_item' if block_type == 'bulleted_list' else 'numbered_list_item'
        blocks = []
        for li in element.find_all('li', recursive=False):
            text = html_to_rich_text(li)
            block = {
                "type": list_type,
                list_type: {
                    "rich_text": text,
                    "color": "default"
                }
            }
            block_id = li.get('data-notion-block-id')
            if block_id:
                block['id'] = block_id
            # 处理嵌套列表
            sub_list = li.find(['ul', 'ol'], recursive=False)
            if sub_list:
                child_list_type = 'bulleted_list_item' if sub_list.name == 'ul' else 'numbered_list_item'
                children_blocks = element_to_notion_block(sub_list)
                if children_blocks:
                    block['has_children'] = True
                    block['children'] = children_blocks
            blocks.append(block)
        return blocks

    elif block_type == 'divider':
        block = {
            "type": "divider",
            "divider": {}
        }
        return block

    elif block_type == 'code':
        code_element = element.find('code')
        code_text = code_element.get_text() if code_element else ''
        language_class = code_element.get('class', [])
        language = 'plain text'
        for cls in language_class:
            if cls.startswith('language-'):
                language = cls.replace('language-', '')
                break
        block = {
            "type": "code",
            "code": {
                "rich_text": [{
                    "type": "text",
                    "text": {
                        "content": code_text,
                        "link": None
                    },
                    "plain_text": code_text,
                    "href": None,
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                        "color": "default"
                    }
                }],
                "language": language
            }
        }
        block_id = element.get('data-notion-block-id')
        if block_id:
            block['id'] = block_id
        return block

    elif block_type == 'image':
        img_tag = element.find('img')
        if img_tag:
            image_url = img_tag.get('src')
            caption_element = element.find('figcaption')
            caption = caption_element.get_text() if caption_element else ''
            block = {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {
                        "url": image_url
                    },
                    "caption": [{
                        "type": "text",
                        "text": {
                            "content": caption,
                            "link": None
                        },
                        "plain_text": caption,
                        "href": None,
                        "annotations": {
                            "bold": False,
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                            "code": False,
                            "color": "default"
                        }
                    }]
                }
            }
            block_id = element.get('data-notion-block-id')
            if block_id:
                block['id'] = block_id
            return block

    elif block_type == 'table':
        # 处理表格
        table_element = element.find('table') if element.name == 'figure' else element
        if table_element:
            rows = []
            for tr in table_element.find_all('tr'):
                cells = []
                for td in tr.find_all(['td', 'th']):
                    cell_content = html_to_rich_text(td)
                    cells.append(cell_content)
                row_block = {
                    "type": "table_row",
                    "table_row": {
                        "cells": cells
                    }
                }
                rows.append(row_block)
            table_block = {
                "type": "table",
                "table": {
                    "table_width": len(rows[0]['table_row']['cells']) if rows else 0,
                    "has_column_header": False,
                    "has_row_header": False,
                    "children": rows
                }
            }
            block_id = element.get('data-notion-block-id')
            if block_id:
                table_block['id'] = block_id
            return table_block

    elif block_type == 'quote':
        # 处理引用块
        # 引用块可能包含多个段落，需要将它们的内容合并
        rich_text = []
        for child in element.contents:
            if isinstance(child, Tag):
                rich_text.extend(html_to_rich_text(child))
            elif isinstance(child, NavigableString):
                text_content = str(child).strip()
                if text_content:
                    rich_text.append({
                        "type": "text",
                        "text": {
                            "content": text_content,
                            "link": None
                        },
                        "plain_text": text_content,
                        "href": None,
                        "annotations": {
                            "bold": False,
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                            "code": False,
                            "color": "default"
                        }
                    })
        block = {
            "type": "quote",
            "quote": {
                "rich_text": rich_text,
                "color": "default"
            }
        }
        block_id = element.get('data-notion-block-id')
        if block_id:
            block['id'] = block_id
        # 处理子块（如果有）
        # if element.find_all(recursive=False):
        #     child_blocks = []
        #     for child_element in element.find_all(recursive=False):
        #         child_block = element_to_notion_block(child_element)
        #         if child_block:
        #             child_blocks.append(child_block)
        #     if child_blocks:
        #         block['has_children'] = True
        #         block['children'] = child_blocks
        return block


    else:
        # 对于不支持的块类型，返回 None 或者按照段落处理
        return None




# for to_do block only
def html_to_rich_text2(element):
    rich_text = []
    for content in element.contents:
        if isinstance(content, str):
            if content.strip():
                rich_text.append({
                    "type": "text",
                    "text": {
                        "content": content.strip()
                    },
                    "plain_text": content.strip()
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
                },
                "plain_text": text
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
                },
                "plain_text": text
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
                },
                "plain_text": text
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
                },
                "plain_text": text
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
                },
                "plain_text": text
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
                },
                "plain_text": '[' + text + ']: (' + href + ')'
            })
        else:
            # 递归处理其他标签
            rich_text.extend(html_to_rich_text(content))
    return rich_text


def html_to_rich_text(element):
    rich_text = []

    for content in element.descendants:
        if isinstance(content, NavigableString):
            text_content = str(content).strip()
            if text_content:
                rich_text.append({
                    "type": "text",
                    "text": {
                        "content": text_content,
                        "link": None
                    },
                    "plain_text": text_content,
                    "href": None,
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                        "color": "default"
                    }
                })
        elif isinstance(content, Tag):
            text_content = content.get_text()
            annotations = {
                "bold": content.name in ['strong', 'b'],
                "italic": content.name in ['em', 'i'],
                "strikethrough": content.name == 's',
                "underline": content.name == 'u',
                "code": content.name == 'code',
                "color": "default"
            }
            href = content.get('href') if content.name == 'a' else None
            rich_text.append({
                "type": "text",
                "text": {
                    "content": text_content,
                    "link": {"url": href} if href else None
                },
                "plain_text": text_content,
                "href": href,
                "annotations": annotations
            })
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
            }
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








