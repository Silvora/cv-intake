# CV Intake

一个用于简历接收、PDF 文本提取、结构化解析、信息核验和岗位匹配评分的简历处理系统。

当前后端基于 FastAPI，工作流基于 LangGraph + LLM，前端基于 Next.js。核心链路已经打通：

`上传 PDF -> OCR 提取文本 -> Summary 抽取 -> Verify 核验 -> Score 打分 -> 写入 SQLite -> SSE 推送前端`

## 功能概览

- 上传 PDF 简历
- 提取 PDF 文本
- 将简历抽取为结构化数据
- 对学校、公司和工作时间做联网核验
- 根据岗位描述对候选人进行 0-100 分评分
- 将 OCR、中间结果、最终评分统一写入数据库
- 通过 SSE 向前端推送处理进度和结果

## 目录结构

```text
.
├── api/                    # FastAPI 路由和服务入口
│   ├── run.py              # FastAPI 应用装配
│   └── routers/
│       ├── job.py          # 岗位管理接口
│       ├── upload.py       # PDF 上传 + OCR + workflow 编排
│       ├── cv.py           # 简历记录查询/更新/删除
│       └── sse.py          # SSE 实时推送
├── config/
│   └── app.py              # 读取 config.yaml
├── db/
│   ├── database.py         # SQLite 连接
│   ├── models.py           # Jobs / Cvs 表模型与迁移
│   └── cv.db               # 本地数据库
├── utils/
│   ├── cv_store.py         # 简历文件落盘、去重、状态写库
│   ├── pdf_text.py         # PDF 文本提取
│   ├── sse_conn.py         # SSE 发布订阅
│   └── log.py              # 日志配置
├── workflow/
│   ├── run.py              # LangGraph 工作流装配与统一入口
│   ├── state.py            # 工作流共享状态
│   ├── llm.py              # LLM 客户端
│   └── node/
│       ├── summary.py      # 简历结构化抽取
│       ├── verify.py       # 联网信息核验
│       └── score.py        # 岗位匹配评分
├── web/                    # Next.js 前端
├── main.py                 # 后端启动入口
├── config.yaml             # 应用、LLM、服务配置
└── requirements.txt
```

## 核心流程

### 1. 上传阶段

入口在 [api/routers/upload.py](/Users/admin/Desktop/cv-intake/api/routers/upload.py:98)。

处理步骤：

1. 接收 `job_id` 和多个 PDF 文件
2. 校验岗位是否存在
3. 调用 `save_uploaded_cv(...)`
4. 将文件保存到 `public/cvs/`
5. 在 `cvs` 表写入一条 `queued` 记录
6. 立即通过 SSE 推送给前端

### 2. OCR 阶段

上传成功后，后端继续串行处理每一份 `queued` 简历：

1. 状态改为 `processing`
2. 调用 [utils/pdf_text.py](/Users/admin/Desktop/cv-intake/utils/pdf_text.py:16) 提取 PDF 文本
3. 成功后把 `resume_text` 和 `resume_text_length` 写入 `cvs`
4. 如果提取为空，状态改为 `ocr_no_text`

当前 PDF 提取优先级：

1. `langchain_community.document_loaders.PDFPlumberLoader`
2. `pdfplumber`
3. `pypdf`

### 3. Workflow 阶段

入口在 [workflow/run.py](/Users/admin/Desktop/cv-intake/workflow/run.py:33) 的 `run_cv_workflow(...)`。

工作流节点顺序：

1. `SummaryNode`
2. `VerifyNode`
3. `ScoreNode`

共享状态定义见 [workflow/state.py](/Users/admin/Desktop/cv-intake/workflow/state.py:6)。

主要字段：

- `resume_text`: OCR 后的简历原文
- `job_text`: 岗位描述
- `resume_summary`: 结构化简历摘要
- `verify_result`: 核验结果
- `score_result`: 评分结果
- `final_answer`: 简短结论
- `error`: 任意阶段的错误或警告

### 4. SummaryNode

文件：[workflow/node/summary.py](/Users/admin/Desktop/cv-intake/workflow/node/summary.py:124)

职责：

- 输入 OCR 简历文本
- 调用模型抽取结构化简历
- 输出 `resume_summary`

当前抽取结构包括：

- 基本信息 `user`
- 教育经历 `education`
- 工作经历 `work_experiences`
- 技能 `skills`
- 项目经历 `projects`
- 奖项 `awards`
- 其他信息 `others`

### 5. VerifyNode

文件：[workflow/node/verify.py](/Users/admin/Desktop/cv-intake/workflow/node/verify.py:110)

职责：

- 不重复抽取，只消费 `resume_summary`
- 使用 `zai` SDK 的 `client.web_search.web_search(...)` 联网查询学校和公司
- 将 `resume_summary + web_search_evidence` 交给工作流现有 `llm` 整理成结构化核验结果
- 校验每段工作经历的起止时间是否前后合理
- 输出统一结构的 `verify_result`

当前核验输出重点包括：

- `schools`
- `companies`
- `work_dates`
- `issues`
- `next_actions`

其中 `schools[i].evidence` 和 `companies[i].evidence` 会附带 1-2 条搜索来源摘要，便于前端直接展示“为什么这样判定”。

### 6. ScoreNode

文件：[workflow/node/score.py](/Users/admin/Desktop/cv-intake/workflow/node/score.py:80)

职责：

- 根据 `job_text + resume_summary + verify_result` 打分
- 输出 0-100 的总分和分项分数
- 给出打分原因、缺失项、风险点和改进建议

评分结构包括：

- `overall`
- `must_have_match`
- `experience_match`
- `skill_match`
- `education_match`

## 数据库存储

核心表为 `cvs`，定义见 [db/models.py](/Users/admin/Desktop/cv-intake/db/models.py:14)。

重要字段：

- 基础信息：`id`、`filename`、`job_id`、`job_name`、`file_path`
- 去重信息：`md5`
- OCR：`ocr_engine`、`resume_text`、`resume_text_length`
- 岗位信息：`job_text`、`job_text_length`
- Workflow 结果：`resume_summary`、`verify_result`、`score_result`
- 展示结论：`final_answer`
- 状态字段：`status`、`error`
- 时间字段：`created_at`、`updated_at`

注意：

- `md5` 表示文件内容 hash
- `cv_id` 不是纯 `md5`，而是 `job_id + md5` 的组合 hash
- 这样可以保证“同一份简历投不同岗位”会保留独立评分结果

## API 概览

### 岗位接口

文件：[api/routers/job.py](/Users/admin/Desktop/cv-intake/api/routers/job.py:61)

- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs`
- `PUT /jobs/{job_id}`
- `DELETE /jobs/{job_id}`

### 上传接口

文件：[api/routers/upload.py](/Users/admin/Desktop/cv-intake/api/routers/upload.py:98)

- `POST /upload`

表单字段：

- `files`: 多个 PDF 文件
- `job_id` 或 `job_ids`: 岗位 id

### 简历接口

文件：[api/routers/cv.py](/Users/admin/Desktop/cv-intake/api/routers/cv.py:96)

- `GET /cvs`
- `GET /cvs/{cv_id}`
- `POST /cvs`
- `PUT /cvs/{cv_id}`
- `DELETE /cvs/{cv_id}`

### SSE 接口

文件：[api/routers/sse.py](/Users/admin/Desktop/cv-intake/api/routers/sse.py:8)

- `GET /sse?type=results`

前端会监听 `results` 事件类型，并按简历 id 合并状态更新。

## 运行方式

### 后端

推荐先创建虚拟环境，然后安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

启动后端：

```bash
python main.py
```

默认服务地址来自 [config.yaml](/Users/admin/Desktop/cv-intake/config.yaml:1)：

- Host: `0.0.0.0`
- Port: `9000`

### 前端

进入前端目录：

```bash
cd web
pnpm install
pnpm dev
```

默认前端会请求：

```text
http://127.0.0.1:9000
```

## 配置说明

配置文件在 [config.yaml](/Users/admin/Desktop/cv-intake/config.yaml:1)。

当前字段：

- `app.name`
- `app.version`
- `llm.model`
- `llm.temperature`
- `llm.api_key`
- `llm.base_url`
- `server.host`
- `server.port`
- `server.cors_origins`

建议：

- 不要把真实生产 API Key 长期硬编码在仓库里
- 本地开发至少改成自己的可用密钥

## 常见状态

`cvs.status` 可能出现这些值：

- `queued`
- `processing`
- `processed`
- `ocr_no_text`
- `skipped_duplicate_md5`
- `skipped_empty_file`
- `skipped_non_pdf`
- `error`

含义：

- `processed`：至少结构化摘要已经生成，主流程完成
- `ocr_no_text`：PDF 可读但没有提取到文本
- `error`：OCR 或 workflow 主流程失败

## 当前限制

- 工作流是同步执行的，`/upload` 会等待 OCR 和 workflow 结束后再返回
- 学校和公司核验依赖 `zai` 的 `web_search` 外网能力，网络或密钥异常会导致 `VerifyNode` 降级为 `blocked`
- 评分依赖外部 LLM 接口，网络或密钥异常会导致 `summary/score` 阶段失败
- 根目录里目前仍保留一个 `REDAME.md`，仅作为跳转提示；主文档以 `README.md` 为准

## 建议的下一步

- 把学校和公司核验接到真实 provider
- 将 `/upload` 改造成后台任务队列，避免长请求阻塞
- 前端增加对 `resume_summary / verify_result / score_result` 的直接展示
- 为 workflow 和上传链路补自动化测试
