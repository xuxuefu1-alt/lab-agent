<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { adminUser } from '../../api/admin_user'

const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('添加用户')
const isEditing = ref(false)
const searchKeyword = ref('')
const searchRole = ref(null)

const listData = reactive({
  items: [],
  total: 0,
  currentPage: 1,
  pageSize: 10,
})

const formData = reactive({
  id: null,
  username: '',
  password: '',
  name: '',
  email: '',
  phone: '',
  role: 'student',
  status: 1,
})

const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度应为3-50个字符', trigger: 'blur' },
  ],
  password: [
    { required: !isEditing.value, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度应为6-50个字符', trigger: 'blur' },
  ],
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { min: 2, max: 50, message: '姓名长度应为2-50个字符', trigger: 'blur' },
  ],
  email: [
    {
      type: 'email',
      message: '请输入正确的邮箱地址',
      trigger: ['blur', 'change'],
    },
  ],
}

const formRef = ref()

const roleOptions = [
  { label: '学生', value: 'student' },
  { label: '管理员', value: 'admin' },
]

const statusOptions = [
  { label: '正常', value: 1 },
  { label: '禁用', value: 0 },
]

async function fetchUsers() {
  loading.value = true
  try {
    const skip = (listData.currentPage - 1) * listData.pageSize
    const response = await adminUser.list(skip, listData.pageSize, {
      keyword: searchKeyword.value || null,
      role: searchRole.value,
    })
    if (response.code === 200) {
      listData.items = response.data.items || []
      listData.total = response.data.total || 0
    } else {
      ElMessage.error(response.message || '获取用户列表失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  formData.id = null
  formData.username = ''
  formData.password = ''
  formData.name = ''
  formData.email = ''
  formData.phone = ''
  formData.role = 'student'
  formData.status = 1
}

function openDialog(row = null) {
  if (row) {
    isEditing.value = true
    dialogTitle.value = '编辑用户'
    Object.assign(formData, row)
    formData.password = '' // 编辑时不显示密码
  } else {
    isEditing.value = false
    dialogTitle.value = '添加用户'
    resetForm()
  }
  dialogVisible.value = true
}

async function saveForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    let response
    // 双重保险：检查 id 和 isEditing 状态
    if (isEditing.value && formData.id) {
      const updateData = {
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        role: formData.role,
        status: formData.status,
      }
      response = await adminUser.update(formData.id, updateData)
    } else {
      response = await adminUser.create({
        username: formData.username,
        password: formData.password,
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        role: formData.role,
      })
    }

    if (response.code === 200) {
      ElMessage.success(response.message || (isEditing.value ? '用户更新成功' : '用户创建成功'))
      dialogVisible.value = false
      await fetchUsers()
    } else {
      ElMessage.error(response.message || '操作失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

async function deleteUser(row) {
  try {
    await ElMessageBox.confirm(`确定要删除用户"${row.name}"吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    const response = await adminUser.delete(row.id)
    if (response.code === 200) {
      ElMessage.success('用户已删除')
      await fetchUsers()
    } else {
      ElMessage.error(response.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

async function toggleStatus(row) {
  try {
    const response = await adminUser.toggleStatus(row.id)
    if (response.code === 200) {
      ElMessage.success('用户状态已切换')
      await fetchUsers()
    } else {
      ElMessage.error(response.message || '操作失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

function handleSearch() {
  listData.currentPage = 1
  fetchUsers()
}

function handleReset() {
  searchKeyword.value = ''
  searchRole.value = null
  listData.currentPage = 1
  fetchUsers()
}

function handlePageChange() {
  fetchUsers()
}

onMounted(() => {
  fetchUsers()
})
</script>

<template>
  <div class="user-management-container">
    <!-- 搜索和操作栏 -->
    <div class="toolbar">
      <div class="search-box">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索用户名、姓名或邮箱..."
          :prefix-icon="Search"
          clearable
          @keyup.enter="handleSearch"
          style="max-width: 300px"
        />

        <el-select
          v-model="searchRole"
          placeholder="选择角色"
          clearable
          style="max-width: 150px"
        >
          <el-option
            v-for="option in roleOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>

        <el-button type="primary" @click="handleSearch">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <div class="actions">
        <el-button :icon="Refresh" circle @click="fetchUsers" />
        <el-button type="primary" :icon="Plus" @click="openDialog">添加用户</el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-table ref="tableRef" :data="listData.items" :loading="loading" stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" sortable="custom" />
      <el-table-column prop="username" label="用户名" min-width="120" />
      <el-table-column prop="name" label="姓名" min-width="120" />
      <el-table-column prop="email" label="邮箱" min-width="150" show-overflow-tooltip />
      <el-table-column prop="phone" label="手机号" width="120" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'info'">
            {{ row.role === 'admin' ? '管理员' : '学生' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'">
            {{ row.status === 1 ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            text
            size="small"
            :icon="Edit"
            @click="openDialog(row)"
          >
            编辑
          </el-button>
          <el-button
            type="warning"
            text
            size="small"
            @click="toggleStatus(row)"
          >
            {{ row.status === 1 ? '禁用' : '启用' }}
          </el-button>
          <el-button
            type="danger"
            text
            size="small"
            :icon="Delete"
            @click="deleteUser(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="listData.currentPage"
        v-model:page-size="listData.pageSize"
        :page-sizes="[5, 10, 20, 50]"
        :total="listData.total"
        layout="total, sizes, prev, pager, next, jumper"
        @change="handlePageChange"
      />
    </div>

    <!-- 编辑/添加对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        label-position="top"
      >
        <el-form-item label="用户名" prop="username" v-if="!isEditing">
          <el-input
            v-model="formData.username"
            placeholder="请输入用户名"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="密码" prop="password" v-if="!isEditing">
          <el-input
            v-model="formData.password"
            type="password"
            placeholder="请输入密码"
            maxlength="50"
            show-password
          />
        </el-form-item>

        <el-form-item label="姓名" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入姓名"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="formData.email"
            placeholder="请输入邮箱"
            maxlength="100"
          />
        </el-form-item>

        <el-form-item label="手机号">
          <el-input
            v-model="formData.phone"
            placeholder="请输入手机号"
            maxlength="20"
          />
        </el-form-item>

        <el-form-item label="角色">
          <el-select v-model="formData.role" placeholder="请选择角色">
            <el-option
              v-for="option in roleOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="状态" v-if="isEditing">
          <el-select v-model="formData.status" placeholder="请选择状态">
            <el-option
              v-for="option in statusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.user-management-container {
  padding: 20px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 10px;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
