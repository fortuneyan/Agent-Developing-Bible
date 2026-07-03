# AI教师Agent - 数据持久化方案设计

**文档类型**: 技术设计文档  
**版本**: v1.0  
**创建日期**: 2026-03-22  
**架构师**: AI Agent  
**数据库选型**: PostgreSQL 16+ (单库方案)

---

## 目录

1. [方案概述](#方案概述)
2. [数据库选型分析](#数据库选型分析)
3. [数据分类与存储策略](#数据分类与存储策略)
4. [数据库Schema设计](#数据库schema设计)
5. [索引设计](#索引设计)
6. [缓存策略](#缓存策略)
7. [消息队列设计](#消息队列设计)
8. [实时通信支持](#实时通信支持)
9. [性能优化策略](#性能优化策略)
10. [备份与恢复](#备份与恢复)

---

## 方案概述

### 核心决策

**采用PostgreSQL单库方案**，原因如下：

1. **简化技术栈**：减少Redis、MongoDB等额外组件，降低运维复杂度
2. **功能完备**：PostgreSQL 16+具备JSONB、全文搜索、LISTEN/NOTIFY、事务性队列等功能
3. **性能满足**：对于中小型在线教学场景（1000+并发用户），PostgreSQL性能足够
4. **ACID保证**：保证数据一致性，无需分布式事务
5. **成本效益**：单数据库方案降低基础设施成本

### 技术选型对比

| 功能需求 | 传统方案（PostgreSQL + Redis + MongoDB） | PostgreSQL单库方案 | 结论 |
|---------|-----------------------------------------|------------------|------|
| 关系数据 | PostgreSQL | PostgreSQL | ✅ 一致 |
| 文档数据 | MongoDB | PostgreSQL JSONB | ✅ 可替代 |
| 缓存/会话 | Redis | PostgreSQL + pg_prewarm | ⚠️ 中等规模可满足 |
| 消息队列 | Redis/RabbitMQ | PostgreSQL LISTEN/NOTIFY + SKIP LOCKED | ✅ 可替代 |
| 实时通信 | Redis Pub/Sub | PostgreSQL LISTEN/NOTIFY | ⚠️ 中等规模可满足 |
| 全文搜索 | Elasticsearch | PostgreSQL tsvector | ⚠️ 简单场景可满足 |

### 适用场景

| 用户规模 | 推荐方案 | 说明 |
|---------|---------|------|
| < 100用户 | PostgreSQL单库 | 完全满足，无需扩展 |
| 100-1000用户 | PostgreSQL单库 | 满足，需优化索引和缓存 |
| 1000-5000用户 | PostgreSQL单库 + Redis缓存 | 引入Redis缓解缓存压力 |
| > 5000用户 | 微服务 + PostgreSQL集群 + Redis + 专用组件 | 按需扩展 |

---

## 数据库选型分析

### PostgreSQL功能映射

#### 1. 替代MongoDB（文档存储）

**功能**：JSONB类型 + GIN索引

**适用数据**：
- 授课日志（动态字段）
- 互动记录（灵活结构）
- 用户配置（主题、通知设置等）

**示例Schema**：
```sql
-- 授课日志表
CREATE TABLE teaching_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id VARCHAR(50) NOT NULL,
    log_type VARCHAR(20) NOT NULL,  -- page_turn, annotation, quiz, etc.
    log_data JSONB NOT NULL,         -- 灵活的日志数据
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建GIN索引加速JSONB查询
CREATE INDEX idx_teaching_logs_channel ON teaching_logs (channel_id);
CREATE INDEX idx_teaching_logs_data ON teaching_logs USING GIN (log_data);

-- 查询示例：查找特定频道的翻页日志
SELECT * FROM teaching_logs 
WHERE channel_id = 'course_20260322_001'
  AND log_data @> '{"action": "page_turn"}';
```

#### 2. 替代Redis（缓存/会话）

**功能**：UNLOGGED表 + pg_prewarm

**适用数据**：
- 频道状态缓存（当前页码、标注等）
- 在线用户列表
- 频存的学习资源

**示例Schema**：
```sql
-- 使用UNLOGGED表（不写WAL，性能更高）
CREATE UNLOGGED TABLE channel_cache (
    channel_id VARCHAR(50) PRIMARY KEY,
    channel_state JSONB NOT NULL,
    expires_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 查询示例：获取频道状态
SELECT channel_state FROM channel_cache 
WHERE channel_id = 'course_20260322_001' 
  AND (expires_at IS NULL OR expires_at > NOW());
```

#### 3. 替代消息队列

**功能**：普通表 + SKIP LOCKED + LISTEN/NOTIFY

**适用数据**：
- 异步任务队列（学情归档、通知发送）
- 频道消息广播

**示例Schema**：
```sql
-- 任务队列表
CREATE TABLE job_queue (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    error_message TEXT
);

-- 创建索引
CREATE INDEX idx_job_queue_status ON job_queue (status, created_at);

-- 消费者获取任务（避免并发冲突）
BEGIN;
UPDATE job_queue
SET status = 'processing', 
    processed_at = NOW(),
    retry_count = retry_count + 1
WHERE id = (
    SELECT id FROM job_queue
    WHERE status = 'pending'
    ORDER BY created_at
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
RETURNING *;
COMMIT;
```

#### 4. 实时通信

**功能**：LISTEN/NOTIFY + 触发器

**适用场景**：
- 频道消息广播（翻页、标注、互动）
- 通知推送（作业发布、批改完成）

**示例实现**：
```sql
-- 创建通知函数
CREATE OR REPLACE FUNCTION notify_channel_message()
RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify(
        'channel_' || NEW.channel_id,
        json_build_object(
            'type', NEW.message_type,
            'data', NEW.message_data,
            'from', NEW.sender_id,
            'timestamp', NEW.created_at
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 频道消息表
CREATE TABLE channel_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id VARCHAR(50) NOT NULL,
    sender_id VARCHAR(50) NOT NULL,
    message_type VARCHAR(20) NOT NULL,
    message_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建触发器
CREATE TRIGGER trg_channel_message_notify
AFTER INSERT ON channel_messages
FOR EACH ROW EXECUTE FUNCTION notify_channel_message();
```

---

## 数据分类与存储策略

### 数据分类

根据数据特性和访问模式，将数据分为以下几类：

| 数据类别 | 特点 | 存储策略 | 表类型 |
|---------|------|---------|--------|
| **核心业务数据** | 结构化、频繁读写、需要ACID | 普通表 | LOGGED |
| **实时缓存数据** | 短生命周期、频繁访问、可丢失 | UNLOGGED表 | UNLOGGED |
| **日志/审计数据** | 只追加、不修改、大量数据 | 分区表 | LOGGED |
| **文档数据** | 灵活结构、动态字段 | JSONB列 | LOGGED |
| **队列数据** | 并发消费、原子操作 | 普通表 + SKIP LOCKED | LOGGED |

### 存储策略详解

#### 1. 核心业务数据

**包含内容**：
- 用户表
- 教案表
- 课件表
- 习题表
- 试卷表
- 学生答题表
- 学情数据表

**特点**：
- 需要严格的ACID保证
- 需要复杂查询和JOIN操作
- 需要索引优化

#### 2. 实时缓存数据

**包含内容**：
- 频道状态缓存（当前页码、标注等）
- 在线用户列表
- 热点课件缓存

**特点**：
- 短生命周期（课程结束后可删除）
- 频繁访问（每次翻页、标注）
- 可丢失（可以从数据库恢复）

**优化**：
- 使用UNLOGGED表（不写WAL日志，性能提升30-50%）
- 设置TTL（过期时间）
- 定期清理过期数据

#### 3. 日志/审计数据

**包含内容**：
- 授课日志
- 互动记录
- 用户操作日志
- 系统日志

**特点**：
- 只追加，不修改
- 数据量大
- 需要按时间分区

**优化**：
- 使用分区表（按月份分区）
- 使用BRIN索引（适合时间序列数据）
- 定期归档历史数据

#### 4. 文档数据

**包含内容**：
- 授课日志详情
- 互动记录详情
- 用户配置

**特点**：
- 灵活结构
- 动态字段
- 需要JSON查询

**优化**：
- 使用JSONB类型
- 创建GIN索引
- 使用@>操作符进行高效查询

#### 5. 队列数据

**包含内容**：
- 异步任务队列（学情归档、通知发送）
- 频道消息队列

**特点**：
- 并发消费
- 原子操作
- 需要重试机制

**优化**：
- 使用SKIP LOCKED避免并发冲突
- 使用状态机管理任务状态
- 设置重试次数和超时时间

---

## 数据库Schema设计

### 核心表设计

#### 1. 用户表 (users)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('teacher', 'student', 'parent', 'admin')),
    full_name VARCHAR(100) NOT NULL,
    avatar_url VARCHAR(255),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- 创建索引
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_created ON users (created_at);

-- 更新时间戳触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

#### 2. 教案表 (lesson_plans)

```sql
CREATE TABLE lesson_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    subject VARCHAR(50) NOT NULL,
    grade VARCHAR(20) NOT NULL,
    chapter VARCHAR(100),
    teacher_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,  -- 教案内容（结构化JSON或Markdown）
    teaching_objectives JSONB,  -- 教学目标（知识、技能、过程、情感、素养）
    key_points TEXT[],  -- 教学重点
    difficulties TEXT[],  -- 教学难点
    teaching_methods TEXT[],  -- 教学方法
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'submitted', 'approved', 'rejected')),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_lesson_plans_teacher ON lesson_plans (teacher_id);
CREATE INDEX idx_lesson_plans_status ON lesson_plans (status);
CREATE INDEX idx_lesson_plans_subject ON lesson_plans (subject);
CREATE INDEX idx_lesson_plans_content ON lesson_plans USING GIN (to_tsvector('chinese', content));

-- 更新时间戳触发器
CREATE TRIGGER update_lesson_plans_updated_at
BEFORE UPDATE ON lesson_plans
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

#### 3. 课件表 (courseware)

```sql
CREATE TABLE courseware (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_plan_id UUID NOT NULL REFERENCES lesson_plans(id),
    title VARCHAR(200) NOT NULL,
    page_count INT NOT NULL,
    content JSONB NOT NULL,  -- 课件内容（每页的文本、图片、标注等）
    file_url VARCHAR(255),  -- 课件文件（PPT、PDF等）
    thumbnail_url VARCHAR(255),
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_courseware_lesson_plan ON courseware (lesson_plan_id);
CREATE INDEX idx_courseware_created_by ON courseware (created_by);

-- 更新时间戳触发器
CREATE TRIGGER update_courseware_updated_at
BEFORE UPDATE ON courseware
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

#### 4. 频道表 (channels) ⭐ 在线授课核心

```sql
CREATE TABLE channels (
    id VARCHAR(50) PRIMARY KEY,  -- channel_id
    name VARCHAR(200) NOT NULL,
    teacher_id UUID NOT NULL REFERENCES users(id),
    lesson_plan_id UUID REFERENCES lesson_plans(id),
    courseware_id UUID REFERENCES courseware(id),
    status VARCHAR(20) DEFAULT 'waiting' CHECK (status IN ('waiting', 'teaching', 'ended', 'archived')),
    current_page INT DEFAULT 1,
    max_students INT DEFAULT 50,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    ended_at TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_channels_teacher ON channels (teacher_id);
CREATE INDEX idx_channels_status ON channels (status);
CREATE INDEX idx_channels_created ON channels (created_at);
```

#### 5. 频道成员表 (channel_members) ⭐

```sql
CREATE TABLE channel_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id VARCHAR(50) NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id),
    joined_at TIMESTAMP DEFAULT NOW(),
    left_at TIMESTAMP,
    is_online BOOLEAN DEFAULT TRUE,
    last_seen_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(channel_id, student_id)
);

-- 创建索引
CREATE INDEX idx_channel_members_channel ON channel_members (channel_id);
CREATE INDEX idx_channel_members_student ON channel_members (student_id);
CREATE INDEX idx_channel_members_online ON channel_members (is_online, last_seen_at);
```

#### 6. 频道状态缓存表 (channel_cache) ⭐ UNLOGGED表

```sql
-- UNLOGGED表：不写WAL日志，性能更高，但崩溃后数据会丢失
CREATE UNLOGGED TABLE channel_cache (
    channel_id VARCHAR(50) PRIMARY KEY,
    channel_state JSONB NOT NULL,  -- 当前频道状态（页码、标注、互动等）
    student_count INT DEFAULT 0,
    active_quiz JSONB,  -- 当前进行的测试
    annotations JSONB DEFAULT '[]',  -- 当前页的标注
    expires_at TIMESTAMP,  -- 过期时间（课程结束后自动清理）
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_channel_cache_expires ON channel_cache (expires_at);
```

**频道状态数据结构**：
```json
{
  "current_page": 3,
  "page_states": {
    "1": {
      "annotations": [],
      "notes": ""
    },
    "2": {
      "annotations": [
        {"type": "circle", "x": 100, "y": 200, "color": "red"}
      ],
      "notes": "重点"
    },
    "3": {
      "annotations": [],
      "notes": ""
    }
  }
}
```

#### 7. 频道消息表 (channel_messages) ⭐

```sql
CREATE TABLE channel_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id VARCHAR(50) NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(id),
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN (
        'page_turn', 'annotation', 'quiz', 'quiz_answer', 
        'raise_hand', 'question', 'answer', 'note'
    )),
    message_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_channel_messages_channel ON channel_messages (channel_id, created_at);
CREATE INDEX idx_channel_messages_type ON channel_messages (message_type);
CREATE INDEX idx_channel_messages_sender ON channel_messages (sender_id);

-- 创建通知触发器
CREATE TRIGGER trg_channel_message_notify
AFTER INSERT ON channel_messages
FOR EACH ROW EXECUTE FUNCTION notify_channel_message();
```

#### 8. 习题表 (exercises)

```sql
CREATE TABLE exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    question_type VARCHAR(20) NOT NULL CHECK (question_type IN (
        'single_choice', 'multiple_choice', 'fill_blank', 
        'true_false', 'short_answer', 'calculation', 
        'proof', 'application', 'comprehensive'
    )),
    options JSONB,  -- 选项（选择题）
    answer TEXT NOT NULL,  -- 正确答案
    explanation TEXT,  -- 解析
    difficulty VARCHAR(10) DEFAULT 'medium' CHECK (difficulty IN ('easy', 'medium', 'hard', 'challenge')),
    subject VARCHAR(50) NOT NULL,
    knowledge_points TEXT[],  -- 知识点
    tags TEXT[],  -- 标签
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- 创建索引
CREATE INDEX idx_exercises_type ON exercises (question_type);
CREATE INDEX idx_exercises_subject ON exercises (subject);
CREATE INDEX idx_exercises_difficulty ON exercises (difficulty);
CREATE INDEX idx_exercises_knowledge_points ON exercises USING GIN (knowledge_points);
CREATE INDEX idx_exercises_tags ON exercises USING GIN (tags);
CREATE INDEX idx_exercises_question ON exercises USING GIN (to_tsvector('chinese', question));
```

#### 9. 试卷表 (test_papers)

```sql
CREATE TABLE test_papers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    paper_type VARCHAR(20) NOT NULL CHECK (paper_type IN (
        'practice', 'quiz', 'unit_test', 'midterm', 'final', 'mock', 'entrance'
    )),
    subject VARCHAR(50) NOT NULL,
    grade VARCHAR(20),
    duration INT,  -- 考试时长（分钟）
    total_score INT DEFAULT 100,
    exercise_ids UUID[] NOT NULL,  -- 习题ID列表
    difficulty_distribution JSONB,  -- 难度分布
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_test_papers_type ON test_papers (paper_type);
CREATE INDEX idx_test_papers_subject ON test_papers (subject);
CREATE INDEX idx_test_papers_created_by ON test_papers (created_by);
```

#### 10. 学生答题表 (student_answers)

```sql
CREATE TABLE student_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id),
    test_paper_id UUID REFERENCES test_papers(id),  -- 课后作业
    channel_id VARCHAR(50) REFERENCES channels(id),  -- 随堂测试
    exercise_id UUID NOT NULL REFERENCES exercises(id),
    answer TEXT NOT NULL,
    is_correct BOOLEAN,
    score DECIMAL(5,2),
    graded_at TIMESTAMP,
    graded_by UUID REFERENCES users(id),
    feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_student_answers_student ON student_answers (student_id);
CREATE INDEX idx_student_answers_test_paper ON student_answers (test_paper_id);
CREATE INDEX idx_student_answers_channel ON student_answers (channel_id);
CREATE INDEX idx_student_answers_exercise ON student_answers (exercise_id);
CREATE INDEX idx_student_answers_created ON student_answers (created_at);
```

#### 11. 学情数据表 (student_learning_records)

```sql
CREATE TABLE student_learning_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id),
    subject VARCHAR(50) NOT NULL,
    knowledge_point VARCHAR(100),
    record_type VARCHAR(20) NOT NULL CHECK (record_type IN (
        'exercise', 'quiz', 'exam', 'class_attendance'
    )),
    score DECIMAL(5,2),
    correct_rate DECIMAL(5,2),
    ability_dimensions JSONB,  -- 能力维度（识记理解、运算求解、实际应用等）
    metadata JSONB,  -- 其他元数据
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_learning_records_student ON student_learning_records (student_id);
CREATE INDEX idx_learning_records_subject ON student_learning_records (subject);
CREATE INDEX idx_learning_records_knowledge_point ON student_learning_records (knowledge_point);
CREATE INDEX idx_learning_records_type ON student_learning_records (record_type);
CREATE INDEX idx_learning_records_created ON student_learning_records (created_at);
```

#### 12. 任务队列表 (job_queue)

```sql
CREATE TABLE job_queue (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    priority INT DEFAULT 0,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- 创建索引
CREATE INDEX idx_job_queue_status ON job_queue (status, priority, created_at);
```

---

## 索引设计

### 索引策略

| 索引类型 | 适用场景 | 优点 | 缺点 |
|---------|---------|------|------|
| **B-tree索引** | 等值查询、范围查询、排序 | 查询速度快 | 占用空间大 |
| **GIN索引** | JSONB、数组、全文搜索 | 支持复杂查询 | 占用空间大，写入慢 |
| **BRIN索引** | 时间序列、分区表 | 占用空间小 | 查询速度慢 |
| **Hash索引** | 等值查询 | 空间小 | 不支持范围查询 |
| **部分索引** | 频繁查询的子集 | 减少索引大小 | 查询需匹配条件 |

### 索引设计示例

#### 1. 频道消息查询优化

```sql
-- 复合索引：按频道和时间排序查询
CREATE INDEX idx_channel_messages_channel_time 
ON channel_messages (channel_id, created_at DESC);

-- 部分索引：只索引活跃频道的消息
CREATE INDEX idx_channel_messages_active 
ON channel_messages (channel_id, created_at DESC)
WHERE created_at > NOW() - INTERVAL '7 days';
```

#### 2. JSONB查询优化

```sql
-- GIN索引：支持JSONB查询
CREATE INDEX idx_teaching_logs_data 
ON teaching_logs USING GIN (log_data);

-- GIN索引：支持数组包含查询
CREATE INDEX idx_exercises_knowledge_points 
ON exercises USING GIN (knowledge_points);
```

#### 3. 全文搜索优化

```sql
-- GIN索引：全文搜索
CREATE INDEX idx_lesson_plans_content_search 
ON lesson_plans USING GIN (to_tsvector('chinese', content));

-- 全文搜索查询示例
SELECT * FROM lesson_plans 
WHERE to_tsvector('chinese', content) @@ to_tsquery('chinese', '函数 & 概念');
```

#### 4. 分区表索引（授课日志）

```sql
-- 按月分区
CREATE TABLE teaching_logs (
    id UUID,
    channel_id VARCHAR(50),
    log_type VARCHAR(20),
    log_data JSONB,
    created_at TIMESTAMP
) PARTITION BY RANGE (created_at);

-- 创建分区表
CREATE TABLE teaching_logs_202603 PARTITION OF teaching_logs
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- BRIN索引：适合时间序列数据
CREATE INDEX idx_teaching_logs_created 
ON teaching_logs_202603 USING BRIN (created_at);
```

---

## 缓存策略

### 缓存层级

| 缓存层级 | 缓存内容 | TTL | 刷新策略 |
|---------|---------|-----|---------|
| **L1: 应用内存** | 频道状态、在线用户 | 30秒 | 定期刷新 |
| **L2: PostgreSQL UNLOGGED表** | 频道状态缓存、课件缓存 | 1小时 | 过期自动清理 |
| **L3: 普通表** | 用户信息、教案、课件 | 永久 | 手动更新 |

### 缓存实现

#### 1. 频道状态缓存

```sql
-- 更新频道状态（插入或替换）
INSERT INTO channel_cache (channel_id, channel_state, student_count, expires_at)
VALUES (
    'course_20260322_001',
    '{"current_page": 3, "annotations": [...]}',
    20,
    NOW() + INTERVAL '2 hours'
)
ON CONFLICT (channel_id) 
DO UPDATE SET 
    channel_state = EXCLUDED.channel_state,
    student_count = EXCLUDED.student_count,
    expires_at = EXCLUDED.expires_at,
    updated_at = NOW();
```

#### 2. 定期清理过期缓存

```sql
-- 创建清理过期缓存的函数
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM channel_cache 
    WHERE expires_at IS NOT NULL AND expires_at < NOW();
    
    -- 记录清理日志
    RAISE NOTICE 'Expired cache cleaned up: % rows', ROW_COUNT;
END;
$$ LANGUAGE plpgsql;

-- 设置定时任务（使用pg_cron扩展）
-- SELECT cron.schedule('cleanup-cache', '*/10 * * * *', 'SELECT cleanup_expired_cache()');
```

---

## 消息队列设计

### 任务队列实现

#### 1. 生产者（发送任务）

```sql
-- 发送学情归档任务
INSERT INTO job_queue (job_type, payload, priority)
VALUES (
    'archive_learning_data',
    '{"channel_id": "course_20260322_001", "student_ids": ["s001", "s002"]}'::jsonb,
    10
);
```

#### 2. 消费者（处理任务）

```python
import psycopg2
from psycopg2 import sql

def consume_job():
    conn = psycopg2.connect("dbname=ai_teacher_agent user=postgres")
    cur = conn.cursor()
    
    while True:
        try:
            # 开启事务
            conn.autocommit = False
            
            # 获取任务（使用SKIP LOCKED避免并发冲突）
            cur.execute("""
                UPDATE job_queue
                SET status = 'processing', processed_at = NOW()
                WHERE id = (
                    SELECT id FROM job_queue
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING id, job_type, payload
            """)
            
            job = cur.fetchone()
            if not job:
                conn.commit()
                time.sleep(1)
                continue
            
            job_id, job_type, payload = job
            
            # 处理任务
            try:
                if job_type == 'archive_learning_data':
                    process_archive_learning(payload)
                
                # 更新任务状态
                cur.execute("""
                    UPDATE job_queue
                    SET status = 'completed', completed_at = NOW()
                    WHERE id = %s
                """, (job_id,))
                
            except Exception as e:
                # 处理失败，增加重试次数
                cur.execute("""
                    UPDATE job_queue
                    SET status = 'failed', 
                        error_message = %s,
                        retry_count = retry_count + 1
                    WHERE id = %s
                """, (str(e), job_id))
                
                if cur.fetchone()[0] >= 3:
                    # 超过最大重试次数，标记为失败
                    pass
                else:
                    # 重新入队
                    cur.execute("""
                        UPDATE job_queue
                        SET status = 'pending'
                        WHERE id = %s
                    """, (job_id,))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            time.sleep(1)
```

---

## 实时通信支持

### LISTEN/NOTIFY实现

#### 1. 服务端发送通知

```sql
-- 插入频道消息（自动触发通知）
INSERT INTO channel_messages (channel_id, sender_id, message_type, message_data)
VALUES (
    'course_20260322_001',
    'teacher_001',
    'page_turn',
    '{"page": 3}'
);
-- 触发器会自动执行 pg_notify('channel_course_20260322_001', ...)
```

#### 2. 客户端监听通知（Python示例）

```python
import psycopg2
import select
import json

def listen_to_channel(channel_id):
    conn = psycopg2.connect("dbname=ai_teacher_agent user=postgres")
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    # 监听频道
    cur.execute(f"LISTEN channel_{channel_id}")
    
    print(f"Listening to channel_{channel_id}...")
    
    while True:
        # 等待通知
        if select.select([conn], [], [], 5) == ([], [], []):
            continue
        
        conn.poll()
        while conn.notifies:
            notify = conn.notifies.pop(0)
            
            # 解析通知消息
            message = json.loads(notify.payload)
            
            # 根据消息类型处理
            if message['type'] == 'page_turn':
                handle_page_turn(message['data'])
            elif message['type'] == 'annotation':
                handle_annotation(message['data'])
            elif message['type'] == 'quiz':
                handle_quiz(message['data'])

def handle_page_turn(data):
    """处理翻页通知"""
    page = data['page']
    print(f"Teacher turned to page {page}")
    # 更新UI显示

def handle_annotation(data):
    """处理标注通知"""
    print(f"Teacher added annotation: {data}")
    # 更新课件标注

def handle_quiz(data):
    """处理测试通知"""
    print(f"Teacher started quiz: {data}")
    # 显示测试窗口
```

---

## 性能优化策略

### 1. 连接池配置

使用连接池（如psycopg2.pool）管理数据库连接：

```python
from psycopg2 import pool

# 创建连接池
db_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=5,
    maxconn=50,
    dbname="ai_teacher_agent",
    user="postgres",
    password="password",
    host="localhost"
)

# 获取连接
conn = db_pool.getconn()
try:
    # 使用连接
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
finally:
    # 释放连接回池
    db_pool.putconn(conn)
```

### 2. 批量操作优化

```sql
-- 批量插入（比单条插入快10-100倍）
INSERT INTO student_answers (student_id, exercise_id, answer, created_at)
VALUES
    ('s001', 'e001', 'A', NOW()),
    ('s002', 'e001', 'B', NOW()),
    ('s003', 'e001', 'A', NOW());
```

### 3. 查询优化

```sql
-- 使用EXPLAIN分析查询计划
EXPLAIN ANALYZE
SELECT * FROM lesson_plans 
WHERE teacher_id = 'teacher_001' 
  AND status = 'approved'
ORDER BY created_at DESC
LIMIT 10;

-- 使用CTE优化复杂查询
WITH recent_lessons AS (
    SELECT id, title, created_at
    FROM lesson_plans
    WHERE teacher_id = 'teacher_001'
    ORDER BY created_at DESC
    LIMIT 100
)
SELECT l.*, c.title AS courseware_title
FROM recent_lessons l
LEFT JOIN courseware c ON l.id = c.lesson_plan_id;
```

### 4. 分区表优化

```sql
-- 授课日志按月分区，历史数据自动归档
-- 每月自动创建新分区
CREATE TABLE teaching_logs_202604 PARTITION OF teaching_logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

### 5. 视图优化

```sql
-- 创建物化视图（定期刷新）
CREATE MATERIALIZED VIEW student_progress_mv AS
SELECT 
    student_id,
    subject,
    AVG(correct_rate) AS avg_correct_rate,
    COUNT(*) AS total_exercises
FROM student_learning_records
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY student_id, subject;

-- 创建索引
CREATE INDEX idx_student_progress_mv_student ON student_progress_mv (student_id);

-- 定期刷新物化视图
-- REFRESH MATERIALIZED VIEW CONCURRENTLY student_progress_mv;
```

---

## 备份与恢复

### 1. 逻辑备份

```bash
# 备份所有数据库
pg_dump -U postgres -d ai_teacher_agent -f backup.sql

# 仅备份数据（不含结构）
pg_dump -U postgres -d ai_teacher_agent --data-only -f data_backup.sql

# 仅备份特定表
pg_dump -U postgres -d ai_teacher_agent -t users -t lesson_plans -f specific_tables.sql
```

### 2. 物理备份

```bash
# 使用pg_basebackup进行物理备份
pg_basebackup -U postgres -D /var/lib/postgresql/backup -Ft -z -P -x

# 恢复
pg_ctl -D /var/lib/postgresql/backup stop
pg_ctl -D /var/lib/postgresql/data start
```

### 3. 定期备份脚本

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/postgresql"
DB_NAME="ai_teacher_agent"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
pg_dump -U postgres -d $DB_NAME -f $BACKUP_DIR/$DB_NAME_$DATE.sql

# 压缩备份
gzip $BACKUP_DIR/$DB_NAME_$DATE.sql

# 删除7天前的备份
find $BACKUP_DIR -name "$DB_NAME_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/$DB_NAME_$DATE.sql.gz"
```

### 4. 持续归档（Point-in-Time Recovery）

```postgresql
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/archive/%f'
max_wal_senders = 3
wal_keep_size = 1GB
```

---

## 总结

### 方案优势

1. **简化技术栈**：仅使用PostgreSQL，无需Redis、MongoDB
2. **降低运维成本**：减少数据库实例，简化部署和维护
3. **性能满足**：对于1000+并发用户的场景，PostgreSQL性能足够
4. **ACID保证**：保证数据一致性，无需分布式事务
5. **灵活扩展**：可根据需要逐步引入Redis等组件

### 注意事项

1. **缓存性能**：UNLOGGED表虽快，但崩溃后数据会丢失（需有恢复机制）
2. **实时通信**：LISTEN/NOTIFY适合中等规模，超大规模可能需要专用消息队列
3. **JSONB查询**：GIN索引虽强大，但占空间，需权衡查询频率和存储成本
4. **连接池**：必须使用连接池管理连接，避免连接泄漏

### 扩展路径

| 用户规模 | 当前方案 | 扩展方案 |
|---------|---------|---------|
| < 1000用户 | PostgreSQL单库 | 无需扩展 |
| 1000-5000用户 | PostgreSQL单库 | 引入Redis缓存 |
| 5000-10000用户 | PostgreSQL + Redis | PostgreSQL主从 + Redis集群 |
| > 10000用户 | 微服务 + PostgreSQL集群 + Redis + 专用组件 | 按需扩展 |

---

**文档版本**: v1.0  
**最后更新**: 2026-03-22  
**下一步**: 完善需求文档
