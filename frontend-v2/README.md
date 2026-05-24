# Strategy Studio Frontend v2

Next.js + React + Tailwind CSS 重构版前端。

## 技术栈

- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS 4
- Framer Motion (动画)

## 开发

```bash
npm install
npm run dev
```

前端运行在 `http://localhost:3000`（默认）。

开发模式下 API 通过 Next.js rewrite 代理到 `http://localhost:8000`。

## 生产构建

```bash
npm run build
npm start
```

## Docker

```bash
docker compose up frontend-v2
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `API_BASE_URL` | 后端 API 地址 | `http://localhost:8000` |

## 路由

| 路径 | 说明 |
|------|------|
| `/login` | 登录/注册 |
| `/projects` | 项目列表 |
| `/projects/new` | 新建项目 |
| `/projects/[id]` | 项目详情 |
| `/projects/[id]/account-package` | 账号包装 |
| `/projects/[id]/execution-plan` | 执行计划 |
| `/projects/[id]/hot-videos` | 热门视频搜索 |
| `/projects/[id]/topics` | 选题生成 |
| `/projects/[id]/images` | 图片生成 |
| `/projects/[id]/videos` | 视频生成 |
| `/projects/[id]/publish` | 内容发布 |
| `/projects/[id]/history` | 生成历史 |
| `/assets` | 数字资产 |
| `/history` | 全局生成历史 |
