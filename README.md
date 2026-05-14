# 研发故障根因定位多 Agent 系统

基于 **感知 → 推理 → 行动** 三阶段协作的线上故障自动定位与恢复系统。

## 快速开始

```bash
cd fault_agent
python3 main.py
```

## 系统架构

```
故障时间 + 服务列表
       │
       ▼
  PerceptionAgent ──(超时5s→降级)──► 感知数据
       │
       ▼
  ReasoningAgent ──(置信度≤0.5→人工模式)──► 根因候选
       │
       ▼
  ActionAgent ──(置信度<0.7→仅通知)──► 执行动作
       │
       ▼
  最终结果 + trace 日志
```

### 三个 Agent

| Agent | 职责 | 关键特性 |
|-------|------|----------|
| PerceptionAgent | 拉取日志/指标/告警，聚合降噪 | asyncio.gather 并发拉取，日志去重合并 |
| ReasoningAgent | 因果链推理 + 历史案例交叉验证 | LLM 推理（无 API Key 时自动 mock），向量检索相似案例 |
| ActionAgent | 执行恢复预案 + 通知负责人 | 置信度<0.7 安全拦截，dry-run 模拟，钉钉/飞书通知 |

### 安全机制

- **置信度 < 0.7**：禁止自动执行，仅发送人工介入通知
- **置信度 ≤ 0.5**：进入人工协助模式，不调用行动 Agent
- **感知超时 5s**：降级使用最近告警数据
- **所有动作先 dry-run**：模拟效果后再执行

## 项目结构

```
fault_agent/
├── agents/
│   ├── perception.py      # 感知 Agent
│   ├── reasoning.py       # 推理 Agent
│   └── action.py          # 行动 Agent
├── pipeline.py            # 编排器（串联三个 Agent）
├── models.py              # Pydantic 数据模型
├── vector_store.py        # 向量检索（chromadb 或 mock）
├── utils/
│   ├── mock_data.py       # 模拟监控数据
│   └── logger.py          # 结构化日志（含 trace_id）
├── tests/                 # 单元测试（15 个）
└── main.py                # 运行入口
```

## 运行测试

```bash
cd fault_agent
python3 -m pytest tests/ -v
```

## 接入真实 LLM

设置环境变量后自动切换到 OpenAI 推理（默认 mock）：

```bash
export OPENAI_API_KEY=your-key-here
python3 main.py
```

## 输出示例

运行后输出包含：
- **感知数据**：去重后的错误日志、关键指标、告警列表
- **推理结果**：3 个根因候选（含置信度和证据），相似历史案例
- **行动结果**：执行的动作或跳过原因，通知内容
- **执行统计**：各 Agent 耗时、trace_id

## 技术栈

- Python 3.10+ / asyncio
- Pydantic（数据模型）
- OpenAI API（可选，推理 Agent）
- chromadb（可选，向量检索，无则回退到关键词匹配）