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
    html += '<div class="nav-link">'
    if has_children:
        html += '<span class="toggle-icon" onclick="toggleSubPages(this)">▶</span> '
    else:
        html += '<span class="toggle-icon"></span>'
    html += f'<a href="{page_url}">{page["name"]}</a>'
    html += '</div>'
    if has_children:
        html += '<ul class="nav flex-column ml-3" style="display: none;">'
        for child in page['children']:
            html += render_page_tree(child)
        html += '</ul>'
    html += '</li>'
    # return Markup(html)
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

# @app.route('/get_sub_pages/<page_id>')
# def get_sub_pages_route(page_id):
#     sub_pages = get_sub_pages(page_id)
#     return jsonify(sub_pages)

# def get_sub_pages(page_id):
#     sub_pages = []
#     children = notion.blocks.children.list(block_id=page_id)
#     for child in children['results']:
#         if child['type'] == 'child_page':
#             sub_page_id = child['id']
#             sub_page_name = child['child_page']['title']
#             has_children = child['has_children']
#             sub_page_data = {
#                 'id': sub_page_id,
#                 'name': sub_page_name,
#                 'has_children': has_children
#             }
#             sub_pages.append(sub_page_data)
#     return sub_pages

# routes.py

@app.route('/get_sub_pages/<page_id>')
def get_sub_pages(page_id):
    sub_pages = []
    try:
        children = notion.blocks.children.list(block_id=page_id)['results']
        for child in children:
            if child['type'] == 'child_page':
                sub_page = {
                    'id': child['id'],
                    'name': child['child_page']['title'],
                    'has_children': child['has_children']
                }
                sub_pages.append(sub_page)
    except Exception as e:
        print(f"Error fetching children for page {page_id}: {e}")
    return jsonify(sub_pages)


def table_to_blocks(table_element):
    blocks = []

    # 创建 table 块
    table_block = {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": 0,  # 列数
            "has_column_header": False,
            "has_row_header": False
        },
        "children": []  # 表格行（table_row）
    }

    # 获取列数
    first_row = table_element.find('tr')
    if first_row:
        columns = len(first_row.find_all(['th', 'td']))
        table_block['table']['table_width'] = columns

    # 检查是否有表头
    if table_element.find('th'):
        table_block['table']['has_column_header'] = True

    # 遍历表格行
    for tr in table_element.find_all('tr'):
        cells = tr.find_all(['th', 'td'])
        cell_contents = []
        for cell in cells:
            # 提取单元格文本
            cell_text = ''.join(cell.stripped_strings)
            cell_rich_text = [{
                "type": "text",
                "text": {
                    "content": cell_text
                }
            }]
            cell_contents.append(cell_rich_text)

        # 创建 table_row 块
        table_row_block = {
            "object": "block",
            "type": "table_row",
            "table_row": {
                "cells": cell_contents
            }
        }
        table_block['children'].append(table_row_block)

    return table_block



def list_to_blocks(element, list_type):
    blocks = []
    for li in element.find_all('li', recursive=False):
        # 处理列表项的文本内容
        text = ''.join([t for t in li.strings])
        block = {
            "object": "block",
            "type": list_type,
            list_type: {
                "rich_text": [{
                    "type": "text",
                    "text": {
                        "content": text
                    }
                }]
            },
            "children": []
        }
        # 检查是否有嵌套列表
        for child in li.contents:
            if child.name == 'ul':
                block['children'] += list_to_blocks(child, 'bulleted_list_item')
            elif child.name == 'ol':
                block['children'] += list_to_blocks(child, 'numbered_list_item')
        blocks.append(block)
    return blocks


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

