# CV Intake

简历接收、OCR 提取、结构化解析、联网核验、岗位评分和面试题生成的一体化服务。

核心链路：

`上传 PDF -> 写入数据库 -> 投递 RQ Worker -> OCR -> LangGraph Workflow -> 持久化结果 -> SSE 推送前端`

## 功能概览

- 上传 PDF 简历
- 提取 PDF 文本
- 抽取结构化简历信息
- 联网核验学校、公司和工作时间
- 根据岗位描述输出总分和分项评分
- 生成面试题结果
- 将中间状态和最终结果写入 SQLite
- 通过 SSE 实时推送处理结果

## 技术栈

- 后端：FastAPI
- 数据库：SQLite + SQLAlchemy 2.x
- 迁移：Alembic
- 异步任务：Redis + RQ
- 工作流：LangGraph
- 模型调用：LLM + `zai-sdk` Web Search
- 前端：Next.js + React Query

## 目录结构

```text
.
├── api/
│   ├── main.py                    # FastAPI 应用装配
│   ├── routers/                   # jobs / cvs / upload / settings / sse
│   ├── services/                  # 上传服务、队列、CV 处理服务
│   ├── utils/                     # 文件存储、仓储、序列化、PDF 文本处理
│   └── workers/                   # RQ worker 入口
├── database/
│   ├── main.py                    # engine / session / migration bootstrap
│   ├── models/                    # SQLAlchemy ORM 模型
│   └── schemas/                   # Pydantic 请求/响应模型
├── workflow/
│   ├── run.py                     # LangGraph 工作流装配
│   ├── state.py                   # Workflow 状态定义
│   ├── llm.py                     # LLM 封装
│   ├── node/                      # summary / verify / score / interview
│   └── tools/                     # Web Search 工具
├── config/
│   └── app.py                     # 读取 config.yaml
├── utils/
│   ├── log.py                     # 日志
│   └── sse_conn.py                # SSE 发布订阅
├── web/
│   ├── app/http/                  # React Query API hooks
│   ├── app/cv/                    # CV 列表页与详情页
│   ├── app/_layout/               # 侧边栏、设置、上传弹窗
│   └── components/ui/             # 通用 UI 组件
├── alembic/                       # 数据库迁移
├── public/                        # 上传后的 PDF 公共目录
├── config.yaml                    # 项目配置
└── main.py                        # 后端启动入口
```

## 系统流程

### 1. 上传

入口：[api/routers/upload.py](/Users/admin/Desktop/cv-intake/api/routers/upload.py:1)

流程：

1. 接收 `files` 和 `job_id`
2. 校验岗位是否存在
3. 保存 PDF 到 `public/cvs/`
4. 写入 `cvs` 记录
5. 立即返回上传结果
6. 将任务投递到 Redis/RQ 队列
7. 通过 SSE 向前端推送初始状态

### 2. Worker 处理

入口：

- [api/workers/worker.py](/Users/admin/Desktop/cv-intake/api/workers/worker.py:1)
- [api/workers/cv_worker.py](/Users/admin/Desktop/cv-intake/api/workers/cv_worker.py:1)
- [api/services/cv_processing_service.py](/Users/admin/Desktop/cv-intake/api/services/cv_processing_service.py:1)

流程：

1. Worker 从 Redis 队列消费任务
2. 提取 PDF 文本
3. 更新 `processing_stage`
4. 执行工作流
5. 将每个阶段结果写回数据库
6. 通过 SSE 持续推送更新

### 3. Workflow

入口：[workflow/run.py](/Users/admin/Desktop/cv-intake/workflow/run.py:1)

当前节点顺序：

1. `SummaryNode`
2. `VerifyNode`
3. `ScoreNode`
4. `InterviewNode`

状态定义见 [workflow/state.py](/Users/admin/Desktop/cv-intake/workflow/state.py:1)。

关键字段：

- `cv_id`
- `cv_name`
- `resume_text`
- `job_text`
- `resume_summary`
- `verify_result`
- `score_result`
- `interview_result`
- `final_answer`
- `processing_stage`
- `error`

### 4. 节点职责

`SummaryNode`
- 输入 OCR 文本
- 输出结构化简历摘要

`VerifyNode`
- 消费 `resume_summary`
- 调用 `zai-sdk` 搜索学校和公司
- 生成核验结果

`ScoreNode`
- 结合 `job_text + resume_summary + verify_result`
- 输出总分、分项分数和原因

`InterviewNode`
- 基于前序结果生成面试问题或面试结果结构

## 数据模型

### ORM

数据库模型位于：

- [database/models/cv.py](/Users/admin/Desktop/cv-intake/database/models/cv.py:1)
- [database/models/job.py](/Users/admin/Desktop/cv-intake/database/models/job.py:1)
- [database/models/settings.py](/Users/admin/Desktop/cv-intake/database/models/settings.py:1)

说明：

- `database.models.*` 只用于数据库查询和写入
- `database.schemas.*` 只用于接口请求和响应校验

### 主要表

`cvs`
- `id`
- `filename`
- `job_id`
- `job_name`
- `file_path`
- `md5`
- `status`
- `processing_stage`
- `processing_attempt`
- `resume_text`
- `resume_summary`
- `verify_result`
- `score_result`
- `interview_result`
- `final_answer`
- `created_at`
- `updated_at`

`jobs`
- `id`
- `label`
- `description`

`settings`
- `model`
- `temperature`
- `api_key`
- `base_url`
- `zhipu_search_api_key`

## API

### Jobs

- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs`
- `PUT /jobs/{job_id}`
- `DELETE /jobs/{job_id}`

### CVs

- `GET /cvs`
- `GET /cvs/{cv_id}`
- `POST /cvs`
- `PUT /cvs/{cv_id}`
- `DELETE /cvs/{cv_id}`

### Upload

- `POST /upload`

表单字段：

- `files`
- `job_id` 或 `job_ids`

### Settings

- `GET /settings`
- `PUT /settings`

### SSE

- `GET /sse?type=results`

前端监听 `results` 事件来同步 CV 状态变化。

## 前端

前端位于 `web/`，使用 Next.js 和 React Query。

主要入口：

- [web/app/http/useApi.ts](/Users/admin/Desktop/cv-intake/web/app/http/useApi.ts:1)
- [web/app/http/type.ts](/Users/admin/Desktop/cv-intake/web/app/http/type.ts:1)
- [web/app/cv/page.tsx](/Users/admin/Desktop/cv-intake/web/app/cv/page.tsx:1)
- [web/app/cv/[id]/page.tsx](/Users/admin/Desktop/cv-intake/web/app/cv/[id]/page.tsx:1)
- [web/app/_layout/app-sidebar.tsx](/Users/admin/Desktop/cv-intake/web/app/_layout/app-sidebar.tsx:1)
- [web/app/utils/status.ts](/Users/admin/Desktop/cv-intake/web/app/utils/status.ts:1)

前端功能：

- 岗位管理
- 模型设置管理
- PDF 上传
- 简历列表
- 简历详情页
- SSE 实时更新

详情页包含：

- PDF 预览
- 摘要
- 核验结果
- 评分结果
- 面试题/面试结果
- OCR 原文

## 运行方式

### 1. 安装后端依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 启动 Redis

```bash
redis-server
```

### 3. 初始化数据库

```bash
python -m alembic upgrade head
```

### 4. 启动 API

```bash
python main.py
```

### 5. 启动 Worker

```bash
python -m api.workers.worker
```

### 6. 启动前端

```bash
cd web
pnpm install
pnpm dev
```

## 配置

配置文件：[config.yaml](/Users/admin/Desktop/cv-intake/config.yaml:1)

当前包含：

- `app`
- `llm`
- `zhipu`
- `server`
- `worker`

关键项：

- `llm.model`
- `llm.api_key`
- `llm.base_url`
- `zhipu.api_key`
- `worker.redis_url`
- `worker.queue_name`

## 状态说明

`cvs.status` 常见值：

- `queued`
- `processing`
- `processed`
- `ocr_no_text`
- `skipped_duplicate_md5`
- `skipped_empty_file`
- `skipped_non_pdf`
- `error`

`processing_stage` 常见值：

- `queued`
- `ocr`
- `summary`
- `verify`
- `score`
- `interview`
- `ocr_no_text`
- `error`

## 当前限制

- Worker 依赖 Redis/RQ
- `VerifyNode` 依赖外网搜索能力
- `SummaryNode`、`ScoreNode`、`InterviewNode` 依赖模型接口可用
- 简历结构化和核验结果仍然主要依赖大模型输出质量
