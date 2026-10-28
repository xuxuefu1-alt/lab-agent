<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { booking } from '../../api/booking'
import { laboratory } from '../../api/laboratory'
import { useAuthStore } from '../../stores/auth'

const authStore = useAuthStore()
const loading = ref(false)
const dialogVisible = ref(false)
const approveDialogVisible = ref(false)
const dialogTitle = ref('创建预约')
const isEditing = ref(false)
const selectedBooking = ref(null)

const listData = reactive({
  items: [],
  total: 0,
  currentPage: 1,
  pageSize: 10,
})

const laboratoryList = ref([])

const formData = reactive({
  id: null,
  laboratory_id: null,
  start_time: '',
  end_time: '',
  purpose: '',
  student_count: 1,
  remarks: '',
})

const approveData = reactive({
  status: '已批准',
  reject_reason: '',
  remarks: '',
})

const formRules = {
  laboratory_id: [
    { required: true, message: '请选择实验室', trigger: 'blur' },
  ],
  start_time: [
    { required: true, message: '请输入开始时间', trigger: 'blur' },
  ],
  end_time: [
    { required: true, message: '请输入结束时间', trigger: 'blur' },
  ],
  purpose: [
    { required: true, message: '请输入预约目的', trigger: 'blur' },
    { min: 1, max: 500, message: '目的长度应为1-500个字符', trigger: 'blur' },
  ],
  student_count: [
    { required: true, message: '请输入学生数量', trigger: 'blur' },
    { type: 'number', message: '学生数量必须为数字', trigger: 'blur' },
  ],
}

const formRef = ref()
const approveFormRef = ref()

const statusOptions = [
  { label: '待审核', value: '待审核' },
  { label: '已批准', value: '已批准' },
  { label: '已拒绝', value: '已拒绝' },
  { label: '已取消', value: '已取消' },
]

async function fetchLaboratories() {
  try {
    const response = await laboratory.list(0, 1000)
    if (response.code === 200) {
      laboratoryList.value = response.data.items || []
    }
  } catch (error) {
    console.error('获取实验室列表失败:', error)
  }
}

async function fetchBookings() {
  loading.value = true
  try {
    const skip = (listData.currentPage - 1) * listData.pageSize
    const response = await booking.list(skip, listData.pageSize)
    if (response.code === 200) {
      listData.items = response.data.items || []
      listData.total = response.data.total || 0
    } else {
      ElMessage.error(response.message || '获取预约列表失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '获取预约列表失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  formData.id = null
  formData.laboratory_id = null
  formData.start_time = ''
  formData.end_time = ''
  formData.purpose = ''
  formData.student_count = 1
  formData.remarks = ''
}

function openDialog(row = null) {
  if (row && authStore.user.role === 'admin') {
    isEditing.value = true
    dialogTitle.value = '编辑预约'
    Object.assign(formData, row)
  } else {
    isEditing.value = false
    dialogTitle.value = '创建预约'
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
      response = await booking.update(formData.id, {
        start_time: formData.start_time,
        end_time: formData.end_time,
        purpose: formData.purpose,
        student_count: formData.student_count,
        remarks: formData.remarks,
      })
    } else {
      response = await booking.create({
        laboratory_id: formData.laboratory_id,
        start_time: formData.start_time,
        end_time: formData.end_time,
        purpose: formData.purpose,
        student_count: formData.student_count,
        remarks: formData.remarks,
      })
    }

    if (response.code === 200) {
      ElMessage.success(response.message || (isEditing.value ? '预约更新成功' : '预约创建成功'))
      dialogVisible.value = false
      await fetchBookings()
    } else {
      ElMessage.error(response.message || '操作失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

async function openApproveDialog(row) {
  selectedBooking.value = row
  approveData.status = '已批准'
  approveData.reject_reason = ''
  approveData.remarks = ''
  approveDialogVisible.value = true
}

async function submitApprove() {
  try {
    if (approveData.status === '已拒绝' && !approveData.reject_reason) {
      ElMessage.error('拒绝时必须输入拒绝原因')
      return
    }

    const response = await booking.approve(selectedBooking.value.id, {
      status: approveData.status,
      reject_reason: approveData.reject_reason,
      remarks: approveData.remarks,
    })

    if (response.code === 200) {
      ElMessage.success(response.message || `预约已${approveData.status}`)
      approveDialogVisible.value = false
      await fetchBookings()
    } else {
      ElMessage.error(response.message || '操作失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

async function cancelBooking(row) {
  try {
    await ElMessageBox.confirm('确定要取消此预约吗？', '取消确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    const response = await booking.cancel(row.id)
    if (response.code === 200) {
      ElMessage.success('预约已取消')
      await fetchBookings()
    } else {
      ElMessage.error(response.message || '取消失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '取消失败')
    }
  }
}

async function deleteBooking(row) {
  try {
    await ElMessageBox.confirm('确定要删除此预约吗？', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    const response = await booking.delete(row.id)
    if (response.code === 200) {
      ElMessage.success('预约已删除')
      await fetchBookings()
    } else {
      ElMessage.error(response.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

function handlePageChange() {
  fetchBookings()
}

function getLabName(labId) {
  const lab = laboratoryList.value.find(l => l.id === labId)
  return lab ? lab.name : '未知'
}

function getStatusType(status) {
  const types = {
    '待审核': 'info',
    '已批准': 'success',
    '已拒绝': 'danger',
    '已取消': 'warning',
  }
  return types[status] || 'info'
}

onMounted(() => {
  fetchLaboratories()
  fetchBookings()
})
</script>

<template>
  <div class="booking-management-container">
    <!-- 搜索和操作栏 -->
    <div class="toolbar">
      <div class="actions">
        <el-button :icon="Refresh" circle @click="fetchBookings" />
        <el-button type="primary" :icon="Plus" @click="openDialog">创建预约</el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-table :data="listData.items" :loading="loading" stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="实验室" min-width="150">
        <template #default="{ row }">
          {{ getLabName(row.laboratory_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="start_time" label="开始时间" min-width="150" />
      <el-table-column prop="end_time" label="结束时间" min-width="150" />
      <el-table-column prop="purpose" label="目的" min-width="150" show-overflow-tooltip />
      <el-table-column prop="student_count" label="学生数" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === '待审核' && authStore.user.role === 'admin'"
            type="primary"
            text
            size="small"
            @click="openApproveDialog(row)"
          >
            审批
          </el-button>
          <el-button
            v-if="row.status === '待审核'"
            type="warning"
            text
            size="small"
            :icon="Edit"
            @click="openDialog(row)"
          >
            编辑
          </el-button>
          <el-button
            v-if="row.status !== '已取消' && row.status !== '已拒绝'"
            type="warning"
            text
            size="small"
            @click="cancelBooking(row)"
          >
            取消
          </el-button>
          <el-button
            v-if="authStore.user.role === 'admin'"
            type="danger"
            text
            size="small"
            :icon="Delete"
            @click="deleteBooking(row)"
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

    <!-- 创建/编辑预约对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        label-position="top"
      >
        <el-form-item label="实验室" prop="laboratory_id">
          <el-select v-model="formData.laboratory_id" placeholder="请选择实验室">
            <el-option
              v-for="lab in laboratoryList"
              :key="lab.id"
              :label="lab.name"
              :value="lab.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="开始时间" prop="start_time">
          <el-date-picker
            v-model="formData.start_time"
            type="datetime"
            placeholder="选择开始时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm"
          />
        </el-form-item>

        <el-form-item label="结束时间" prop="end_time">
          <el-date-picker
            v-model="formData.end_time"
            type="datetime"
            placeholder="选择结束时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm"
          />
        </el-form-item>

        <el-form-item label="预约目的" prop="purpose">
          <el-input
            v-model="formData.purpose"
            type="textarea"
            placeholder="请输入预约目的"
            maxlength="500"
            show-word-limit
            :rows="3"
          />
        </el-form-item>

        <el-form-item label="学生数量" prop="student_count">
          <el-input-number
            v-model="formData.student_count"
            :min="1"
            :max="100"
            controls-position="right"
          />
        </el-form-item>

        <el-form-item label="备注">
          <el-input
            v-model="formData.remarks"
            type="textarea"
            placeholder="请输入备注"
            maxlength="500"
            show-word-limit
            :rows="2"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 审批预约对话框 -->
    <el-dialog v-model="approveDialogVisible" title="审批预约" width="500px">
      <el-form label-width="100px" label-position="top">
        <el-form-item label="审批状态">
          <el-select v-model="approveData.status" placeholder="请选择审批状态">
            <el-option label="已批准" value="已批准" />
            <el-option label="已拒绝" value="已拒绝" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="approveData.status === '已拒绝'" label="拒绝原因">
          <el-input
            v-model="approveData.reject_reason"
            type="textarea"
            placeholder="请输入拒绝原因"
            maxlength="500"
            show-word-limit
            :rows="2"
          />
        </el-form-item>

        <el-form-item label="备注">
          <el-input
            v-model="approveData.remarks"
            type="textarea"
            placeholder="请输入备注"
            maxlength="500"
            show-word-limit
            :rows="2"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="approveDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitApprove">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.booking-management-container {
  padding: 20px;
}

.toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 20px;
  gap: 10px;
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
