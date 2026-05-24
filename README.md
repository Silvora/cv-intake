# CV Intake

一个用于简历接收、PDF 文本提取、结构化解析、联网核验和岗位评分的简历处理系统。

核心链路：

`上传 PDF -> OCR 提取文本 -> Summary 抽取 -> Verify 核验 -> Score 打分 -> 写入 SQLite -> SSE 推送前端`

## 功能

- 上传 PDF 简历
- 提取 PDF 文本
- 抽取结构化简历信息
- 联网核验学校、公司和工作时间
- 根据岗位描述输出 0-100 分评分
- 保存中间结果和最终结果到数据库
- 通过 SSE 推送处理状态

## 目录

```text
.
├── api/                    # FastAPI 路由
│   └── routers/
│       ├── job.py          # 岗位接口
│       ├── upload.py       # 上传 + 异步工作流
│       ├── cv.py           # 简历查询接口
│       └── sse.py          # SSE 推送
├── config.yaml             # 应用和模型配置
├── db/                     # SQLite 与 ORM
├── public/                 # 前端可访问的文件
├── utils/                  # PDF、存储、SSE、日志
├── workflow/               # Summary / Verify / Score 工作流
└── web/                    # Next.js 前端
```

## 后端流程

### 上传

入口：[api/routers/upload.py](/Users/admin/Desktop/cv-intake/api/routers/upload.py:1)

1. 接收 `job_id` 和多个 PDF
2. 保存文件基础信息
3. 写入 `cvs` 表
4. 立即返回
5. 后台异步跑 OCR 和工作流

### 工作流

入口：[workflow/run.py](/Users/admin/Desktop/cv-intake/workflow/run.py:1)

顺序：

1. `SummaryNode`
2. `VerifyNode`
3. `ScoreNode`

关键状态字段：

- `resume_text`
- `job_text`
- `resume_summary`
- `verify_result`
- `score_result`
- `final_answer`

### 节点说明

`SummaryNode`：
- 输入 OCR 文本
- 输出结构化简历摘要

`VerifyNode`：
- 读取 `resume_summary`
- 使用 `zai-sdk` 的 `web_search`
- 联网查询学校和公司
- 输出核验结果

`ScoreNode`：
- 读取 `job_text + resume_summary + verify_result`
- 输出总分、分项分数和原因

## 数据库

核心表是 `cvs`，定义在 [db/models.py](/Users/admin/Desktop/cv-intake/db/models.py:1)。

主要字段：

- `filename`
- `job_id`
- `job_name`
- `file_path`
- `resume_text`
- `job_text`
- `resume_summary`
- `verify_result`
- `score_result`
- `final_answer`
- `status`
- `error`

说明：

- `cv_id` 由岗位和文件内容共同决定
- 同一份简历投不同岗位会生成独立记录

## 前端

前端使用 Next.js + React Query。

主要入口：

- [web/app/http/useApi.ts](/Users/admin/Desktop/cv-intake/web/app/http/useApi.ts:1)
- [web/app/cv/page.tsx](/Users/admin/Desktop/cv-intake/web/app/cv/page.tsx:1)
- [web/app/cv/[id]/page.tsx](/Users/admin/Desktop/cv-intake/web/app/cv/[id]/page.tsx:1)
- [web/app/_layout/app-sidebar.tsx](/Users/admin/Desktop/cv-intake/web/app/_layout/app-sidebar.tsx:1)
- [web/app/utils/status.ts](/Users/admin/Desktop/cv-intake/web/app/utils/status.ts:1)

页面结构：

- 左侧列表：简历记录
- 详情页：PDF、摘要、核验、评分、原文
- 评分区块：总分 + 分项评分 + 颜色分段

## API

- `GET /jobs`
- `GET /cvs`
- `GET /cvs/{id}`
- `POST /upload`
- `GET /sse?type=results`

## 运行

后端：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

前端：

```bash
cd web
pnpm install
pnpm dev
```

## 配置

配置文件：[config.yaml](/Users/admin/Desktop/cv-intake/config.yaml:1)

建议把真实 API Key 放到本地配置，不要长期硬编码进仓库。

## 状态

常见 `cvs.status`：

- `queued`
- `processing`
- `processed`
- `ocr_no_text`
- `skipped_duplicate_md5`
- `skipped_empty_file`
- `skipped_non_pdf`
- `error`

## 限制

- 上传后工作流是异步执行的
- `VerifyNode` 依赖外网搜索能力
- `ScoreNode` 依赖模型接口可用
