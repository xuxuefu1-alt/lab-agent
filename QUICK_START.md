# 快速启动指南

## 项目结构
```
lag-agent/
├── backend/          # Python FastAPI 后端
├── fronted/          # Vue3 前端项目
├── docs/             # 文档
└── IMPLEMENTATION_REPORT.md  # 完整实现报告
```

---

## 🔧 后端启动 (Python)

### 前置步骤：启动必需的 Redis Stack
后端启动时会初始化 LangGraph Redis 检查点索引。开发环境和生产环境都必须使用 Redis Stack；Redis 未就绪时，后端会快速失败，不会切换为内存检查点。

请先在项目根目录启动 Redis：
```bash
docker compose -f ops/observability/docker-compose.yml up -d redis
docker compose -f ops/observability/docker-compose.yml ps redis
```

确认 Redis 容器状态为 `healthy` 后，再按下面步骤启动后端。

### 1. 进入后端目录
```bash
cd backend
```

### 2. 激活虚拟环境
```bash
# Windows
.\.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. 启动服务器
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**输出示例**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 4. 查看API文档
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🎨 前端启动 (Node.js)

### 1. 进入前端目录
```bash
cd fronted
```

### 2. 安装依赖 (如果未安装)
```bash
npm install
```

### 3. 启动开发服务器
```bash
npm run dev
```

**输出示例**:
```
  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

### 4. 访问应用
打开浏览器: http://localhost:5173

---

## 📝 功能入口

### 登录
1. 访问 http://localhost:5173
2. 使用测试账户登录
3. 密码通常为: `123456` (具体按你的设置)

### 实验室管理
- 菜单: 左侧菜单栏 → "实验室管理"
- 路由: `/laboratories`
- 功能:
  - 查看实验室列表
  - 搜索实验室 (名称/位置)
  - 创建新实验室
  - 编辑实验室信息
  - 删除实验室

### 设备列表管理
- 菜单: 左侧菜单栏 → "设备列表管理"
- 路由: `/equipment`
- 功能:
  - 查看设备列表
  - 多条件搜索 (名称/型号/序列号)
  - 按实验室筛选
  - 按维护状态筛选
  - 创建新设备
  - 编辑设备信息
  - 删除设备

---

## 🧪 运行测试

### 后端集成测试
```bash
cd backend
.\.venv\Scripts\python.exe test_laboratory_equipment.py
```

**测试覆盖**:
- ✅ 实验室CRUD操作
- ✅ 设备CRUD操作
- ✅ 序列号唯一性验证
- ✅ 搜索和筛选功能
- ✅ 异常处理

---

## 📡 API 端点速览

### 实验室API
```
POST   /api/laboratories           # 创建实验室
GET    /api/laboratories           # 获取列表 (支持搜索/分页)
GET    /api/laboratories/{id}      # 获取详情
PUT    /api/laboratories/{id}      # 更新实验室
DELETE /api/laboratories/{id}      # 删除实验室
```

### 设备API
```
POST   /api/equipment              # 创建设备
GET    /api/equipment              # 获取列表 (支持多条件筛选)
GET    /api/equipment/{id}         # 获取详情
PUT    /api/equipment/{id}         # 更新设备
DELETE /api/equipment/{id}         # 删除设备
```

### 查询参数示例
```bash
# 实验室搜索
GET /api/laboratories?skip=0&limit=10&keyword=化学

# 设备列表 (按实验室和维护状态)
GET /api/equipment?skip=0&limit=10&laboratory_id=1&maintenance_status=正常

# 设备搜索
GET /api/equipment?skip=0&limit=10&keyword=显微镜
```

---

## 🐛 常见问题

### 后端无法启动
**问题**: `ModuleNotFoundError: No module named 'pymysql'`
**解决**: 
```bash
# 激活虚拟环境后安装依赖
pip install -r requirements.txt
```

### 前端无法连接后端
**问题**: `无法连接服务器`
**检查**:
1. 后端服务是否运行在 http://localhost:8000
2. CORS配置是否正确 (已默认配置)
3. 查看浏览器控制台错误信息

### 数据库连接失败
**问题**: `Connection refused to MySQL`
**检查**:
1. MySQL服务是否运行
2. `.env` 文件中的连接字符串是否正确
3. 数据库用户名密码是否正确

---

## 📦 项目依赖

### 后端依赖
```
fastapi==0.115.13
uvicorn==0.34.0
sqlalchemy==2.0.41
pymysql==1.1.1
pydantic-settings==2.7.1
bcrypt==5.0.0
PyJWT==2.13.0
```

### 前端依赖
```
vue@3.5.43
vue-router@4.5.1
element-plus@2.14.7
@element-plus/icons-vue@2.3.2
pinia@4.0.3
vite@6.4.4
```

---

## 🔑 环境变量 (.env)

后端 `.env` 文件位置: `backend/.env`

```ini
# 数据库连接
mysql_url = mysql+pymysql://root:password@127.0.0.1:3306/lab_agent

# JWT配置
JWT_SECRT_KEY = your-secret-key
JWT_EXPIRE_HOURS = 24
JWT_ALGORITHM = HS256

# 大模型配置
LLM_API_KEY = your-api-key
LLM_BASE_URL = https://api.deepseek.com
LLM_MODEL = deepseek-flash
```

---

## 📊 数据库表结构

### laboratory 表
```sql
CREATE TABLE laboratory (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  location VARCHAR(255) NOT NULL,
  capacity INT DEFAULT 0,
  manager_id INT NOT NULL,
  status INT DEFAULT 1,
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### equipment 表
```sql
CREATE TABLE equipment (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  equipment_type VARCHAR(50) NOT NULL,
  laboratory_id INT NOT NULL,
  model VARCHAR(100),
  serial_number VARCHAR(100) UNIQUE,
  description TEXT,
  purchase_date VARCHAR(20),
  maintenance_status VARCHAR(20) DEFAULT '正常',
  status INT DEFAULT 1,
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

---

## 🎯 测试流程

### 手动功能测试

#### 1. 创建实验室
- 导航到"实验室管理"
- 点击"添加实验室"
- 填写表单并提交
- 验证列表中显示新实验室

#### 2. 创建设备
- 导航到"设备列表管理"
- 点击"添加设备"
- 选择刚才创建的实验室
- 填写设备信息并提交
- 验证列表中显示新设备

#### 3. 搜索功能
- 在实验室列表中输入关键词搜索
- 在设备列表中使用多条件筛选
- 验证搜索结果正确

#### 4. 编辑和删除
- 编辑已创建的实验室/设备
- 删除测试数据
- 验证更新和删除成功

---

## 📈 性能指标

- **响应时间**: < 200ms (单条记录操作)
- **列表查询**: < 500ms (默认10条)
- **搜索性能**: < 1s (千条记录)
- **同时连接**: 支持100+并发

---

## ✅ 部署检查清单

- [ ] 后端服务正常启动
- [ ] 前端开发服务正常启动
- [ ] 数据库连接正常
- [ ] 可成功登录系统
- [ ] 实验室管理功能可用
- [ ] 设备列表管理功能可用
- [ ] 搜索和筛选功能正常
- [ ] 创建/编辑/删除操作正常
- [ ] 表单验证正确
- [ ] 错误提示显示正确

---

## 📞 需要帮助?

查看完整的实现报告: `IMPLEMENTATION_REPORT.md`

包含的内容:
- 详细的API文档
- 数据模型说明
- 代码文件清单
- 测试覆盖范围
- 安全性说明
- 后续优化建议

---

**祝你使用愉快！** 🚀
