# app/notion_parser.py

from notion_client import Client
from bs4 import BeautifulSoup, NavigableString, Tag
import json
import time
# 加载配置
config = {}
with open('app/config/config.json') as config_file:
    config = json.load(config_file)

# 初始化 Notion 客户端
notion = Client(auth=config['notion_token'])


# Global cache variable
cache = {
    'page_tree': None,
    'timestamp': None,
    'expiry': config.get('cache_expiry', 3600)  # Default expiry time is 1 hour
}

def get_cached_page_tree():
    if cache['page_tree'] is None or cache_expired():
        update_cache()
    return cache['page_tree']

def cache_expired():
    if cache['timestamp'] is None:
        return True
    return (time.time() - cache['timestamp']) > cache['expiry']

def update_cache():
    # Reload config
    with open('app/config/config.json') as config_file:
        config.update(json.load(config_file))
    # Rebuild page tree
    cache['page_tree'] = build_page_tree()
    # Update timestamp
    cache['timestamp'] = time.time()

def build_page_tree():
    pages = []
    for root_page_id in get_page_ids():
        page_title = get_page_title(root_page_id)
        root_page = {
            'id': root_page_id,
            'name': page_title,
            'has_children': True,  # Assume root pages have children
            'children': []  # We'll leave children empty for now
        }
        pages.append(root_page)
    return pages



def get_sub_pages_from_cache(page_id):
    # First, check if the sub-pages are already in the cache
    page_tree = get_cached_page_tree()
    sub_pages = find_sub_pages_in_cache(page_id, page_tree)
    if sub_pages is not None and len(sub_pages) >0:
        return sub_pages
    else:
        # Sub-pages not in cache, fetch from Notion API and update cache
        sub_pages = []
        parent_page = find_page_in_cache(page_id, page_tree)
        if not parent_page['has_children']:
            return sub_pages
        try:
            children = notion.blocks.children.list(block_id=page_id, page_size=100)['results']
            for child in children:
                if child['type'] == 'child_page':
                    sub_page_id = child['id']
                    sub_page_title = child['child_page']['title']
                    has_children = child['has_children']
                    sub_page = {
                        'id': sub_page_id,
                        'name': sub_page_title,
                        'has_children': has_children,
                        'children': []  # We won't load grandchildren yet
                    }
                    sub_pages.append(sub_page)
            # Update cache with the sub-pages
            add_sub_pages_to_cache(page_id, sub_pages)
        except Exception as e:
            print(f"Error fetching children for page {page_id}: {e}")
        return sub_pages



def find_sub_pages_in_cache(page_id, pages=None):
    if pages is None:
        pages = get_cached_page_tree()
    for page in pages:
        if page['id'] == page_id:
            return page.get('children')
        if 'children' in page and page['children']:
            result = find_sub_pages_in_cache(page_id, page['children'])
            if result is not None:
                return result
    return None

def add_sub_pages_to_cache(page_id, sub_pages):
    # Find the page in the cache and add the sub_pages
    page_tree = get_cached_page_tree()
    page = find_page_in_cache(page_id, page_tree)
    if page:
        page['children'] = sub_pages
        # Update has_children
        page['has_children'] = len(sub_pages) > 0


def find_page_in_cache(page_id, pages=None):
    if pages is None:
        pages = get_cached_page_tree()
    for page in pages:
        if page['id'] == page_id:
            return page
        if 'children' in page and page['children']:
            result = find_page_in_cache(page_id, page['children'])
            if result is not None:
                return result
    return None



def upTracePageAncestor2Cache(page_id):
    """
    Traces the ancestors of the given page_id and inserts the path into the cache tree.
    """
    # Get the current cached page tree
    page_tree = get_cached_page_tree()

    # List to hold the path from the root to the current page
    path = []

    current_page_id = page_id
    while True:
        # Check if current_page_id is already in cache
        page_in_cache = find_page_in_cache(current_page_id, page_tree)
        if page_in_cache:
            # Page is already in cache; we can attach the path here
            break
        else:
            # Page not in cache; retrieve it via Notion API
            try:
                page = notion.pages.retrieve(page_id=current_page_id)
                page_title = page["properties"]["title"]['title'][0]['plain_text'] #get_page_title(current_page_id) #page["properties"]["title"]['title'][0]['plain_text']
                parent_info = page.get('parent')
                has_children = page.get('has_children', True) # True 

                # Create a page dict
                page_dict = {
                    'id': current_page_id,
                    'name': page_title,
                    'has_children': has_children,
                    'children': []
                }

                # Insert at the beginning of the path list
                path.insert(0, page_dict)

                if parent_info and parent_info.get('type') == 'page_id':
                    # Continue tracing upwards to the parent
                    current_page_id = parent_info.get('page_id')
                else:
                    # Reached a root page not in cache; add it to the root of the cache tree
                    page_tree.append(page_dict)
                    # Update cache timestamp
                    cache['timestamp'] = time.time()
                    return
            except Exception as e:
                print(f"Error retrieving page {current_page_id}: {e}")
                return

    # Now, we have a page in cache (`page_in_cache`) and a path of pages to attach
    parent_in_cache = page_in_cache
    for page_dict in path:
        # Attach each page in the path to the appropriate parent in the cache
        # Check if the child already exists in the parent's children
        child_in_cache = find_page_in_children(page_dict['id'], parent_in_cache['children'])
        if not child_in_cache:
            parent_in_cache['children'].append(page_dict) #todo: add ony 1???  or traverse all children??
            parent_in_cache['has_children'] = True
            # Move to the next level
            parent_in_cache = page_dict
        else:
            # Child already exists; move to it
            parent_in_cache = child_in_cache

    # Update cache timestamp
    cache['timestamp'] = time.time()


def find_page_in_children(page_id, children):
    for child in children:
        if child['id'] == page_id:
            return child
    return None

def generate_breadcrumbs_from_cache(page_id):
    """
    Generates a list of breadcrumbs from the root to the given page_id.
    Each breadcrumb is a dictionary with 'id' and 'name'.
    """
    breadcrumbs = []
    page = find_page_in_cache(page_id, get_cached_page_tree())
    if page is None:
        return breadcrumbs  # Empty list if page not found

    # Traverse up to the root
    while page:
        breadcrumbs.insert(0, {'id': page['id'], 'name': page['name']})
        parent_page = find_parent_in_cache(page['id'], get_cached_page_tree())
        page = parent_page
    return breadcrumbs

# def find_parent_in_cache(child_id, pages):
#     for page in pages:
#         if any(child['id'] == child_id for child in page.get('children', [])):
#             return page
#         # Recursively search in children
#         result = find_parent_in_cache(child_id, page.get('children', []))
#         if result:
#             return result
#     return None

# find parent by child_id
def find_parent_in_cache(child_id, pages=None):
    # ensuring upTracePageAncestor2Cache 
    title = get_cached_page_title(child_id)
    if pages is None:
        pages = get_cached_page_tree()
    for page in pages:
        if any(child['id'] == child_id for child in page.get('children', [])):
            return page
        # Recursively search in children
        result = find_parent_in_cache(child_id, page.get('children', []))
        if result:
            return result
    return None






def update_page_name_in_cache(page_id, new_name):
    page_tree = get_cached_page_tree()
    page = find_page_in_cache(page_id, page_tree)
    if page:
        page['name'] = new_name
        # Update cache timestamp
        cache['timestamp'] = time.time()



def update_parent_children_in_cache(parent_id):
    try:
        # Fetch the latest children of the parent page
        children = notion.blocks.children.list(block_id=parent_id, page_size=100)['results']
        sub_pages = []
        for child in children:
            if child['type'] == 'child_page':
                sub_page_id = child['id']
                sub_page_title = child['child_page']['title']
                has_children = child['has_children']
                sub_page = {
                    'id': sub_page_id,
                    'name': sub_page_title,
                    'has_children': has_children,
                    'children': []
                }
                sub_pages.append(sub_page)
        # Update the parent in the cache
        page_tree = get_cached_page_tree()
        parent_page = find_page_in_cache(parent_id, page_tree)
        if parent_page:
            parent_page['children'] = sub_pages
            parent_page['has_children'] = len(sub_pages) > 0
            cache['timestamp'] = time.time()
    except Exception as e:
        print(f"Error updating parent children in cache: {e}")


def update_node_children_in_cache(page_id):
    try:
        # Fetch the latest children of the node
        children = notion.blocks.children.list(block_id=page_id, page_size=100)['results']
        sub_pages = []
        for child in children:
            if child['type'] == 'child_page':
                sub_page_id = child['id']
                sub_page_title = child['child_page']['title']
                has_children = child['has_children']
                sub_page = {
                    'id': sub_page_id,
                    'name': sub_page_title,
                    'has_children': has_children,
                    'children': []
                }
                sub_pages.append(sub_page)
        # Update the node in the cache
        page_tree = get_cached_page_tree()
        node = find_page_in_cache(page_id, page_tree)
        if node:
            node['children'] = sub_pages
            node['has_children'] = len(sub_pages) > 0
            cache['timestamp'] = time.time()
    except Exception as e:
        print(f"Error updating node children in cache: {e}")






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

def get_cached_page_title(page_id):
    page_tree = get_cached_page_tree()
    page = find_page_in_cache(page_id, page_tree)
    if page:
        return page["name"]
    else:
        # Page not in cache; load the entire path into cache
        upTracePageAncestor2Cache(page_id)
        return get_page_title(page_id)

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
        elif element.name == 'h4':
            block_type = 'heading_3'
        elif element.name == 'h5':
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

    elif block_type in ['link_to_page', 'child_page']: # child_page - NOT WORKING

        '''
        <p data-notion-block-type="link_to_page" data-notion-block-id="135012cb-4981-815c-9e5a-e6de0edfb39b">
            <a href="/page/135012cb-4981-8013-be94-e659e8bd472e">sub-1</a>
        </p>
        '''
        href = element.find('a').get('href')
        sub_id= href.split('/')[-1]

        block = {
                "type": "link_to_page",
                "link_to_page": {
                    "type": "page_id",
                    "page_id": sub_id
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
        language = 'python'
        # body.children[0].code.language should be `"abap"`, `"agda"`, `"arduino"`, `"ascii art"`, `"assembly"`, `"bash"`, `"basic"`, `"bnf"`, `"c"`, `"c#"`, `"c++"`, `"clojure"`, `"coffeescript"`, `"coq"`, `"css"`, `"dart"`, `"dhall"`, `"diff"`, `"docker"`, `"ebnf"`, `"elixir"`, `"elm"`, `"erlang"`, `"f#"`, `"flow"`, `"fortran"`, `"gherkin"`, `"glsl"`, `"go"`, `"graphql"`, `"groovy"`, `"haskell"`, `"hcl"`, `"html"`, `"idris"`, `"java"`, `"javascript"`, `"json"`, `"julia"`, `"kotlin"`, `"latex"`, `"less"`, `"lisp"`, `"livescript"`, `"llvm ir"`, `"lua"`, `"makefile"`, `"markdown"`, `"markup"`, `"matlab"`, `"mathematica"`, `"mermaid"`, `"nix"`, `"notion formula"`, `"objective-c"`, `"ocaml"`, `"pascal"`, `"perl"`, `"php"`, `"plain text"`, `"powershell"`, `"prolog"`, `"protobuf"`, `"purescript"`, `"python"`, `"r"`, `"racket"`, `"reason"`, `"ruby"`, `"rust"`, `"sass"`, `"scala"`, `"scheme"`, `"scss"`, `"shell"`, `"solidity"`, `"sql"`, `"swift"`, `"toml"`, `"typescript"`, `"vb.net"`, `"verilog"`, `"vhdl"`, `"visual basic"`, `"webassembly"`, `"xml"`, `"yaml"`, `"java/c/c++/c#"`, or `"notionscript"`
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


