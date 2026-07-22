# RiskEvent 生命周期增强设计文档

## 概述

本次改造为 RiskEvent 表增加了 pipeline 批次追踪能力，使系统可以完整追溯每次评分批次的来源和模型版本。

## 修改内容

### 1. 数据库模型变更

#### RiskEvent 表新增字段

| 字段名 | 类型 | 说明 | 索引 |
|--------|------|------|------|
| `pipeline_run_id` | VARCHAR(50) | Pipeline 运行批次唯一标识 | `idx_risk_events_pipeline_run` |
| `model_version` | VARCHAR(20) | 使用的模型版本号 | - |

### 2. 数据一致性说明

#### User.current_risk_score vs RiskEvent

| 维度 | User.current_risk_score | RiskEvent |
|------|------------------------|-----------|
| **性质** | Current State (当前状态) | Immutable History (不可变历史快照) |
| **更新方式** | UPDATE (可变) | INSERT ONLY (仅追加) |
| **时效性** | 始终最新 | 按时间点不可变 |
| **用途** | 快速查询当前用户状态 | 历史追溯、批次分析、审计 |
| **生命周期** | 随每次评分更新 | 永久保留 |

**设计原则：**
- `User.current_risk_score` 是查询用户当前风险的快速入口
- `RiskEvent` 是完整的不可变历史记录，每次评分都创建新记录
- 同一用户可以有多个 RiskEvent，每个属于不同的 pipeline run

### 3. Pipeline Run ID 生成规则

```python
pipeline_run_id = f"run_{timestamp}_{random_8chars}"
# 示例: run_20260722_143052_a3f8b2c1
```

**组成部分：**
- `run_`: 固定前缀
- `20260722_143052`: UTC 时间戳 (YYYYMMDD_HHMMSS)
- `a3f8b2c1`: 8 位随机十六进制字符

### 4. 代码修改清单

| 文件 | 修改内容 |
|------|----------|
| `backend/app/models/database.py` | RiskEvent 模型增加 `pipeline_run_id`, `model_version` 字段和索引 |
| `backend/app/models/schemas.py` | RiskEventResponse 增加 `pipeline_run_id`, `model_version` 字段 |
| `backend/app/services/risk_service.py` | `score_user()` 和 `score_all_users()` 增加参数 |
| `backend/app/services/pipeline_service.py` | `run_pipeline()` 生成 run_id 并传递给评分服务 |
| `backend/app/api/routes/risk.py` | `/events` 接口增加 `pipeline_run_id` 查询参数 |
| `backend/app/migrations/add_riskevent_lifecycle_fields.py` | 数据库迁移脚本 |

### 5. 保持不变的部分

以下逻辑未修改，确保评分结果一致性：

- ✅ 评分公式 (ML + Rules + Graph 加权组合)
- ✅ 风险等级阈值 (HIGH=70, MEDIUM=40)
- ✅ Override 逻辑 (协同欺诈提升等级)
- ✅ RiskFactor 创建逻辑
- ✅ User.current_risk_score 更新逻辑

### 6. 风险等级判定逻辑

CRITICAL 级别可以通过两条路径达成：

**路径 1: 协同欺诈 Override**
- 条件：ML ≥ 80 AND Rule ≥ 40 AND Graph ≥ 50
- 结果：风险等级提升至 CRITICAL
- 特点：不修改加权分数，仅提升风险等级

**路径 2: 高分判定**
- 条件：final_score ≥ 90
- 结果：自动判定为 CRITICAL
- 特点：在 HIGH (≥ 70) 风险带内的自然高分

**风险等级分层**：
- CRITICAL: ≥ 90 (或满足 Override 条件)
- HIGH: 70 - 89
- MEDIUM: 50 - 69
- LOW: < 50

## 使用示例

### 查询特定 Pipeline Run 的所有事件

```sql
-- 查询某次 pipeline run 创建的所有风险事件
SELECT user_id, risk_score, risk_level, detected_at
FROM risk_events
WHERE pipeline_run_id = 'run_20260722_143052_a3f8b2c1'
ORDER BY detected_at;
```

### 查询用户的所有历史事件

```sql
-- 查询某用户的所有风险事件，按时间倒序
SELECT id, pipeline_run_id, model_version, risk_score, detected_at
FROM risk_events
WHERE user_id = 'U00010'
ORDER BY detected_at DESC;
```

### API 查询示例

```bash
# 获取所有最新事件（默认）
GET /api/risk/events

# 获取特定 pipeline run 的事件
GET /api/risk/events?pipeline_run_id=run_20260722_143052_a3f8b2c1

# 获取特定 pipeline run 的高风险事件
GET /api/risk/events?pipeline_run_id=run_20260722_143052_a3f8b2c1&risk_level=HIGH
```

## 数据库迁移

### 运行迁移

```bash
# 升级（添加新字段）
python -m app.migrations.add_riskevent_lifecycle_fields

# 降级（移除新字段）
python -m app.migrations.add_riskevent_lifecycle_fields --downgrade
```

### 迁移验证 SQL

```sql
-- 验证字段已添加
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'risk_events'
AND column_name IN ('pipeline_run_id', 'model_version');

-- 验证索引已创建
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'risk_events'
AND indexname = 'idx_risk_events_pipeline_run';
```

## 测试验证

### 测试场景 1: 运行 Pipeline 后验证字段

```sql
-- 1. 运行 pipeline (通过 API 或 CLI)
-- 2. 查看最新事件是否包含 pipeline_run_id 和 model_version

SELECT 
    id,
    user_id,
    pipeline_run_id,
    model_version,
    risk_score,
    detected_at
FROM risk_events
ORDER BY detected_at DESC
LIMIT 5;
```

**预期结果：**
- 新事件应包含 `pipeline_run_id` (格式: `run_YYYYMMDD_HHMMSS_XXXXXXXX`)
- 新事件应包含 `model_version` (如果存在激活的模型)

### 测试场景 2: 验证同一 Pipeline Run 的所有事件

```sql
-- 1. 获取最新的 pipeline_run_id
SELECT DISTINCT pipeline_run_id
FROM risk_events
ORDER BY detected_at DESC
LIMIT 1;

-- 2. 统计该 run 的总事件数
SELECT COUNT(*) as total_events
FROM risk_events
WHERE pipeline_run_id = 'run_20260722_143052_a3f8b2c1';
```

**预期结果：**
- 事件数应等于被评分的用户总数

### 测试场景 3: 验证历史事件查询

```sql
-- 查询同一用户在不同 pipeline run 中的事件
SELECT 
    pipeline_run_id,
    model_version,
    risk_score,
    risk_level,
    detected_at
FROM risk_events
WHERE user_id = 'U00010'
ORDER BY detected_at DESC;
```

**预期结果：**
- 同一用户可有多个事件
- 每个事件有唯一的 `pipeline_run_id`
- 最早的事件可能没有 `pipeline_run_id` (迁移前的历史数据)

## 向后兼容性

- ✅ 新字段为可空字段 (`nullable=True`)
- ✅ 历史数据自动兼容 (字段为 NULL)
- ✅ API 查询参数为可选 (默认行为不变)
- ✅ 评分服务参数为可选 (向后兼容)
