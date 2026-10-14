# 智能实验室预约系统

前后端分离项目：

```text
练习/
├── fronted/   # Vue 3 + Element Plus 前端
└── backend/   # 后续后端服务
```

## 启动前端

```bash
cd fronted
npm install
npm run dev
```

前端默认地址：`http://localhost:5173`

当前登录接口使用 mock 数据，前端真实接口适配代码位于 `fronted/src/api`。后续开发后端时，在 `fronted/.env` 中设置：

```env
VITE_API_BASE_URL=http://localhost:8080/api
VITE_USE_MOCK=false
```
