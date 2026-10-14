# 智能实验室预约系统前端

基于 Vue 3、Vite、Element Plus、Vue Router 和 Pinia 的管理端前端。

## 启动

```bash
npm install
npm run dev
```

默认访问地址：`http://127.0.0.1:5173`

开发环境会将 `/api` 请求代理到 `http://127.0.0.1:8000`。如后端端口不同，可在启动前设置：

```env
VITE_DEV_API_TARGET=http://127.0.0.1:8000
```

## 环境变量

复制 `.env.example` 为 `.env`，真实接口建议使用以下配置：

```env
VITE_API_BASE_URL=/api
VITE_USE_MOCK=false
VITE_DEV_API_TARGET=http://127.0.0.1:8000
```

只有在前端独立开发时才启用 mock：

```env
VITE_USE_MOCK=true
```

## 登录接口契约

前端请求：

```text
POST /api/auth/login
Content-Type: application/json
```

请求体：

```json
{
  "username": "admin",
  "password": "123456"
}
```

后端响应使用统一包装：

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "your-token",
    "user": {
      "id": 1,
      "role": "admin",
      "username": "admin",
      "name": "管理员",
      "status": 1
    }
  }
}
```

前端会自动完成以下处理：

- 登录请求自动携带 JSON 请求头。
- 已登录请求自动携带 `Authorization: Bearer <token>`。
- 解析后端统一响应，兼容后端业务错误使用 HTTP 200 返回的情况。
- 登录成功后持久化 token 和用户信息。
- 收到 401 时清理本地会话，由路由守卫回到登录页。
