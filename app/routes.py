from flask import render_template, request, redirect, url_for, session, flash
import json
from app import app
from notion_client import Client
from markupsafe import Markup
from flask import jsonify
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename
from .minio_helper import S3Client
from datetime import datetime
from .notion_parser import (
    get_block_content,
    parse_block,
    html_to_notion_blocks,
    get_page_title,
    get_page_tree
)




# 加载配置
config = {}
with open('app/config/config.json') as config_file:
    config = json.load(config_file)

notion = Client(auth=config['notion_token'])

# Session management
app.config['SECRET_KEY'] = 'your_secret_key'

s3_client = S3Client(
    endpoint=config['minio']['endpoint'],
    access_key=config['minio']['access_key'],
    secret_key=config['minio']['secret_key'],
    bucket_name=config['minio']['bucket'],
    secure=config['minio']['secure']
)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = next(
            (u for u in config['users'] if u['username'] == username and u['password'] == password),
            None
        )
        if user:
            session['username'] = username
            session['role'] = user['role']
            session['user_permissions'] = config['roles'][user['role']]['operation']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    page_tree = get_page_tree()
    return render_template('index.html', page_tree=page_tree)


@app.route('/page/<page_id>', methods=['GET', 'POST'])
def view_page(page_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    user_role = session.get('role')
    user_permissions = config['roles'][user_role]['operation']
    if request.method == 'POST':
        if 'write' in user_permissions:
            new_content_html = request.form['content']
            new_blocks = html_to_notion_blocks(new_content_html)
            # 清空原有内容并添加新内容 - not working as -- AttributeError: 'BlocksChildrenEndpoint' object has no attribute 'replace'
            # notion.blocks.children.replace(block_id=page_id, children=new_blocks)

            # 获取现有的子块
            existing_children = notion.blocks.children.list(block_id=page_id)
            # 遍历并删除所有子块
            for child in existing_children['results']:
                notion.blocks.update(block_id=child['id'], archived=True)
            # 追加新的子块
            notion.blocks.children.append(block_id=page_id, children=new_blocks)


            flash('页面已更新')
            return redirect(url_for('view_page', page_id=page_id))
        else:
            flash('您没有权限编辑此页面')
            return redirect(url_for('view_page', page_id=page_id))
            
    page_title = get_page_title(page_id)
    page_tree = get_page_tree()
    content = get_block_content(page_id)
    return render_template(
        'page.html',
        content=content,
        page_title=page_title,
        page_id=page_id,
        page_tree=page_tree,
        user_permissions=user_permissions
    )



@app.template_global()
def render_page_tree(page):
    page_url = url_for('view_page', page_id=page['id'])
    has_children = bool(page.get('children'))

    html = '<li class="nav-item">'
    html += f'<div class="nav-link page-item" data-page-id="{page["id"]}" data-has-children="{has_children}">'

    # Icon container
    html += '<span class="icon-container">'

    # Document or chevron icon
    if has_children:
        html += '''
            <svg class="icon chevron-icon" viewBox="0 0 12 12">
                <path d="M6.02734 8.80274C6.27148 8.80274 6.47168 8.71484 6.66211 8.51465L10.2803 4.82324C10.4268 4.67676 10.5 4.49609 10.5 4.28125C10.5 3.85156 10.1484 3.5 9.72363 3.5C9.50879 3.5 9.30859 3.58789 9.15234 3.74902L6.03223 6.9668L2.90722 3.74902C2.74609 3.58789 2.55078 3.5 2.33105 3.5C1.90137 3.5 1.55469 3.85156 1.55469 4.28125C1.55469 4.49609 1.62793 4.67676 1.77441 4.82324L5.39258 8.51465C5.58789 8.71973 5.78808 8.80274 6.02734 8.80274Z"></path>
            </svg>
        '''
    else:
        html += '''
            <svg class="icon document-icon" viewBox="0 0 14 14">
                <path d="M4.35645 15.4678H11.6367C13.0996 15.4678 13.8584 14.6953 13.8584 13.2256V7.02539C13.8584 6.0752 13.7354 5.6377 13.1406 5.03613L9.55176 1.38574C8.97754 0.804688 8.50586 0.667969 7.65137 0.667969H4.35645C2.89355 0.667969 2.13477 1.44043 2.13477 2.91016V13.2256C2.13477 14.7021 2.89355 15.4678 4.35645 15.4678ZM4.46582 14.1279C3.80273 14.1279 3.47461 13.7793 3.47461 13.1436V2.99219C3.47461 2.36328 3.80273 2.00781 4.46582 2.00781H7.37793V5.75391C7.37793 6.73145 7.86328 7.20312 8.83398 7.20312H12.5186V13.1436C12.5186 13.7793 12.1836 14.1279 11.5205 14.1279H4.46582ZM8.95703 6.02734C8.67676 6.02734 8.56055 5.9043 8.56055 5.62402V2.19238L12.334 6.02734H8.95703ZM10.4336 9.00098H5.42969C5.16992 9.00098 4.98535 9.19238 4.98535 9.43164C4.98535 9.67773 5.16992 9.86914 5.42969 9.86914H10.4336C10.6797 9.86914 10.8643 9.67773 10.8643 9.43164C10.8643 9.19238 10.6797 9.00098 10.4336 9.00098ZM10.4336 11.2979H5.42969C5.16992 11.2979 4.98535 11.4893 4.98535 11.7354C4.98535 11.9746 5.16992 12.1592 5.42969 12.1592H10.4336C10.6797 12.1592 10.8643 11.9746 10.8643 11.7354C10.8643 11.4893 10.6797 11.2979 10.4336 11.2979Z"></path>
            </svg>
        '''
    html += '</span>'

    # Page title
    html += f'<a href="{page_url}" class="page-title">{page["name"]}</a>'

    # Action buttons (hidden by default)
    html += '''
        <div class="action-buttons">
            <span class="button dots-button" onclick="showContextMenu(event, '{page["id"]}')">
                <!-- Three-dot icon -->
                <svg class="icon dots-icon" viewBox="0 0 13 3">
                    <g>
                        <path d="M3,1.5A1.5,1.5,0,1,1,1.5,0,1.5,1.5,0,0,1,3,1.5Z"></path>
                        <path d="M8,1.5A1.5,1.5,0,1,1,6.5,0,1.5,1.5,0,0,1,8,1.5Z"></path>
                        <path d="M13,1.5A1.5,1.5,0,1,1,11.5,0,1.5,1.5,0,0,1,13,1.5Z"></path>
                    </g>
                </svg>
            </span>
            <span class="button plus-button" onclick="addSubPage('{page["id"]}')">
                <!-- Plus icon -->
                <svg class="icon plus-icon" viewBox="0 0 14 14">
                    <path d="M2 7.16357C2 7.59692 2.36011 7.95093 2.78735 7.95093H6.37622V11.5398C6.37622 11.9731 6.73022 12.3271 7.16357 12.3271C7.59692 12.3271 7.95093 11.9731 7.95093 11.5398V7.95093H11.5398C11.9731 7.95093 12.3271 7.59692 12.3271 7.16357C12.3271 6.73022 11.9731 6.37622 11.5398 6.37622H7.95093V2.78735C7.95093 2.36011 7.59692 2 7.16357 2C6.73022 2 6.37622 2.36011 6.37622 2.78735V6.37622H2.78735C2.36011 6.37622 2 6.73022 2 7.16357Z"></path>
                </svg>
            </span>
        </div>
    '''

    html += '</div>'

    # Subpages
    if has_children:
        html += '<ul class="nav flex-column ml-3 subpage-list" style="display: none;">'
        for child in page['children']:
            html += render_page_tree(child)
        html += '</ul>'
    html += '</li>'
    return html
    


def get_pages():
    pages = []
    for page_info in config['pages']:
        page_id = page_info['page_id']
        page_name = get_page_title(page_id)
        page_data = {
            'id': page_id,
            'name': page_name,
            'has_children': True  # 假设顶层页面有子页面，前端可以根据需要进一步获取
        }
        pages.append(page_data)
    return pages
def get_page_title(page_id):
    page = notion.pages.retrieve(page_id=page_id)
    if 'properties' in page and 'title' in page['properties']:
        title_property = page['properties']['title']['title']
        page_name = ''.join([t['plain_text'] for t in title_property]) if title_property else 'Untitled'
    else:
        page_name = 'Untitled'
    return page_name


@app.route('/get_sub_pages/<page_id>')
def get_sub_pages(page_id):
    sub_pages = []
    try:
        # 获取直接子页面
        children = notion.blocks.children.list(block_id=page_id, page_size=100)['results']
        for child in children:
            if child['type'] == 'child_page':
                sub_page_id = child['id']
                sub_page = {
                    'id': sub_page_id,
                    'name': child['child_page']['title'],
                    'has_children': child['has_children']
                }
                sub_pages.append(sub_page)
    except Exception as e:
        print(f"Error fetching children for page {page_id}: {e}")
    return jsonify(sub_pages)


def update_notion_page_content(page_id, new_blocks):
    # 删除原有内容
    # 注意：Notion API 不支持直接替换整个页面的内容，需要先删除现有的子块
    # 获取现有子块
    existing_blocks = notion.blocks.children.list(block_id=page_id)
    for block in existing_blocks['results']:
        notion.blocks.delete(block_id=block['id'])

    # 添加新的块
    for block in new_blocks:
        notion.blocks.children.append(block_id=page_id, children=[block])

def inline_element_to_rich_text(element):
    rich_text = []

    for item in element.descendants:
        if isinstance(item, str):
            text_content = item.strip()
            if text_content:
                rich_text.append({
                    "type": "text",
                    "text": {
                        "content": text_content
                    }
                })
        elif item.name == 'strong' or item.name == 'b':
            text_content = item.get_text()
            rich_text.append({
                "type": "text",
                "text": {
                    "content": text_content
                },
                "annotations": {
                    "bold": True
                }
            })
        elif item.name == 'em' or item.name == 'i':
            text_content = item.get_text()
            rich_text.append({
                "type": "text",
                "text": {
                    "content": text_content
                },
                "annotations": {
                    "italic": True
                }
            })
        elif item.name == 'a':
            text_content = item.get_text()
            href = item.get('href')
            rich_text.append({
                "type": "text",
                "text": {
                    "content": text_content,
                    "link": {
                        "url": href
                    }
                }
            })
        # 添加更多的 inline 元素处理
        else:
            # 处理其他未支持的 inline 元素
            pass
    return rich_text



# timestamp in %Y%m%d%H%M%S + milliseconds
def get_timestamp_with_milliseconds():
    # Get current time with microseconds
    now = datetime.now()
    # Format the timestamp as %Y%m%d%H%M%S and append milliseconds
    timestamp = now.strftime('%Y%m%d%H%M%S') + f'{int(now.microsecond / 1000):03d}'
    return timestamp

@app.route('/upload_image', methods=['POST'])
def upload_image():
    print("upload_image")
    if 'username' not in session:
        return jsonify({'error': '未登录'}), 401
    if 'write' not in session.get('user_permissions', []):
        return jsonify({'error': '无权限'}), 403
    # file = request.files.get('upload')
    file = request.files.get('upload') or request.files.get('file')
    if file:
        filename = secure_filename(file.filename) 

        object_name = get_timestamp_with_milliseconds()+"_" +filename # 或者使用None以自动获取文件名
        s3_client.upload_stream(file.stream, object_name, content_type=file.content_type)

        # 首先设置Bucket策略为公共读取
        s3_client.set_bucket_policy_public_read()
        public_url = s3_client.get_direct_url(object_name, days=-1)


        # 返回符合 CKEditor 期望的 JSON 格式
        return jsonify({'uploaded': True, 'url': public_url})
    else:
        return jsonify({'uploaded': False, 'error': {'message': '未选择文件'}}), 400



@app.route('/delete_page/<page_id>', methods=['POST'])
def delete_page(page_id):
    try:
        notion.pages.update(page_id=page_id, archived=True)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting page {page_id}: {e}")
        return jsonify({'success': False})

@app.route('/rename_page/<page_id>', methods=['POST'])
def rename_page_route(page_id):
    new_title = request.json.get('title')
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": new_title
                            }
                        }
                    ]
                }
            }
        )
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error renaming page {page_id}: {e}")
        return jsonify({'success': False})

@app.route('/duplicate_page/<page_id>', methods=['POST'])
def duplicate_page(page_id):
    try:
        # Retrieve the original page
        original_page = notion.pages.retrieve(page_id)
        properties = original_page['properties']
        children = notion.blocks.children.list(block_id=page_id)['results']
        
        # Create a new page with "(copy)" appended to the title
        title_property = properties['title']['title']
        original_title = ''.join([t['plain_text'] for t in title_property])
        new_title = original_title + ' (copy)'

        new_page = notion.pages.create(
            parent={"page_id": original_page['parent']['page_id']},
            properties={
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": new_title
                            }
                        }
                    ]
                }
            },
            children=children
        )
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error duplicating page {page_id}: {e}")
        return jsonify({'success': False})

@app.route('/create_sub_page/', methods=['POST'])
def create_sub_page():
    data = request.json
    parent_id = data.get('parent_id')
    title = data.get('title')
    try:
        new_page = notion.pages.create(
            parent={"page_id": parent_id},
            properties={
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
        )
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error creating subpage under {parent_id}: {e}")
        return jsonify({'success': False})