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
    # get_page_tree,
    get_cached_page_tree,
    get_sub_pages_from_cache,
    find_page_in_cache,
    upTracePageAncestor2Cache,
    generate_breadcrumbs_from_cache,
    get_cached_page_title,

    update_page_name_in_cache,
    update_parent_children_in_cache,
    update_node_children_in_cache,
    find_parent_in_cache
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
    page_tree = get_cached_page_tree() # get_page_tree()
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
    
    # Check if the page is in the cache
    if not is_page_in_cache(page_id):
        # Load the page and its ancestors into the cache
        upTracePageAncestor2Cache(page_id)
        
    page_title = get_cached_page_title(page_id)
    page_tree = get_cached_page_tree() #get_page_tree()
    content = get_block_content(page_id)

    # Generate breadcrumbs from the cache
    breadcrumbs = generate_breadcrumbs_from_cache(page_id)
    
    return render_template(
        'page.html',
        content=content,
        page_title=page_title,
        page_id=page_id,
        page_tree=page_tree,
        user_permissions=user_permissions,
        breadcrumbs=breadcrumbs
    )

def is_page_in_cache(page_id):
    page_tree = get_cached_page_tree()
    return find_page_in_cache(page_id, page_tree) is not None



def render_page_tree(page):
    page_url = url_for('view_page', page_id=page['id'])
    has_children = page.get('has_children', False)

    html = '<li class="nav-item">'
    html += f'<div class="nav-link page-item" data-page-id="{page["id"]}" data-has-children="{has_children}">'

    # Icon container
    html += '<span class="icon-container" onclick="toggleSubPages(this)">'

    # Document or chevron icon
    if has_children:
        html += '''
            <svg class="icon chevron-icon" viewBox="0 0 12 12">
                <!-- Chevron icon SVG path -->
                <path d="M6.02734 8.80274C6.27148 8.80274 6.47168 8.71484 6.66211 8.51465L10.2803 4.82324C10.4268 4.67676 10.5 4.49609 10.5 4.28125C10.5 3.85156 10.1484 3.5 9.72363 3.5C9.50879 3.5 9.30859 3.58789 9.15234 3.74902L6.03223 6.9668L2.90722 3.74902C2.74609 3.58789 2.55078 3.5 2.33105 3.5C1.90137 3.5 1.55469 3.85156 1.55469 4.28125C1.55469 4.49609 1.62793 4.67676 1.77441 4.82324L5.39258 8.51465C5.58789 8.71973 5.78808 8.80274 6.02734 8.80274Z"></path>
            </svg>
        '''
    else:
        html += '''
            <svg class="icon document-icon" viewBox="0 0 14 14">
                <!-- Document icon SVG path -->
                <path d="M3 1h8a1 1 0 011 1v10a1 1 0 01-1 1H3a1 1 0 01-1-1V2a1 1 0 011-1z"></path>
            </svg>
        '''
    html += '</span>'

    # Page title
    html += f'<a href="{page_url}" class="page-title">{page["name"]}</a>'

    # Action buttons
    html += f'''
        <div class="action-buttons">
            <span class="button refresh-button" onclick="refreshPageTree('{page["id"]}')">
                <!-- Refresh icon SVG -->
                <svg fill="#000000" width="16px" height="16px" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                    <path d="M497.408 898.56c-.08-.193-.272-.323-.385-.483l-91.92-143.664c-6.528-10.72-20.688-14.527-31.728-8.512l-8.193 5.04c-11.007 6-10.767 21.537-4.255 32.256l58.927 91.409c-5.024-1.104-10.096-2-15.056-3.296-103.184-26.993-190.495-96.832-239.535-191.6-46.336-89.52-55.04-191.695-24.512-287.743 30.512-96.048 99.775-174.464 189.295-220.784 15.248-7.888 21.2-26.64 13.312-41.856-7.872-15.264-26.64-21.231-41.855-13.327-104.272 53.952-184.4 145.28-219.969 257.152C45.982 485.008 56.11 604.033 110.078 708.29c57.136 110.336 158.832 191.664 279.024 223.136 1.36.352 2.784.56 4.16.911l-81.311 41.233c-11.008 6.032-14.657 19.631-8.128 30.351l3.152 8.176c6.56 10.72 17.84 14.527 28.815 8.512L484.622 944.4c.193-.128.385-.096.578-.224l9.984-5.456c5.52-3.024 9.168-7.969 10.624-13.505 1.52-5.52.815-11.663-2.448-16.991zm416.496-577.747c-57.056-110.304-155.586-191.63-275.762-223.118-8.56-2.24-17.311-3.984-26.048-5.712l79.824-40.48c11.008-6.033 17.568-19.632 11.04-30.369l-3.153-8.16c-6.56-10.736-20.752-14.528-31.727-8.528L519.262 80.654c-.176.112-.384.08-.577.208l-9.967 5.472c-5.537 3.04-9.168 7.967-10.624 13.503-1.52 5.52-.816 11.648 2.464 16.976l5.92 9.712c.096.192.272.305.384.497l91.92 143.648c6.512 10.736 20.688 14.528 31.712 8.513l7.216-5.025c11.008-6 11.727-21.536 5.231-32.24l-59.2-91.856c13.008 2 25.968 4.416 38.624 7.76 103.232 27.04 187.393 96.864 236.4 191.568 46.32 89.519 55.024 191.695 24.48 287.728-30.511 96.047-96.655 174.448-186.174 220.816-15.233 7.887-21.168 26.607-13.28 41.87 5.519 10.64 16.335 16.768 27.599 16.768 4.8 0 9.664-1.12 14.272-3.488 104.272-53.936 181.248-145.279 216.816-257.119 35.536-111.904 25.393-230.929-28.574-335.152z"/>
                </svg>
            </span>
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
        for child in page.get('children', []):
            html += render_page_tree(child)
        html += '</ul>'
    html += '</li>'
    return html


@app.route('/refresh_page_tree/<page_id>')
def refresh_page_tree(page_id):
    try:
        # Update the node's children in the cache
        update_node_children_in_cache(page_id)
        # Re-render the page tree starting from this node
        page_tree = get_cached_page_tree()
        page = find_page_in_cache(page_id, page_tree)
        if page:
            html = render_page_tree(page)
            return jsonify({'success': True, 'html': html})
        else:
            return jsonify({'success': False, 'message': 'Page not found in cache'})
    except Exception as e:
        print(f"Error refreshing page tree for page {page_id}: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/get_sub_pages/<page_id>')
def get_sub_pages(page_id):
    sub_pages = get_sub_pages_from_cache(page_id)
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
        #get parent id from cache
        # parent = find_parent_in_cache(page_id,None)
        parent = find_parent_in_cache(page_id)
        parent_id = parent['id']
        notion.pages.update(page_id=page_id, archived=True)
        # Update cache
        update_parent_children_in_cache(parent_id)

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
        # Update cache
        update_page_name_in_cache(page_id, new_title)

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error renaming page {page_id}: {e}")
        return jsonify({'success': False})

@app.route('/duplicate_page/<page_id>', methods=['POST'])
def duplicate_page(page_id):
    try:
        # Retrieve the original page
        original_page = notion.pages.retrieve(page_id)
        parent_id = original_page['parent']['page_id']
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
        # Update cache
        update_parent_children_in_cache(parent_id)
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
        # Update cache
        update_node_children_in_cache(parent_id)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error creating subpage under {parent_id}: {e}")
        return jsonify({'success': False})