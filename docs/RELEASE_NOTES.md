# Release Notes

## v0.1.0-mvp

发布时间：2026-05-09

### 已完成功能

v0.1.0-mvp 完成 AI 短视频账号策略与内容创作系统的主链路：

1. 项目档案
   - 创建项目
   - 查看项目列表
   - 查看项目详情
   - 编辑项目
   - 删除项目

2. 账号包装和执行计划
   - 从项目详情进入账号包装页
   - 从项目详情进入执行计划页
   - 调用 `POST /api/strategy/account-package-execution-plan/generate`
   - 结果保存到 `account_strategy_contexts`
   - 返回至少 4 周计划和 30 天 daily_plan
   - 生成记录写入 `generation_records`

3. 选题生成
   - 从项目详情进入选题生成页
   - 调用 `POST /api/creation/topics/generate`
   - 支持 `count=20` 返回 20 个选题
   - 选题保存到 `topics`
   - 生成记录写入 `generation_records`

4. 文案生成
   - 从选题进入文案生成页
   - 调用 `POST /api/creation/scripts/generate`
   - 文案保存到 `scripts`
   - 生成记录写入 `generation_records`

5. 生成历史
   - 访问 `/history`
   - 访问 `/projects/:id/history`
   - 调用 `GET /api/generation-records`
   - 调用 `GET /api/generation-records/{record_id}`
   - 查看 `strategy_bundle`、`topics`、`script` 三类记录

### 测试结果

后端测试：

```powershell
cd backend
python -m unittest discover -s tests
```

验收结果：

```text
Ran 4 tests
OK
```

前端构建：

```powershell
cd frontend
npm run build
```

验收结果：

```text
✓ built
```

### 已知非阻塞问题

1. 前端构建存在 Vite chunk size 警告，不影响 MVP 使用。
2. 后端 SQLAlchemy 使用 `datetime.utcnow()` 时存在弃用警告，后续可改为 timezone-aware UTC。
3. 当前 Docker Compose 仍需进一步完善 PostgreSQL ready 检查、Alembic 初始化和生产化启动方式。
4. 当前 migration 工程化尚未完全替代 `Base.metadata.create_all`。
5. 生成历史页面为基础查询能力，后续可增加分页总数、时间范围筛选和更友好的详情视图。

### 下一阶段计划

Sprint 8 工程化收尾：

1. Alembic migration 替代 `Base.metadata.create_all`
2. PostgreSQL 环境完整启动和初始化
3. Docker Compose 联调 backend、frontend、postgres
4. openai_compatible 本地大模型中转联调
5. 初始化行业模板库和平台规则库
6. 完善 README、部署说明、用户指南和发布说明

Sprint 8 不新增行业、人设、直播、私域、变现等业务模块。
