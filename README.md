# notion_flask
A Flask web application that integrates with the Notion API to display and manage Notion pages in a web interface. This app allows users to view, edit, and organize Notion pages with features like page tree navigation, breadcrumbs, caching for improved performance, and basic page operations.

# Request Limits
> https://developers.notion.com/reference/request-limits

2000 characters
Limits for property values

| Property value type	 |    Size limit| 
| ----------- | ----------- |
| Any URL	        |         2000 characters | 
| Any email	        |     200 characters | 
| Any phone number	|     200 characters | 
| Any multi-select	|     100 options | 

# Features
1. User Authentication and Roles: Supports multiple user roles with configurable permissions.
2. View and Edit Pages: Display and edit Notion pages directly from the web interface.
3. Page Tree Navigation: Collapsible page tree in the sidebar for easy navigation.
4. Breadcrumb Navigation: Displays the hierarchy of the current page for context.
5. Page Operations: Create, rename, duplicate, and delete pages.
6. Caching Mechanism: Improves performance by caching page data and minimizing API calls.
7. Image Uploading: Upload images and embed them into pages.
8. Responsive Design: Mobile-friendly and responsive user interface.


# Installation
## Prerequisites
- Python 3.6+
- pip (Python package installer)
- Notion Integration Token: You need to create an integration at Notion Developers and obtain a token.
- AWS S3 Account (optional, for image uploads): If you want to enable image uploading, you'll need AWS credentials and an S3 bucket.

## Steps
1.  Clone the Repository
    ```
    git clone https://github.com/yourusername/notion-flask-app.git
    cd notion-flask-app
    ```
2.  Create a Virtual Environment
    ```
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
3. Install Dependencies
    ```
    pip install -r requirements.txt
4. Set Up Configuration
- Copy the Example Configuration File
    ```
    cp app/config/config.example.json app/config/config.json
    ```
- Edit config.json

Open app/config/config.json and update the following fields:

        - notion_token: Your Notion integration token.
        - pages: A list of root page IDs you want to include.

            ```
            "pages": [
            {
                "page_id": "YOUR_ROOT_PAGE_ID"
            }
            ]
            ```
        - roles: Define user roles and permissions.
        ```

        "roles": {
        "admin": {
            "operation": ["read", "write", "execute"]
        },
        "user": {
            "operation": ["read"]
        }
        }
        ```
        - users: Define user credentials and roles.

json
```
"users": [
  {
    "username": "admin",
    "password": "admin_password",
    "role": "admin"
  },
  {
    "username": "user",
    "password": "user_password",
    "role": "user"
  }
]
```
- AWS S3 Configuration (optional):
```
        "aws_access_key_id": "YOUR_AWS_ACCESS_KEY_ID",
        "aws_secret_access_key": "YOUR_AWS_SECRET_ACCESS_KEY",
        "aws_bucket_name": "YOUR_AWS_S3_BUCKET_NAME",
        "aws_region": "YOUR_AWS_REGION"
```
- cache_expiry (optional): Cache expiration time in seconds (default is 3600 seconds or 1 hour).

5. Set the Secret Key

    Open app/__init__.py and set a secret key for session management:
    ```
    app.config['SECRET_KEY'] = 'your_secret_key'
    ```
6. Run the Application
    ```
    flask run
    ```
The application will be available at http://127.0.0.1:5000/.

# Application Structure
```
notion-flask-app/
├── app/
│   ├── __init__.py
│   ├── routes.py
│   ├── notion_parser.py
│   ├── notion_cache.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── page.html
│   ├── static/
│   │   ├── styles.css
│   │   ├── script.js
│   ├── config/
│   │   ├── config.example.json
│   │   ├── config.json
├── requirements.txt
├── README.md
```

- app/__init__.py: Initializes the Flask application.
- app/routes.py: Defines the routes and views.
- app/notion_parser.py: Contains functions to interact with the Notion API and parse content.
- app/notion_cache.py: Implements the caching mechanism.
- app/templates/: Contains HTML templates for rendering views.
- app/static/: Contains static files like CSS and JavaScript.
- app/config/config.json: Configuration file for the application.

# 技术栈
后端: Python Flask
前端: HTML, CSS, JavaScript（使用CKEditor）
数据库: 使用Notion API进行数据存储
文件存储: 使用Minio（OSS）上传和管理文件。

# Configuration
Notion Integration Token

    - Create an integration at Notion Developers.
    - Share the pages you want to access with your integration.
    - Obtain the integration token and set it in config.json.

config.json File

This file contains all the configuration settings for the application, including Notion integration, user roles, and caching settings.

    - notion_token: Your Notion integration token.
    - pages: A list of root pages to include in the application.
    - roles: Define user roles and permissions.
    - users: Define user credentials and their roles.
    - cache_expiry: Cache expiration time in seconds.
    - AWS S3 Configuration: Required if you enable image uploading.
# Usage
Login and Roles

    - Login Page: Access the login page at http://127.0.0.1:5000/login.
    - Credentials: Use the username and password defined in config.json.
    - Roles and Permissions: User permissions are determined by their assigned role.

Viewing Pages

    - Page Tree: After logging in, the sidebar displays the page tree.
    - Navigate: Click on any page to view its content.
    - Content Rendering: The content is fetched from the corresponding Notion page.

Editing Pages

    - Permissions: Only users with write permissions can edit pages.
    - Editor: An HTML editor is provided for editing page content.
    - Save Changes: Click "Save" to update the content on Notion.

Page Tree Navigation

    - Collapsible Tree: The sidebar displays a collapsible page tree.
    - Expand/Collapse: Click the chevron icons to expand or collapse sections.
    - Refresh: Use the refresh icon to reload a page's children from Notion.

Breadcrumb Navigation

    - Hierarchy Display: Breadcrumbs at the top of each page show the navigation path.
    - Clickable: Breadcrumb items are clickable for quick navigation.

Page Operations

    - Create New Page: Click the plus icon next to a page to create a sub-page.
    - Rename Page: Use the dots menu to rename a page.
    - Duplicate Page: Use the dots menu to duplicate a page.
    - Delete Page: Use the dots menu to delete a page.

Image Uploading

    - Upload Images: Use the image upload feature to add images to pages.
    - AWS S3: Images are uploaded to AWS S3 and embedded into the page content.

Caching Mechanism

The application implements a caching mechanism to improve performance by reducing the number of API calls to Notion.
How It Works

    - Cache Structure: A nested data structure that mirrors the page tree.
    - Cached Data: Includes page titles, page tree, and content.
    - Expiration: Cache entries expire based on the cache_expiry setting.

Cache Updates

    - Page Operations: The cache is updated when pages are created, renamed, duplicated, or deleted.
    - Manual Refresh: Users can refresh a page or the entire tree using the refresh icons.
    - Automatic Refresh: Cache entries refresh automatically after the expiration time.

Benefits

    - Performance: Reduces load times by minimizing API calls.
    - Efficiency: Ensures that data is up-to-date without unnecessary network requests.

# Notion API Integration
    Notion SDK: The application uses the official Notion SDK for Python.
    API Calls: Interacts with Notion to retrieve and update pages.
    Permissions: Ensure your Notion integration has access to the necessary pages.

# Notes
    Security: Keep your Notion token and AWS credentials secure.
    Error Handling: Check the console or logs for error messages during development.
    Customization: Feel free to customize the templates and styles to fit your needs.
    Limitations: The app does not support all Notion features (e.g., databases, complex blocks).

# 具体技术细节
## 1. 块类型处理:
创建一个专门的模块（如notion_parser.py），负责处理不同块类型的转换逻辑。
确保在编辑器中每种块类型都能正确显示和操作，并在保存时能将其转换回Notion API所需的格式。
## 2. CKEditor配置:
引入必要的CKEditor插件以支持代码块、音频等功能，确保工具栏能够正常显示。

## 3. 文件上传处理:
实现文件上传功能，将文件保存到Minio，并返回文件的公开URL。

## 4. 用户认证:
初期可以使用简单的配置文件来管理用户信息，后期考虑集成更复杂的认证机制（如JWT）。

# CKeditor super build features: 
> Demo: https://ckeditor.com/ckeditor-5/demo/?utm_source=google&utm_medium=ppc&utm_campaign=sitelink_demo&utm_term=ckeditor%20online%20demo&utm_content=demos&ppc_keyword=ckeditor%20online%20demo&utm_term=ckeditor%20online%20demo&utm_campaign=%5BS%5D+Branded+US-CA&utm_source=adwords&utm_medium=ppc&hsa_acc=7316756744&hsa_cam=16047152104&hsa_grp=130110378942&hsa_ad=656713827592&hsa_src=g&hsa_tgt=kwd-965758288312&hsa_kw=ckeditor%20online%20demo&hsa_mt=p&hsa_net=adwords&hsa_ver=3&gad_source=1&gclid=Cj0KCQjw7Py4BhCbARIsAMMx-_LZ7NqvFL8yZrFwzFvHGvi88a8wJdbWl9_ia9xkhUPdfnuXbE-qTAAaAjMREALw_wcB

> https://ckeditor.com/docs/ckeditor5/latest/getting-started/legacy/installation-methods/predefined-builds.html#available-builds

> https://ckeditor.com/docs/ckeditor5/latest/getting-started/legacy/installation-methods/quick-start.html#running-a-full-featured-editor-from-cdn
 

# 问题（Todo）
针对具体问题（如页面加载速度、block显示不正常等），需要逐步调试和修复：
- [x] **加载性能:** 确保只在必要时请求API数据，避免重复请求。
- [x] **Block显示:** 确保CKEditor的配置和所需插件都已正确设置，并对特殊元素（如音频、checkbox）进行特殊处理。
- [x] **Submit** 
- [ ] **Diary** 
- [ ] **AI Copilot** 
- [ ] **文件上传** 
- [x] **新建page** 
- [ ] **Weekly recap** 
- [ ] **Page tree cache** 

# Acknowledgments

    Notion: For providing an API to interact with their platform.
    Flask: For being an excellent web framework for Python.
    CKEditor: For the rich text editor used in the application.