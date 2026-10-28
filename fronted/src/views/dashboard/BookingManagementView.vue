<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Refresh } from '@element-plus/icons-vue'
import { booking } from '../../api/booking'
import { equipment } from '../../api/equipment'
import { laboratory } from '../../api/laboratory'
import { useAuthStore } from '../../stores/auth'

const authStore = useAuthStore()
const loading = ref(false)
const dialogVisible = ref(false)
const approveDialogVisible = ref(false)
const dialogTitle = ref('创建预约')
const isEditing = ref(false)
const selectedBooking = ref(null)
const formRef = ref()

const listData = reactive({
  items: [],
  total: 0,
  currentPage: 1,
  pageSize: 10,
})

const laboratoryList = ref([])
const equipmentList = ref([])
const equipmentCatalog = ref([])

const formData = reactive({
  id: null,
  laboratory_id: null,
  equipment_ids: [],
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
  laboratory_id: [{ required: true, message: '请选择实验室', trigger: 'change' }],
  start_time: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  end_time: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
  purpose: [
    { required: true, message: '请输入预约目的', trigger: 'blur' },
    { min: 1, max: 500, message: '预约目的长度应为 1-500 个字符', trigger: 'blur' },
  ],
  student_count: [{ required: true, message: '请输入学生数量', trigger: 'change' }],
}

const normalMaintenanceStatuses = ['正常', 'Normal', '姝ｅ父']

async function fetchLaboratories() {
  try {
    const response = await laboratory.list(0, 1000)
    if (response.code === 200) laboratoryList.value = response.data.items || []
  } catch (error) {
    ElMessage.error(error.message || '获取实验室列表失败')
  }
}

async function fetchEquipment(laboratoryId) {
  equipmentList.value = []
  if (!laboratoryId) return
  try {
    const response = await equipment.list(0, 1000, { laboratory_id: laboratoryId })
    if (response.code === 200) {
      equipmentList.value = (response.data.items || []).filter(
        item => item.status === 1 && normalMaintenanceStatuses.includes(item.maintenance_status),
      )
    }
  } catch (error) {
    ElMessage.error(error.message || '获取设备列表失败')
  }
}

async function fetchEquipmentCatalog() {
  try {
    const response = await equipment.list(0, 1000)
    if (response.code === 200) equipmentCatalog.value = response.data.items || []
  } catch (error) {
    console.error('获取设备目录失败', error)
  }
}

async function handleLaboratoryChange(laboratoryId) {
  formData.equipment_ids = []
  await fetchEquipment(laboratoryId)
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
  Object.assign(formData, {
    id: null,
    laboratory_id: null,
    equipment_ids: [],
    start_time: '',
    end_time: '',
    purpose: '',
    student_count: 1,
    remarks: '',
  })
  equipmentList.value = []
}

async function openDialog(row = null) {
  if (row && row.status === '待审核') {
    isEditing.value = true
    dialogTitle.value = '编辑预约'
    Object.assign(formData, row)
    formData.equipment_ids = [...(row.equipment_ids || [])]
    await fetchEquipment(row.laboratory_id)
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

  const payload = {
    laboratory_id: formData.laboratory_id,
    equipment_ids: formData.equipment_ids,
    start_time: formData.start_time,
    end_time: formData.end_time,
    purpose: formData.purpose,
    student_count: formData.student_count,
    remarks: formData.remarks,
  }

  try {
    const response = isEditing.value && formData.id
      ? await booking.update(formData.id, {
          laboratory_id: payload.laboratory_id,
          equipment_ids: payload.equipment_ids,
          start_time: payload.start_time,
          end_time: payload.end_time,
          purpose: payload.purpose,
          student_count: payload.student_count,
          remarks: payload.remarks,
        })
      : await booking.create(payload)

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

function openApproveDialog(row) {
  selectedBooking.value = row
  approveData.status = '已批准'
  approveData.reject_reason = ''
  approveData.remarks = ''
  approveDialogVisible.value = true
}

async function submitApprove() {
  if (approveData.status === '已拒绝' && !approveData.reject_reason) {
    ElMessage.error('拒绝预约时必须填写拒绝原因')
    return
  }
  try {
    const response = await booking.approve(selectedBooking.value.id, approveData)
    if (response.code === 200) {
      ElMessage.success(response.message || '预约审批完成')
      approveDialogVisible.value = false
      await fetchBookings()
    } else {
      ElMessage.error(response.message || '审批失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '审批失败')
  }
}

async function cancelBooking(row) {
  try {
    await ElMessageBox.confirm('确定要取消这条预约吗？', '取消确认', {
      confirmButtonText: '确定',
      cancelButtonText: '返回',
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
    if (error !== 'cancel') ElMessage.error(error.message || '取消失败')
  }
}

async function deleteBooking(row) {
  try {
    await ElMessageBox.confirm('确定要删除这条预约吗？', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '返回',
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
    if (error !== 'cancel') ElMessage.error(error.message || '删除失败')
  }
}

function getLabName(laboratoryId) {
  return laboratoryList.value.find(item => item.id === laboratoryId)?.name || `实验室#${laboratoryId}`
}

function getEquipmentNames(ids = []) {
  if (!ids.length) return '未选择设备'
  return ids
    .map(id => equipmentCatalog.value.find(item => item.id === id)?.name || `设备#${id}`)
    .join('、')
}

function getStatusType(status) {
  return {
    待审核: 'info',
    已批准: 'success',
    已拒绝: 'danger',
    已取消: 'warning',
  }[status] || 'info'
}

function handlePageChange() {
  fetchBookings()
}

onMounted(() => {
  fetchLaboratories()
  fetchEquipmentCatalog()
  fetchBookings()
})
</script>

<template>
  <div class="booking-management-container">
    <div class="toolbar">
      <div class="actions">
        <el-button :icon="Refresh" circle @click="fetchBookings" />
        <el-button type="primary" :icon="Plus" @click="openDialog">创建预约</el-button>
      </div>
    </div>

    <el-table :data="listData.items" :loading="loading" stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="实验室" min-width="150">
        <template #default="{ row }">{{ getLabName(row.laboratory_id) }}</template>
      </el-table-column>
      <el-table-column label="预约设备" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">{{ getEquipmentNames(row.equipment_ids || []) }}</template>
      </el-table-column>
      <el-table-column prop="start_time" label="开始时间" min-width="150" />
      <el-table-column prop="end_time" label="结束时间" min-width="150" />
      <el-table-column prop="purpose" label="预约目的" min-width="180" show-overflow-tooltip />
      <el-table-column prop="student_count" label="人数" width="80" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === '待审核' && authStore.user.role === 'admin'"
            type="primary"
            text
            size="small"
            @click="openApproveDialog(row)"
          >审批</el-button>
          <el-button
            v-if="row.status === '待审核'"
            type="warning"
            text
            size="small"
            :icon="Edit"
            @click="openDialog(row)"
          >编辑</el-button>
          <el-button
            v-if="row.status !== '已取消' && row.status !== '已拒绝'"
            type="warning"
            text
            size="small"
            @click="cancelBooking(row)"
          >取消</el-button>
          <el-button
            v-if="authStore.user.role === 'admin'"
            type="danger"
            text
            size="small"
            :icon="Delete"
            @click="deleteBooking(row)"
          >删除</el-button>
        </template>
      </el-table-column>
    </el-table>

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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="620px">
      <el-form ref="formRef" :model="formData" :rules="formRules" label-position="top">
        <el-form-item label="实验室" prop="laboratory_id">
          <el-select
            v-model="formData.laboratory_id"
            placeholder="请选择实验室"
            style="width: 100%"
            @change="handleLaboratoryChange"
          >
            <el-option
              v-for="lab in laboratoryList.filter(item => item.status === 1)"
              :key="lab.id"
              :label="`${lab.name}（${lab.location}）`"
              :value="lab.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="预约设备">
          <el-select
            v-model="formData.equipment_ids"
            multiple
            collapse-tags
            collapse-tags-tooltip
            :disabled="!formData.laboratory_id"
            placeholder="可选：选择该实验室下需要使用的设备"
            style="width: 100%"
          >
            <el-option
              v-for="item in equipmentList"
              :key="item.id"
              :label="`${item.name}（${item.equipment_type}）`"
              :value="item.id"
            />
          </el-select>
          <div class="field-hint">只展示当前实验室下处于正常状态的设备。</div>
        </el-form-item>

        <el-form-item label="开始时间" prop="start_time">
          <el-date-picker
            v-model="formData.start_time"
            type="datetime"
            placeholder="请选择开始时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="结束时间" prop="end_time">
          <el-date-picker
            v-model="formData.end_time"
            type="datetime"
            placeholder="请选择结束时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="预约目的" prop="purpose">
          <el-input v-model="formData.purpose" type="textarea" maxlength="500" show-word-limit :rows="3" />
        </el-form-item>

        <el-form-item label="学生数量" prop="student_count">
          <el-input-number v-model="formData.student_count" :min="1" :max="100" controls-position="right" />
        </el-form-item>

        <el-form-item label="备注">
          <el-input v-model="formData.remarks" type="textarea" maxlength="500" show-word-limit :rows="2" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">返回</el-button>
        <el-button type="primary" @click="saveForm">保存预约</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="approveDialogVisible" title="审批预约" width="500px">
      <el-form label-position="top">
        <el-form-item label="审批结果">
          <el-select v-model="approveData.status" style="width: 100%">
            <el-option label="批准" value="已批准" />
            <el-option label="拒绝" value="已拒绝" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="approveData.status === '已拒绝'" label="拒绝原因">
          <el-input v-model="approveData.reject_reason" type="textarea" maxlength="500" show-word-limit :rows="2" />
        </el-form-item>
        <el-form-item label="审批备注">
          <el-input v-model="approveData.remarks" type="textarea" maxlength="500" show-word-limit :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveDialogVisible = false">返回</el-button>
        <el-button type="primary" @click="submitApprove">提交审批</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.booking-management-container { padding: 20px; }
.toolbar { display: flex; justify-content: flex-end; margin-bottom: 20px; }
.actions { display: flex; gap: 10px; align-items: center; }
.pagination { display: flex; justify-content: flex-end; margin-top: 20px; }
.field-hint { color: #909399; font-size: 12px; line-height: 20px; margin-top: 4px; }
</style>
