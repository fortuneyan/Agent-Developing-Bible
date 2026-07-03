# Markdown 转 eBook 完整方案

> **支持 Mermaid 流程图 + 代码高亮 + 专业排版**

---

## 📋 目录

1. [方案对比](#1-方案对比)
2. [方案一: Pandoc + Mermaid-Filter (推荐)](#1-方案一-pandoc--mermaid-filter-推荐)
3. [方案二: Marp (PPT式电子书)](#2-方案二-marp-ppt式电子书)
4. [方案三: Typora 导出](#3-方案三-typora-导出)
5. [方案四: GitBook / VitePress (在线文档)](#4-方案四-gitbook--vitepress-在线文档)
6. [方案五: 专业电子书平台](#5-方案五-专业电子书平台)

---

## 1. 方案对比

| 方案 | 优点 | 缺点 | 适用场景 | Mermaid | 代码高亮 |
|------|------|------|----------|---------|----------|
| **Pandoc + Mermaid-Filter** | 跨平台、格式多、完全免费 | 需要命令行、配置复杂 | PDF/EPUB/MOBI | ✅ 支持 | ✅ 优秀 |
| **Marp** | 简单易用、PPT风格 | 不适合长文档 | 演示文稿/短教程 | ✅ 支持 | ✅ 优秀 |
| **Typora** | 所见即所得、操作简单 | 仅付费版导出PDF | 快速预览、个人使用 | ✅ 支持 | ✅ 优秀 |
| **GitBook / VitePress** | 在线访问、可托管 | 需要编程基础 | 在线文档/官网 | ✅ 支持 | ✅ 优秀 |
| **专业平台** | 无需技术、专业排版 | 需要付费 | 商业出版 | ✅ 部分支持 | ✅ 优秀 |

---

## 2. 方案一: Pandoc + Mermaid-Filter (推荐)

### 2.1 简介

**Pandoc** 是最强大的通用文档转换器,支持 Markdown → PDF/EPUB/MOBI 等 40+ 种格式。

**Mermaid-Filter** 是 Pandoc 的插件,可以把 Mermaid 流程图转换为 SVG 图片。

### 2.2 安装步骤

#### Windows 安装

```powershell
# 1. 安装 Pandoc
# 访问 https://pandoc.org/installing.html 下载 Windows 安装包

# 2. 安装 Python (如果还没有)
# 访问 https://www.python.org/downloads/ 下载安装

# 3. 安装 mermaid-filter
pip install mermaid-filter

# 4. 安装 LaTeX (用于 PDF 渲染)
# 访问 https://www.latex-project.org/get/ 下载 MiKTeX 或 TeX Live
# 或使用较小的轻量版: https://miktex.org/download
```

#### macOS 安装

```bash
# 1. 安装 Pandoc
brew install pandoc

# 2. 安装 mermaid-filter
pip install mermaid-filter

# 3. 安装 LaTeX (用于 PDF 渲染)
brew install --cask mactex
```

### 2.3 转换命令

#### Markdown → PDF

```powershell
# 基础命令
pandoc input.md -o output.pdf --filter mermaid-filter

# 完整命令 (推荐)
pandoc input.md ^
  -o output.pdf ^
  --filter mermaid-filter ^
  --pdf-engine=xelatex ^
  -V CJKmainfont="Microsoft YaHei" ^
  -V mainfont="Arial" ^
  --highlight-style=tango ^
  --toc ^
  --toc-depth=3 ^
  -H pandoc-styles/custom-header.tex ^
  --metadata=title="AI Agent 开发指南" ^
  --metadata=author="你的名字" ^
  -N
```

#### Markdown → EPUB

```powershell
pandoc input.md ^
  -o output.epub ^
  --filter mermaid-filter ^
  --highlight-style=tango ^
  --toc ^
  --toc-depth=3 ^
  --metadata=title="AI Agent 开发指南" ^
  --metadata=author="你的名字" ^
  --metadata=lang="zh-CN" ^
  --epub-cover-image=cover.jpg ^
  -N
```

### 2.4 自定义样式

#### 创建 `pandoc-styles/custom-header.tex`

```latex
% 页面设置
\usepackage{geometry}
\geometry{
  a4paper,
  left=2.5cm,
  right=2.5cm,
  top=3cm,
  bottom=3cm
}

% 字体设置 (中文)
\usepackage{xeCJK}
\setCJKmainfont{Microsoft YaHei}
\setCJKsansfont{Microsoft YaHei}

% 标题样式
\usepackage{titlesec}
\titleformat{\section}
  {\normalfont\Large\bfseries\color{blue}}
  {\thesection}{1em}{}

\titleformat{\subsection}
  {\normalfont\large\bfseries\color{darkblue}}
  {\thesubsection}{1em}{}

% 代码块样式
\usepackage{minted}
\usemintedstyle{friendly}

% 页眉页脚
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhead[L]{AI Agent 开发指南}
\fancyhead[R]{\thepage}

% 颜色
\usepackage{xcolor}
\definecolor{darkblue}{rgb}{0,0,0.6}
\definecolor{codegray}{rgb}{0.5,0.5,0.5}
```

### 2.5 Mermaid 流程图配置

Mermaid-Filter 会自动把 Mermaid 代码块转换为 SVG 图片:

```markdown
```mermaid
graph TD
    Start((开始)) --> Thought
    Thought[思考] --> Action[行动]
    Action --> Observation[观察]
    Observation --> Decision{完成?}
    Decision -- 否 --> Thought
    Decision -- 是 --> End((结束))
```
```

转换后会自动渲染成 SVG 并嵌入 PDF/EPUB。

### 2.6 代码高亮

Pandoc 支持多种代码高亮样式:

```powershell
# 可选样式:
--highlight-style=pygments   # 默认
--highlight-style=tango      # 推荐
--highlight-style=espresso
--highlight-style=zenburn
--highlight-style=kate
--highlight-style=monochrome
--highlight-style=breezedark
--highlight-style=haddock
```

### 2.7 批量转换脚本

创建 `convert-to-pdf.ps1` (PowerShell):

```powershell
# 设置路径
$markdown_dir = "C:\Users\jike\Desktop\agent 开发指南"
$output_dir = "$markdown_dir\output"

# 创建输出目录
if (-not (Test-Path $output_dir)) {
    New-Item -ItemType Directory -Path $output_dir
}

# 获取所有 Markdown 文件
$markdown_files = Get-ChildItem -Path $markdown_dir -Filter "*.md" -Exclude "变现*.md", "营销*.md"

# 遍历并转换
foreach ($file in $markdown_files) {
    $output_file = "$output_dir\$($file.BaseName).pdf"

    Write-Host "Converting: $($file.Name) → $output_file"

    pandoc $file.FullName `
        -o $output_file `
        --filter mermaid-filter `
        --pdf-engine=xelatex `
        -V CJKmainfont="Microsoft YaHei" `
        -V mainfont="Arial" `
        --highlight-style=tango `
        --toc `
        --toc-depth=3 `
        -H "$markdown_dir\pandoc-styles\custom-header.tex" `
        --metadata=title="$($file.BaseName)" `
        --metadata=author="你的名字" `
        -N
}

Write-Host "✅ Conversion completed! Output directory: $output_dir"
```

运行:

```powershell
cd "C:\Users\jike\Desktop\agent 开发指南"
.\convert-to-pdf.ps1
```

---

## 3. 方案二: Marp (PPT式电子书)

### 3.1 简介

**Marp** 是基于 Markdown 的演示文稿工具,但也可以生成 PDF。

**优点**: 简单易用、内置 Mermaid 支持、代码高亮漂亮。

**缺点**: 不适合长文档 (适合每章单独转换)。

### 3.2 安装

```bash
# 使用 npm 安装
npm install -g @marp-team/marp-cli
```

### 3.3 转换命令

```bash
# Markdown → PDF
marp input.md --pdf --allow-local-files

# 批量转换
marp "*.md" --pdf --allow-local-files
```

### 3.4 自定义样式

创建 `.marprc.js`:

```javascript
module.exports = {
  engine: {
    standalone: true
  },
  themeSet: './theme',
  theme: 'default'
}
```

创建 `theme/default.css`:

```css
/* 字体 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700&display=swap');

section {
  font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
  font-size: 24px;
}

/* 代码块 */
pre {
  background: #2d2d2d;
  color: #f8f8f2;
  padding: 20px;
  border-radius: 8px;
}

code {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 18px;
}

/* 标题 */
h1 {
  color: #2563eb;
  font-size: 48px;
}

h2 {
  color: #1d4ed8;
  font-size: 36px;
}
```

### 3.5 Mermaid 支持

直接在 Markdown 中使用 Mermaid:

```markdown
```mermaid
graph LR
    A[开始] --> B[处理]
    B --> C[结束]
```
```

Marp 会自动渲染。

---

## 4. 方案三: Typora 导出

### 4.1 简介

**Typora** 是最好的 Markdown 编辑器之一,所见即所得。

**优点**: 操作简单、实时预览、支持 Mermaid。

**缺点**: 仅付费版支持导出 PDF、批量转换不便。

### 4.2 使用步骤

1. 打开 Typora
2. 打开 Markdown 文件
3. `文件` → `导出` → `PDF`
4. 等待渲染完成

### 4.3 配置导出设置

`文件` → `偏好设置` → `导出`:

- **PDF 引擎**: `wkhtmltopdf` 或 `Chrome`
- **页面边距**: 自定义
- **字体**: 选择支持中文的字体 (微软雅黑、思源黑体)
- **代码高亮**: 选择主题 (GitHub Dark, Atom One Dark 等)

### 4.4 Mermaid 配置

Typora 原生支持 Mermaid, 直接写 Mermaid 代码块即可。

### 4.5 批量导出

Typora 不支持批量导出,需要使用脚本自动化:

```powershell
# 自动打开 Typora 并导出 (需要配置)
# 这是一个思路, 实际实现较复杂
```

**建议**: 如果需要批量转换,使用 Pandoc 方案。

---

## 5. 方案四: GitBook / VitePress (在线文档)

### 5.1 简介

**GitBook** 和 **VitePress** 是静态站点生成器,可以把 Markdown 转换成美观的在线文档。

**优点**: 在线访问、可托管、美观、支持搜索、支持 Mermaid。

**缺点**: 需要编程基础、不能直接生成 PDF (但可以打印 PDF)。

### 5.2 GitBook 方案

#### 使用 GitBook.com (最简单)

1. 访问 https://www.gitbook.com
2. 创建新空间
3. 导入 Markdown 文件
4. GitBook 会自动渲染 Mermaid 和代码高亮

#### 使用 GitBook CLI (自托管)

```bash
# 安装 GitBook CLI
npm install -g gitbook-cli

# 初始化
gitbook init

# 写 Markdown 文件
# GitBook 会自动读取 SUMMARY.md 中的目录

# 预览
gitbook serve

# 构建
gitbook build
```

**配置 Mermaid**:

在 `book.json` 中:

```json
{
  "plugins": ["mermaid-gb3"]
}
```

安装插件:

```bash
gitbook install
```

### 5.3 VitePress 方案

#### 安装

```bash
npm create vitepress@latest my-docs
```

#### 配置

编辑 `.vitepress/config.js`:

```javascript
import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'AI Agent 开发指南',
  description: '从 Demo 到生产, 一年踩坑全记录',

  themeConfig: {
    sidebar: [
      {
        text: '模块一: 基础设施',
        items: [
          { text: '第 1 章: AI 平台与 API Key 管理', link: '/ch01-api-key-management' },
          { text: '第 2 章: Context 与 Prompt 管理', link: '/ch02-context-management' },
          // ...
        ]
      },
      // ...
    ]
  },

  markdown: {
    config: (md) => {
      md.use(require('markdown-it-mermaid'))
    }
  }
})
```

#### 安装依赖

```bash
npm install markdown-it-mermaid
```

#### 构建

```bash
npm run dev      # 开发模式
npm run build    # 构建静态站点
```

#### 导出 PDF

在浏览器中打开 `http://localhost:5173`, 然后打印为 PDF。

### 5.4 优势

- **在线访问**: 读者可以在任何设备上阅读
- **可托管**: 可以托管在 GitHub Pages、Vercel、Netlify
- **美观**: 自带主题, 可以自定义
- **搜索**: 内置搜索功能
- **更新方便**: 修改 Markdown 文件后重新构建即可

---

## 6. 方案五: 专业电子书平台

### 6.1 推荐平台

#### 1. **掘金小册**

- **URL**: https://juejin.cn/books
- **特点**:
  - 国内最大的技术社区
  - 支持 Markdown
  - 自动渲染代码高亮
  - 不支持 Mermaid (需要转换成图片)
  - 收入分成高
- **流程**:
  1. 提交申请
  2. 审核通过后创建小册
  3. 复制 Markdown 内容
  4. 发布

#### 2. **GitBook / Read the Docs**

- **URL**: https://www.gitbook.com, https://readthedocs.org
- **特点**:
  - 专业的文档平台
  - 支持 Mermaid
  - 支持代码高亮
  - 可以导出 PDF
- **流程**:
  1. 注册账号
  2. 导入 Git 仓库
  3. 自动构建站点

#### 3. **Leanpub**

- **URL**: https://leanpub.com
- **特点**:
  - 专业的电子书发布平台
  - 支持 Markdown
  - 支持 Mermaid (需手动转换)
  - 支持 EPUB/PDF/MOBI
  - 有收入分成
- **流程**:
  1. 注册账号
  2. 创建新书
  3. 上传 Markdown 文件
  4. 配置样式
  5. 发布

#### 4. **Gumroad**

- **URL**: https://gumroad.com
- **特点**:
  - 简单易用的销售平台
  - 支持 PDF
  - 支持付费下载
  - 可以自定义价格
- **流程**:
  1. 注册账号
  2. 创建产品
  3. 上传 PDF 文件
  4. 设置价格
  5. 发布

### 6.2 Mermaid 图片转换

如果平台不支持 Mermaid, 可以先转换成图片:

#### 方法一: 使用 Mermaid CLI

```bash
# 安装
npm install -g @mermaid-js/mermaid-cli

# 转换
mmdc -i input.mmd -o output.png -t dark -b transparent
```

#### 方法二: 使用在线工具

- https://mermaid.live/ (官方在线编辑器)
- https://mermaid-js.github.io/mermaid-live-editor/

#### 方法三: 使用 Pandoc (推荐)

```bash
# 先转换成带图片的 Markdown
pandoc input.md -o output.md --filter mermaid-filter

# 然后再上传到平台
```

---

## 7. 推荐方案总结

### 7.1 个人使用

**推荐**: **Typora** (快速预览) 或 **Pandoc** (批量转换)

### 7.2 付费电子书 (PDF/EPUB/MOBI)

**推荐**: **Pandoc + Mermaid-Filter**

**原因**:
- 完全免费
- 支持所有格式
- 批量转换
- 高度自定义
- 支持中文

### 7.3 在线文档

**推荐**: **VitePress** 或 **GitBook**

**原因**:
- 美观
- 支持 Mermaid
- 可以托管
- 可以搜索
- 更新方便

### 7.4 技术平台发布

**推荐**: **掘金小册** 或 **Leanpub**

**原因**:
- 有收入分成
- 流量大
- 读者信任度高

---

## 8. 快速上手 (5 分钟)

### 8.1 快速转换单个文件 (Pandoc)

```powershell
# 1. 安装依赖
choco install pandoc
pip install mermaid-filter

# 2. 转换
pandoc "01_Agent开发指南_AI平台和api-key管理.md" `
  -o "01_Agent开发指南_AI平台和api-key管理.pdf" `
  --filter mermaid-filter `
  --pdf-engine=xelatex `
  -V CJKmainfont="Microsoft YaHei" `
  --highlight-style=tango
```

### 8.2 批量转换所有章节

```powershell
# 使用我提供的脚本
cd "C:\Users\jike\Desktop\agent 开发指南"
.\convert-to-pdf.ps1
```

### 8.3 在线预览 (VitePress)

```bash
# 1. 创建项目
npm create vitepress@latest agent-guide

# 2. 复制 Markdown 文件到 docs/

# 3. 配置 .vitepress/config.js

# 4. 预览
cd agent-guide
npm run dev
```

---

## 9. 常见问题

### Q1: Mermaid 流程图不显示怎么办?

**A**: 检查是否安装了 `mermaid-filter`:

```bash
pip install mermaid-filter
```

### Q2: 中文字体不显示怎么办?

**A**: 在 Pandoc 命令中指定中文字体:

```powershell
-V CJKmainfont="Microsoft YaHei"
```

### Q3: 代码高亮不漂亮怎么办?

**A**: 尝试不同的高亮样式:

```powershell
--highlight-style=tango
--highlight-style=zenburn
--highlight-style=monokai
```

### Q4: 如何批量转换?

**A**: 使用我提供的 `convert-to-pdf.ps1` 脚本。

### Q5: 如何生成 EPUB/MOBI?

**A**: 使用 Pandoc:

```powershell
# 生成 EPUB
pandoc input.md -o output.epub --filter mermaid-filter

# 生成 MOBI (需要 Calibre)
pandoc input.md -o output.epub --filter mermaid-filter
ebook-convert output.epub output.mobi
```

---

## 10. 资源链接

- Pandoc 官方文档: https://pandoc.org/MANUAL.html
- Mermaid 官方文档: https://mermaid.js.org/
- Marp 官方文档: https://marp.app/
- Typora 官方文档: https://support.typora.io/
- VitePress 官方文档: https://vitepress.vuejs.org/
- GitBook 官方文档: https://docs.gitbook.com/

---

**最后建议**:

如果你需要**批量转换成 PDF/EPUB** → 使用 **Pandoc + Mermaid-Filter**

如果你需要**在线预览** → 使用 **VitePress**

如果你需要**在技术平台发布** → 使用 **掘金小册** 或 **Leanpub**

---

**祝转换顺利! 📚**
