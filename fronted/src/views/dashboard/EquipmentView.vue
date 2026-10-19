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
import { equipment } from '../../api/equipment'
import { laboratory } from '../../api/laboratory'

const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('添加设备')
const isEditing = ref(false)
const searchKeyword = ref('')
const searchLaboratoryId = ref(null)
const searchMaintenanceStatus = ref(null)
const tableRef = ref()

const listData = reactive({
  items: [],
  total: 0,
  currentPage: 1,
  pageSize: 10,
})

const laboratoryList = ref([])

const formData = reactive({
  id: null,
  name: '',
  equipment_type: '',
  laboratory_id: null,
  model: '',
  serial_number: '',
  description: '',
  purchase_date: '',
  maintenance_status: '正常',
  status: 1,
})

const formRules = {
  name: [
    { required: true, message: '请输入设备名称', trigger: 'blur' },
    { min: 1, max: 100, message: '名称长度应为1-100个字符', trigger: 'blur' },
  ],
  equipment_type: [
    { required: true, message: '请输入设备类型', trigger: 'blur' },
    { min: 1, max: 50, message: '类型长度应为1-50个字符', trigger: 'blur' },
  ],
  laboratory_id: [
    { required: true, message: '请选择所属实验室', trigger: 'blur' },
  ],
  purchase_date: [
    {
      type: 'string',
      pattern: /^\d{4}-\d{2}-\d{2}$/,
      message: '请输入正确的日期格式 (YYYY-MM-DD)',
      trigger: 'blur',
    },
  ],
}

const formRef = ref()

const equipmentTypeOptions = [
  { label: '显微镜', value: '显微镜' },
  { label: '分析天平', value: '分析天平' },
  { label: '分光光度计', value: '分光光度计' },
  { label: '离心机', value: '离心机' },
  { label: '高温炉', value: '高温炉' },
  { label: '冷冻箱', value: '冷冻箱' },
  { label: '干燥箱', value: '干燥箱' },
  { label: '培养皿', value: '培养皿' },
  { label: '其他', value: '其他' },
]

const maintenanceStatusOptions = [
  { label: '正常', value: '正常' },
  { label: '维修中', value: '维修中' },
  { label: '停用', value: '停用' },
]

const statusOptions = [
  { label: '正常', value: 1 },
  { label: '禁用', value: 0 },
]

const columns = [
  {
    prop: 'id',
    label: 'ID',
    width: 60,
    sortable: 'custom',
  },
  {
    prop: 'name',
    label: '设备名称',
    minWidth: 150,
  },
  {
    prop: 'equipment_type',
    label: '设备类型',
    minWidth: 120,
  },
  {
    prop: 'model',
    label: '型号',
    minWidth: 120,
  },
  {
    prop: 'serial_number',
    label: '序列号',
    minWidth: 120,
    showOverflowTooltip: true,
  },
  {
    prop: 'maintenance_status',
    label: '维护状态',
    width: 100,
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

async function fetchEquipment() {
  loading.value = true
  try {
    const skip = (listData.currentPage - 1) * listData.pageSize
    const filters = {}

    if (searchKeyword.value) {
      filters.keyword = searchKeyword.value
    }
    if (searchLaboratoryId.value) {
      filters.laboratory_id = searchLaboratoryId.value
    }
    if (searchMaintenanceStatus.value) {
      filters.maintenance_status = searchMaintenanceStatus.value
    }

    const response = await equipment.list(skip, listData.pageSize, filters)
    if (response.code === 200) {
      listData.items = response.data.items || []
      listData.total = response.data.total || 0
    } else {
      ElMessage.error(response.message || '获取设备列表失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '获取设备列表失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  formData.id = null
  formData.name = ''
  formData.equipment_type = ''
  formData.laboratory_id = null
  formData.model = ''
  formData.serial_number = ''
  formData.description = ''
  formData.purchase_date = ''
  formData.maintenance_status = '正常'
  formData.status = 1
}

async function openDialog(row = null) {
  resetForm()
  if (row) {
    isEditing.value = true
    dialogTitle.value = '编辑设备'
    Object.assign(formData, row)
  } else {
    isEditing.value = false
    dialogTitle.value = '添加设备'
  }
  dialogVisible.value = true
}

async function saveForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    let response
    if (isEditing.value) {
      response = await equipment.update(formData.id, {
        name: formData.name,
        equipment_type: formData.equipment_type,
        laboratory_id: formData.laboratory_id,
        model: formData.model || null,
        serial_number: formData.serial_number || null,
        description: formData.description || null,
        purchase_date: formData.purchase_date || null,
        maintenance_status: formData.maintenance_status,
        status: formData.status,
      })
    } else {
      response = await equipment.create({
        name: formData.name,
        equipment_type: formData.equipment_type,
        laboratory_id: formData.laboratory_id,
        model: formData.model || null,
        serial_number: formData.serial_number || null,
        description: formData.description || null,
        purchase_date: formData.purchase_date || null,
        maintenance_status: formData.maintenance_status,
        status: formData.status,
      })
    }

    if (response.code === 200) {
      ElMessage.success(response.message || (isEditing.value ? '设备更新成功' : '设备创建成功'))
      dialogVisible.value = false
      await fetchEquipment()
    } else {
      ElMessage.error(response.message || '操作失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

async function deleteEquipment(row) {
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

    const response = await equipment.delete(row.id)
    if (response.code === 200) {
      ElMessage.success('设备已删除')
      await fetchEquipment()
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
  fetchEquipment()
}

function handleReset() {
  searchKeyword.value = ''
  searchLaboratoryId.value = null
  searchMaintenanceStatus.value = null
  listData.currentPage = 1
  fetchEquipment()
}

function handlePageChange() {
  fetchEquipment()
}

onMounted(() => {
  fetchLaboratories()
  fetchEquipment()
})
</script>

<template>
  <div class="equipment-container">
    <!-- 搜索和操作栏 -->
    <div class="toolbar">
      <div class="search-box">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索设备名称、型号或序列号..."
          :prefix-icon="Search"
          clearable
          style="max-width: 250px"
        />

        <el-select
          v-model="searchLaboratoryId"
          placeholder="选择实验室"
          clearable
          style="max-width: 200px"
        >
          <el-option
            v-for="lab in laboratoryList"
            :key="lab.id"
            :label="lab.name"
            :value="lab.id"
          />
        </el-select>

        <el-select
          v-model="searchMaintenanceStatus"
          placeholder="选择维护状态"
          clearable
          style="max-width: 150px"
        >
          <el-option
            v-for="option in maintenanceStatusOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>

        <el-button type="primary" @click="handleSearch">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <div class="actions">
        <el-button :icon="Refresh" circle @click="fetchEquipment" />
        <el-button type="primary" :icon="Plus" @click="openDialog">添加设备</el-button>
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
      <el-table-column prop="name" label="设备名称" min-width="150" />
      <el-table-column prop="equipment_type" label="设备类型" min-width="120" />
      <el-table-column prop="model" label="型号" min-width="120" />
      <el-table-column
        prop="serial_number"
        label="序列号"
        min-width="120"
        show-overflow-tooltip
      />
      <el-table-column prop="maintenance_status" label="维护状态" width="100" />
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
            @click="deleteEquipment(row)"
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
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        label-position="top"
      >
        <el-form-item label="设备名称" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入设备名称"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="设备类型" prop="equipment_type">
          <el-select
            v-model="formData.equipment_type"
            placeholder="请选择设备类型"
            filterable
            allow-create
          >
            <el-option
              v-for="option in equipmentTypeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="所属实验室" prop="laboratory_id">
          <el-select
            v-model="formData.laboratory_id"
            placeholder="请选择所属实验室"
          >
            <el-option
              v-for="lab in laboratoryList"
              :key="lab.id"
              :label="lab.name"
              :value="lab.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="设备型号">
          <el-input
            v-model="formData.model"
            placeholder="请输入设备型号"
            maxlength="100"
          />
        </el-form-item>

        <el-form-item label="序列号">
          <el-input
            v-model="formData.serial_number"
            placeholder="请输入序列号"
            maxlength="100"
          />
        </el-form-item>

        <el-form-item label="购入日期" prop="purchase_date">
          <el-date-picker
            v-model="formData.purchase_date"
            type="date"
            placeholder="选择购入日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>

        <el-form-item label="维护状态">
          <el-select
            v-model="formData.maintenance_status"
            placeholder="请选择维护状态"
          >
            <el-option
              v-for="option in maintenanceStatusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
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

        <el-form-item label="设备描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            placeholder="请输入设备描述"
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
.equipment-container {
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
