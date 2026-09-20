# Seminar Rotation Pairing API

研讨会轮换配对服务。给定 2～16 名（偶数）参与者、**禁配关系** 与 **历史相遇次数**，
在满足全部禁配约束的完整配对（完美匹配）中：

1. **全局最小化重复相遇总次数**（所有被配成一对的组合的历史相遇次数之和）；
2. 同分时按参与者 ID 稳定择优：每对内部按 ID 升序排列，再将所有配对按
   `(a, b)` 字典序排序，取字典序最小的配对序列；
3. 若禁配关系导致无法覆盖全部参与者的完整配对，返回 **HTTP 422** 并说明原因。

技术栈：Python · FastAPI · Pydantic v2 · Uvicorn，位掩码子集 DP 求解最小权完美匹配
（16 人时状态空间仅 2¹⁶，毫秒级完成）。

## 一条命令启动

前置条件：已安装 Docker 与 Docker Compose Plugin（`docker compose`）。

```bash
docker compose up --build
```

镜像构建时即完成全部依赖安装（见 `Dockerfile` / `requirements.txt`），
启动后通过 <http://localhost:8000> 访问。

启动后可用地址：

| 用途 | 地址 |
| --- | --- |
| 健康检查 | <http://localhost:8000/health> |
| 配对接口 | `POST http://localhost:8000/pairings` |
| Swagger UI（可在线试调） | <http://localhost:8000/docs> |
| ReDoc | <http://localhost:8000/redoc> |
| OpenAPI 3 文档 | <http://localhost:8000/openapi.json> |

停止：在当前终端按 `Ctrl+C`；后台模式用 `docker compose down`。

## 环境变量（均为可选项）

服务本身**无必须配置的环境项**（无需数据库、密钥）。以下变量仅用于部署调整，
可在启动前通过 shell 环境或同目录下的 `.env` 文件提供（见 `.env.example`）：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PAIRING_API_PORT` | `8000` | 宿主机映射端口；容器内始终监听 8000。例如 `PAIRING_API_PORT=9000 docker compose up --build` 后访问 <http://localhost:9000> |
| `LOG_LEVEL` | `info` | Uvicorn 日志级别：`critical`/`error`/`warning`/`info`/`debug`/`trace` |

## API

### `GET /health`

```json
{ "status": "ok", "service": "Seminar Rotation Pairing API", "version": "1.0.0" }
```

### `POST /pairings`

请求体：

```json
{
  "participants": ["alice", "bob", "carol", "dave"],
  "forbidden_pairs": [
    { "a": "alice", "b": "bob" }
  ],
  "past_meetings": [
    { "a": "alice", "b": "carol", "count": 3 },
    { "a": "bob", "b": "dave", "count": 1 }
  ]
}
```

字段说明：

- `participants`（**必填**）：参与者 ID 列表，数量为 2～16 的偶数；ID 非空、唯一。
- `forbidden_pairs`（可选）：禁配关系，`a`/`b` 必须引用已知参与者且互不相同；关系无向，重复项自动合并。
- `past_meetings`（可选）：历史相遇次数，`count` 为非负整数；同一对出现多条记录时**次数累加**。

成功响应 `200`：

```json
{
  "pairs": [
    { "a": "alice", "b": "dave" },
    { "a": "bob", "b": "carol" }
  ],
  "total_repeated_meetings": 0,
  "num_pairs": 2
}
```

`pairs` 已按 `(a, b)` 字典序升序返回，即同分择优后的稳定序列。

### 无解：HTTP 422

禁配关系过强、不存在完美匹配时返回 422：

```json
{
  "error": "infeasible",
  "detail": "无法完成完整配对：以下参与者与其余所有人均为禁配关系，无法安排搭档: zoe",
  "blocking_participants": ["zoe"]
}
```

当不存在“孤立”参与者但仍因子集冲突无解时（例如两个互不相连的奇数人群体），
`blocking_participants` 为空数组，`detail` 会说明禁配关系造成了无法同时满足的子集冲突。

请求体本身不合规（奇数人数、人数越界、ID 重复、引用未知参与者、负数历史次数等）
同样返回 422，响应体为 FastAPI 标准校验错误数组。

### 择优（tie-break）规则示例

4 人 `a,b,c,d` 且无任何历史记录时存在三种合法配对，接口固定返回：

```json
{ "pairs": [{ "a": "a", "b": "b" }, { "a": "c", "b": "d" }] }
```

即字典序最小的序列 `[(a,b),(c,d)]`；同样输入永远得到同样输出，结果可复现。

## 本地开发（不使用 Docker）

需要 Python 3.11+：

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

运行测试（测试额外需要 `pytest` 与 `httpx`）：

```bash
pip install -r requirements-dev.txt
pytest -q
```

## 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── main.py        # FastAPI 路由、请求装配、422 语义
│   ├── models.py      # Pydantic v2 请求/响应模型与输入校验
│   └── solver.py      # 位掩码 DP：最小重复相遇 + 字典序择优
├── tests/             # 求解器与 HTTP 层测试
├── Dockerfile         # 构建期安装依赖
├── docker-compose.yml # 一条命令启动与端口映射
├── requirements.txt
└── .env.example
```
