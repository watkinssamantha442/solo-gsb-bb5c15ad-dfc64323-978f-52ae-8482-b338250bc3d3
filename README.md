# 研讨会轮换配对 API

基于 FastAPI + Pydantic 的研讨会轮换配对服务：在满足全部禁配关系的完整配对中，
全局最小化重复相遇总次数，并在同分时给出稳定唯一的配对方案。

## 环境要求

| 依赖 | 版本要求 | 说明 |
| --- | --- | --- |
| Docker | 20.10+ | 构建并运行容器 |
| Docker Compose | v2（`docker compose`） | 编排启动 |

- 无需任何环境变量或外部服务（数据库、缓存等），应用完全自包含。
- 依赖安装已在镜像构建阶段完成（`pip install -r requirements.txt`），无需手动操作。

## 快速开始

```bash
docker compose up --build
```

启动后访问：

| 地址 | 说明 |
| --- | --- |
| http://localhost:8000/health | 健康检查 |
| http://localhost:8000/docs | Swagger UI 交互文档 |
| http://localhost:8000/openapi.json | OpenAPI 规范 |
| http://localhost:8000/pairings | 配对计算接口（POST） |

服务监听宿主机 **8000** 端口（`docker-compose.yml` 中映射 `8000:8000`，
如端口冲突可改为 `"<空闲端口>:8000"`）。

## API 说明

### `POST /pairings`

请求体：

```json
{
  "participants": ["alice", "bob", "carol", "dave"],
  "forbidden_pairs": [{"a": "alice", "b": "bob"}],
  "history": [
    {"a": "alice", "b": "carol", "count": 2},
    {"a": "bob", "b": "dave", "count": 1}
  ]
}
```

字段约束：

- `participants`：必填，2~16 名且为偶数，ID 互不重复；字符串或整数均可
  （整数会规范化为字符串，排序按字符串形式进行）。
- `forbidden_pairs`：可选，禁配关系列表，两人不得被配成一对。
- `history`：可选，历史相遇记录，`count` 为非负整数；同一对出现多次时次数累加。
- 禁配与历史记录引用的参与者必须已登记在 `participants` 中。

成功响应 `200`：

```json
{
  "pairs": [["alice", "dave"], ["bob", "carol"]],
  "total_repeat_encounters": 0
}
```

择优规则：

1. **首要目标**：在所有满足禁配关系的完整配对中，使"重复相遇总次数"
   （各配对历史相遇次数之和）全局最小——采用位掩码动态规划求解，保证全局最优；
2. **同分稳定择优**：并列最优时，取"按参与者 ID 排序后的配对序列"字典序最小者。
   配对序列规范化形式为：每对内部按 ID 升序、各对之间按字典序排列，
   因此相同请求永远返回相同结果。

错误响应 `422`（两类）：

- 请求参数非法（人数非偶数/超范围、ID 重复、引用未知参与者、自配对、负数次数等），
  响应体为 Pydantic 校验明细；
- 禁配关系下不存在完整配对，响应体为：

```json
{"detail": "无法完成完整配对：禁配关系使所有参与者无法被同时配成若干对"}
```

### `GET /health`

返回 `{"status": "ok"}`，用于存活探针。

## 示例

```bash
curl -s -X POST http://localhost:8000/pairings \
  -H 'Content-Type: application/json' \
  -d '{
    "participants": ["alice", "bob", "carol", "dave"],
    "forbidden_pairs": [{"a": "alice", "b": "bob"}],
    "history": [{"a": "alice", "b": "carol", "count": 2}]
  }'
```

## 本地开发与测试（可选）

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload   # 本地调试
pytest                          # 运行全部测试（求解器 + API 集成）
```

## 项目结构

```
app/
  main.py      # FastAPI 入口与路由（/pairings、/health、OpenAPI）
  models.py    # Pydantic 请求/响应模型与校验规则
  solver.py    # 位掩码 DP 最小权重完美匹配求解器（纯标准库）
tests/
  test_solver.py  # 求解器单元测试
  test_api.py     # API 集成测试
Dockerfile
docker-compose.yml
requirements.txt      # 运行时依赖
requirements-dev.txt  # 开发/测试依赖
```
