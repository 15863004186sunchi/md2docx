# md2docx

将 Markdown 文档按标题映射填充到 Word 模板（`.docx`）中，支持 Mermaid 代码块转图片后插入。

产品迭代计划：`docs/产品迭代计划-2026Q2.md`

## 1. 安装

```bash
cd project/md2docx
pip install -e .
```

如果你需要 Mermaid 渲染，请先安装 Node.js 并安装 `mmdc`：

```bash
npm i -g @mermaid-js/mermaid-cli
```

## 1.1 Docker Compose（容器化）

```bash
cd project/md2docx
docker compose build
```

先在容器里生成示例模板，再执行转换：

```bash
docker compose run --rm md2docx-cli python examples/generate_template.py
docker compose run --rm md2docx-cli md2docx convert -i examples/sample.md -t examples/template.docx -o out/demo_compose.docx -c examples/config.yaml -r out/demo_compose.report.json
```

启动 Web 服务（推荐部署方式）：

```bash
docker compose up -d md2docx-web
```

浏览器访问：`http://<服务器IP>:8080/`

停止服务：

```bash
docker compose down
```

## 2. 快速开始

```bash
md2docx convert \
  -i examples/sample.md \
  -t /path/to/template.docx \
  -o /path/to/output.docx \
  -c examples/config.yaml \
  -r /path/to/report.json
```

本仓库也提供了可直接演示的模板生成脚本：

```bash
python examples/generate_template.py
md2docx convert -i examples/sample.md -t examples/template.docx -o out/demo.docx -c examples/config.yaml -r out/demo.report.json
```

## 2.1 Web 版本（非容器）

```bash
python -m pip install -e .
python -m uvicorn md2docx.web:app --host 0.0.0.0 --port 8080
```

打开 `http://127.0.0.1:8080/`，上传 `md + docx` 后下载结果 ZIP。

API 端点：

- `GET /health`：健康检查
- `POST /api/convert`：multipart 上传转换（返回 ZIP）

## 2.2 谷歌云服务器部署建议

```bash
git clone <your-repo-url>
cd md2docx/project/md2docx
docker compose up -d --build md2docx-web
```

服务器防火墙放行 `8080` 端口后，即可公网访问 Web 页面。
如需容器内 Mermaid 无沙箱启动，已内置 `puppeteer-config.json` 并通过环境变量 `MD2DOCX_MMDC_PUPPETEER_CONFIG` 自动启用。

### CentOS 10 一键部署脚本

已提供脚本：`deploy/gcp-centos10-deploy.sh`

在 GCP CentOS 10 服务器执行：

```bash
curl -fsSL https://raw.githubusercontent.com/<你的用户名>/<仓库名>/main/project/md2docx/deploy/gcp-centos10-deploy.sh -o gcp-centos10-deploy.sh
chmod +x gcp-centos10-deploy.sh
REPO_URL="https://github.com/<你的用户名>/<仓库名>.git" BRANCH="main" bash gcp-centos10-deploy.sh
```

可选参数：
- `DEPLOY_ROOT`（默认 `/opt/md2docx`）
- `APP_SUBDIR`（默认 `project/md2docx`）
- `SERVICE_NAME`（默认 `md2docx-web`）
- `EXPOSE_PORT`（默认 `8080`）

## 3. 模板约定（MVP）

- 模板必须使用标准标题样式（例如 `Heading 1/2/3`，或中文 `标题 1/2/3`）。
- Markdown 标题与模板标题建议保持一致（支持编号自动规范化）。
- 默认替换策略为 `replace`：每个标题后到下一个标题前的内容会被替换。
- 可配置 `match.duplicate_policy`：`first`（取第一个）、`error`（标记歧义）、`by_level`（按标题级别唯一匹配）。

## 4. 主要特性

- 标题匹配：路径精确匹配优先，其次标题精确匹配，最后可选模糊匹配。
- Mermaid 渲染：识别 ```` ```mermaid ```` 代码块并调用 `mmdc` 生成图片插入。
- 转换报告：输出 `summary/matched/ambiguous/unmatched/warnings/mermaid_failures`。

## 5. 已知限制

- MVP 不处理复杂表格、页眉页脚动态填充、目录字段自动刷新。
- 当模板重名标题在 `by_level` 下仍无法唯一确定时，会保留为歧义并写入候选标题路径。

## 6. 推送到 GitHub

```bash
git init
git add .
git commit -m "feat: add web service and docker deployment for md2docx"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```
