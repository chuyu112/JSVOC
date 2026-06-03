import type { NextConfig } from "next";

// 部署架构说明：
// 前端(服务器) ←→ Nginx ←→ 用户浏览器
//                    ↓
//              Next.js standalone (3000端口)
//                    ↓ rewrites (服务器端代理)
//              frp (127.0.0.1:8000) ←→ 本地电脑 FastAPI
//
// 这样浏览器只访问前端域名，无跨域，后端地址不暴露

const API_BASE_URL = process.env.API_BASE_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    unoptimized: true,
  },
  env: {
    // 浏览器端也走同域，由 Next.js 服务器端代理到后端
    // 空字符串表示使用当前域名（前端服务器）
    NEXT_PUBLIC_API_BASE_URL: "",
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_BASE_URL}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${API_BASE_URL}/health`,
      },
    ];
  },
};

export default nextConfig;
