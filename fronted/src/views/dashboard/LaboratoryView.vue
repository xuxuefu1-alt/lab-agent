<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Delete,
  Edit,
  Plus,
  Refresh,
  Search,
} from '@element-plus/icons-vue'
import { laboratory } from '../../api/laboratory'

const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('添加实验室')
const isEditing = ref(false)
const searchKeyword = ref('')
const tableRef = ref()

const listData = reactive({
  items: [],
  total: 0,
  currentPage: 1,
  pageSize: 10,
})

const formData = reactive({
  id: null,
  name: '',
  description: '',
  location: '',
  capacity: 0,
  manager_id: null,
  status: 1,
})

const formRules = {
  name: [
    { required: true, message: '请输入实验室名称', trigger: 'blur' },
    { min: 1, max: 100, message: '名称长度应为1-100个字符', trigger: 'blur' },
  ],
  location: [
    { required: true, message: '请输入实验室位置', trigger: 'blur' },
    { min: 1, max: 255, message: '位置长度应为1-255个字符', trigger: 'blur' },
  ],
  capacity: [
    { required: true, message: '请输入容纳人数', trigger: 'blur' },
    { type: 'number', message: '容纳人数必须为数字', trigger: 'blur' },
  ],
  manager_id: [
    { required: true, message: '请选择管理员', trigger: 'blur' },
  ],
}

const formRef = ref()

const columns = [
  {
    prop: 'id',
    label: 'ID',
    width: 60,
    sortable: 'custom',
  },
  {
    prop: 'name',
    label: '实验室名称',
    minWidth: 150,
  },
  {
    prop: 'location',
    label: '位置',
    minWidth: 150,
  },
  {
    prop: 'capacity',
    label: '容纳人数',
    width: 100,
  },
  {
    prop: 'description',
    label: '描述',
    minWidth: 200,
    showOverflowTooltip: true,
  },
  {
    prop: 'status',
    label: '状态',
    width: 100,
    formatter: (row) => (row.status === 1 ? '正常' : '禁用'),
  },
  {
    label: '操作',
    width: 150,
    align: 'center',
    fixed: 'right',
  },
]

const statusOptions = [
  { label: '正常', value: 1 },
  { label: '禁用', value: 0 },
]

function getAvailabilityLabel(row) {
  if (row.status !== 1) return '已停用'
  return row.availability_label || '可预约'
}

function getAvailabilityTagType(row) {
  if (row.status !== 1) return 'info'
  if (row.availability_status === 'occupied') return 'danger'
  if (row.availability_status === 'pending' || row.availability_status === 'reserved') return 'warning'
  return 'success'
}

function getReservation(row) {
  return row.reservation || null
}

function getReservations(row) {
  if (Array.isArray(row.reservations) && row.reservations.length) return row.reservations
  return getReservation(row) ? [getReservation(row)] : []
}

function getReservationStatusLabel(status) {
  if (status === '已批准') return '已审批'
  if (status === '待审核') return '待审批'
  return status || '未知'
}

function getReservationStatusType(status) {
  return status === '已批准' ? 'success' : 'warning'
}

function getReservationUser(reservation) {
  return reservation?.user_name || reservation?.username || '未设置'
}

function getReservationApprover(reservation) {
  return reservation?.approved_by_name || reservation?.approved_by_username || '--'
}

async function fetchLaboratories() {
  loading.value = true
  try {
    const skip = (listData.currentPage - 1) * listData.pageSize
    const response = await laboratory.list(skip, listData.pageSize, searchKeyword.value || null)
    if (response.code === 200) {
      listData.items = response.data.items || []
      listData.total = response.data.total || 0
    } else {
      ElMessage.error(response.message || '获取实验室列表失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '获取实验室列表失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  formData.id = null
  formData.name = ''
  formData.description = ''
  formData.location = ''
  formData.capacity = 0
  formData.manager_id = null
  formData.status = 1
}

async function openDialog(row = null) {
  if (row) {
    isEditing.value = true
    dialogTitle.value = '编辑实验室'
    Object.assign(formData, row)
  } else {
    isEditing.value = false
    dialogTitle.value = '添加实验室'
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
      response = await laboratory.update(formData.id, {
        name: formData.name,
        description: formData.description,
        location: formData.location,
        capacity: formData.capacity,
        manager_id: formData.manager_id,
        status: formData.status,
      })
    } else {
      response = await laboratory.create({
        name: formData.name,
        description: formData.description,
        location: formData.location,
        capacity: formData.capacity,
        manager_id: formData.manager_id,
        status: formData.status,
      })
    }

    if (response.code === 200) {
      ElMessage.success(response.message || (isEditing.value ? '实验室更新成功' : '实验室创建成功'))
      dialogVisible.value = false
      await fetchLaboratories()
    } else {
      ElMessage.error(response.message || '操作失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

async function deleteLaboratory(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除"${row.name}"吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    const response = await laboratory.delete(row.id)
    if (response.code === 200) {
      ElMessage.success('实验室已删除')
      await fetchLaboratories()
    } else {
      ElMessage.error(response.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

function handleSearch() {
  listData.currentPage = 1
  fetchLaboratories()
}

function handleReset() {
  searchKeyword.value = ''
  listData.currentPage = 1
  fetchLaboratories()
}

function handlePageChange() {
  fetchLaboratories()
}

onMounted(() => {
  fetchLaboratories()
})
</script>

<template>
  <div class="laboratory-container">
    <!-- 搜索和操作栏 -->
    <div class="toolbar">
      <div class="search-box">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索实验室名称或位置..."
          :prefix-icon="Search"
          clearable
          @keyup.enter="handleSearch"
          style="max-width: 300px"
        />
        <el-button type="primary" @click="handleSearch">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <div class="actions">
        <el-button :icon="Refresh" circle @click="fetchLaboratories" />
        <el-button type="primary" :icon="Plus" @click="openDialog">添加实验室</el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-table
      ref="tableRef"
      :data="listData.items"
      :columns="columns"
      :loading="loading"
      stripe
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="60" sortable="custom" />
      <el-table-column prop="name" label="实验室名称" min-width="150" />
      <el-table-column prop="location" label="位置" min-width="150" />
      <el-table-column prop="capacity" label="容纳人数" width="100" />
      <el-table-column label="预约状态" width="120">
        <template #default="{ row }">
          <el-popover v-if="getReservations(row).length" placement="top-start" :width="360" trigger="hover">
            <template #reference>
              <el-tag :type="getAvailabilityTagType(row)" size="small" class="reservation-trigger">
                存在预约
              </el-tag>
            </template>
            <div class="reservation-popover">
              <div class="reservation-popover-title">预约详情（{{ getReservations(row).length }} 条）</div>
              <div
                v-for="(reservation, index) in getReservations(row)"
                :key="reservation.id || index"
                class="reservation-item"
              >
                <div class="reservation-popover-row">
                  <span>预约人</span>
                  <strong>{{ getReservationUser(reservation) }}</strong>
                </div>
                <div class="reservation-popover-row">
                  <span>预约时间</span>
                  <strong>{{ reservation.start_time }} - {{ reservation.end_time }}</strong>
                </div>
                <div class="reservation-popover-row">
                  <span>审批状态</span>
                  <el-tag :type="getReservationStatusType(reservation.status)" size="small">
                    {{ getReservationStatusLabel(reservation.status) }}
                  </el-tag>
                </div>
                <div class="reservation-popover-row">
                  <span>审批人</span>
                  <strong>{{ getReservationApprover(reservation) }}</strong>
                </div>
              </div>
            </div>
          </el-popover>
          <el-tag v-else :type="getAvailabilityTagType(row)" size="small">
            {{ getAvailabilityLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        prop="description"
        label="描述"
        min-width="200"
        show-overflow-tooltip
      />
      <el-table-column
        prop="status"
        label="状态"
        width="100"
        :formatter="(row) => (row.status === 1 ? '正常' : '禁用')"
      />
      <el-table-column label="操作" width="150" align="center" fixed="right">
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
            type="danger"
            text
            size="small"
            :icon="Delete"
            @click="deleteLaboratory(row)"
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
        <el-form-item label="实验室名称" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入实验室名称"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="位置" prop="location">
          <el-input
            v-model="formData.location"
            placeholder="请输入实验室位置"
            maxlength="255"
          />
        </el-form-item>

        <el-form-item label="容纳人数" prop="capacity">
          <el-input-number
            v-model="formData.capacity"
            :min="0"
            :max="10000"
            controls-position="right"
          />
        </el-form-item>

        <el-form-item label="管理员ID" prop="manager_id">
          <el-input-number
            v-model="formData.manager_id"
            :min="1"
            controls-position="right"
          />
        </el-form-item>

        <el-form-item label="状态">
          <el-select v-model="formData.status" placeholder="请选择状态">
            <el-option
              v-for="option in statusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            placeholder="请输入实验室描述"
            maxlength="1000"
            show-word-limit
            :rows="4"
          />
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
.laboratory-container {
  padding: 20px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 10px;
}

.search-box {
  display: flex;
  gap: 10px;
  align-items: center;
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

.reservation-trigger {
  cursor: pointer;
}

.reservation-popover {
  display: grid;
  gap: 10px;
  color: #303133;
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;
}

.reservation-popover-title {
  color: #1f2937;
  font-size: 13px;
  font-weight: 600;
  padding-bottom: 2px;
}

.reservation-popover-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  font-size: 12px;
}

.reservation-popover-row > span {
  color: #909399;
  flex: 0 0 auto;
}

.reservation-popover-row > strong {
  color: #303133;
  font-weight: 500;
  text-align: right;
  line-height: 1.4;
}

.reservation-item {
  display: grid;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}

.reservation-item:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}
</style>
