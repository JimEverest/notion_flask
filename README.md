# notion_flask
基于 Notion API 构建一套自定义的 Web Flask应用程序

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


# 项目概述
该项目旨在使用Notion API构建一个自定义的Flask Web应用程序，使用户能够访问、编辑和管理Notion中的笔记。重点是支持各种Notion块类型，提供良好的用户体验，并保持界面的简洁性。

# 需求和功能规划
## 1. 基本功能
浏览、查看、创建和编辑Notion笔记。
支持多种Notion块类型的显示和编辑，包括文本、图片、音频、待办事项等。
提供一个富文本编辑器（如CKEditor）来实现所见即所得的编辑体验。
## 2. 用户管理

账户登录和权限验证机制。
通过config文件管理用户凭据（初期简单，后期考虑JWT等更安全的方案）。
## 3. 界面设计

页面布局：左侧为页面列表，右侧为内容编辑区。
侧边栏支持折叠和展开，默认只加载根页面，点击时动态加载子页面。
界面简洁大方，符合极简主义设计风格。
## 4. 性能优化

加载特定页面时，只请求该页面的数据，不遍历所有子页面以提高响应速度。
## 5. 块类型转换

设计一套完善的块类型转换机制，将Notion块与CKEditor中的内容格式进行转换，确保操作的可逆性。

# 技术栈
后端: Python Flask
前端: HTML, CSS, JavaScript（使用CKEditor）
数据库: 使用Notion API进行数据存储
文件存储: 使用Minio（OSS）上传和管理文件。


# 开发计划（In Agile）
- 迭代1: 
    - 基础架构
    - 搭建Flask应用基本结构。
    - 实现用户登录和基本权限控制。
- 迭代2: 
    - 基本功能实现
    - 实现页面的创建、查看、编辑功能。
    - 集成CKEditor，支持基本文本和图片编辑。
-  迭代3: 
    - 块类型支持
    - 完善块类型转换，支持更多Notion块（如to-do, callout, audio等）。
    - 优化块的显示效果和功能。

- 迭代4: 
    - 性能优化与用户体验
    - 优化页面加载性能，改进UI设计。
    - 根据用户反馈进一步调整和完善功能。


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
- [ ] **Block显示:** 确保CKEditor的配置和所需插件都已正确设置，并对特殊元素（如音频、checkbox）进行特殊处理。
- [ ] **Submit** 
- [ ] **Diary** 
- [ ] **AI Copilot** 
- [ ] **文件上传** 
- [ ] **新建page** 
- [ ] **Weekly recap** 