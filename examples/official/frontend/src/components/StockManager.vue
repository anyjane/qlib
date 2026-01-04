<template>
  <div class="stock-manager">
    <el-card shadow="hover">
      <!-- 工具栏 -->
      <div class="toolbar">
        <el-button type="primary" @click="handleInitialize">
          <i class="el-icon-refresh"></i>
          重新初始化代码列表
        </el-button>

        <el-button type="success" @click="handleImport">
          <i class="el-icon-upload2"></i>
          导入股票
        </el-button>

        <el-dropdown @command="handleExport" split-button type="primary">
          <el-button type="primary" size="small">
            导出股票
            <i class="el-icon-arrow-down el-icon--right"></i>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="csv">导出为 CSV</el-dropdown-item>
              <el-dropdown-item command="excel">导出为 Excel</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button type="success" icon="el-icon-plus" @click="handleAdd">添加</el-button>

        <el-button
          type="danger"
          :disabled="selectedStocks.length === 0"
          @click="handleBatchDelete"
        >
          <i class="el-icon-delete"></i>
          批量删除
        </el-button>

        <el-button
          type="warning"
          :disabled="selectedStocks.length === 0"
          @click="handleBatchEnable(true)"
        >
          <i class="el-icon-check"></i>
          批量启用
        </el-button>

        <el-button
          type="warning"
          :disabled="selectedStocks.length === 0"
          @click="handleBatchEnable(false)"
        >
          <i class="el-icon-close"></i>
          批量禁用
        </el-button>

        <el-input
          v-model="searchQuery"
          placeholder="搜索股票代码或名称"
          clearable
          style="width: 200px; margin-left: 10px"
        >
          <template #prefix>
            <i class="el-input__icon el-icon-search"></i>
          </template>
        </el-input>

        <el-button icon="el-icon-refresh" @click="loadStocks">刷新</el-button>
      </div>

      <!-- 数据表格 -->
      <el-table
        :data="filteredStocks"
        v-loading="loading"
        style="width: 100%; margin-top: 20px"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55"></el-table-column>

        <el-table-column prop="code" label="股票代码" width="120"></el-table-column>

        <el-table-column prop="name" label="股票名称" width="150"></el-table-column>

        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="A500" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_a500 ? 'success' : 'info'" size="small">
              {{ row.is_a500 ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button
              size="small"
              :type="row.enabled ? 'warning' : 'success'"
              @click="handleToggleEnable(row)"
            >
              {{ row.enabled ? '禁用' : '启用' }}
            </el-button>

            <el-button
              size="small"
              type="primary"
              icon="el-icon-edit"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>

            <el-button
              size="small"
              type="danger"
              icon="el-icon-delete"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="margin-top: 20px; text-align: right">
        <span style="margin-right: 10px">
          共 {{ filteredStocks.length }} 条
        </span>
      </div>
    </el-card>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入股票" width="500px">
      <el-upload
        ref="uploadRef"
        class="upload-demo"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
      >
        <i class="el-icon-upload"></i>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 CSV 和 Excel 格式，请确保文件包含 code 和 name 列
          </div>
        </template>
      </el-upload>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="importDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmImport">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑股票" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="股票代码">
          <el-input v-model="editForm.code" disabled></el-input>
        </el-form-item>

        <el-form-item label="股票名称">
          <el-input v-model="editForm.name"></el-input>
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmEdit">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 添加对话框 -->
    <el-dialog v-model="addDialogVisible" title="添加股票" width="500px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="股票代码" required>
          <el-input
            v-model="addForm.code"
            placeholder="例如：sh600000"
          ></el-input>
        </el-form-item>

        <el-form-item label="股票名称" required>
          <el-input v-model="addForm.name" placeholder="例如：平安银行"></el-input>
        </el-form-item>

        <el-form-item label="A500">
          <el-switch v-model="addForm.is_a500"></el-switch>
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="addDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmAdd">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { stockApi } from '../api/stock'

export default {
  name: 'StockManager',
  setup() {
    const stocks = ref([])
    const loading = ref(false)
    const selectedStocks = ref([])
    const searchQuery = ref('')

    // 对话框状态
    const importDialogVisible = ref(false)
    const editDialogVisible = ref(false)
    const addDialogVisible = ref(false)

    // 表单数据
    const editForm = ref({
      code: '',
      name: ''
    })

    const addForm = ref({
      code: '',
      name: '',
      is_a500: false
    })

    // 上传文件
    const uploadFile = ref(null)

    // 计算属性
    const filteredStocks = computed(() => {
      if (!searchQuery.value) return stocks.value

      const query = searchQuery.value.toLowerCase()
      return stocks.value.filter(stock =>
        stock.code.toLowerCase().includes(query) ||
        stock.name.toLowerCase().includes(query)
      )
    })

    // 加载股票列表
    const loadStocks = async () => {
      loading.value = true
      try {
        stocks.value = await stockApi.getStocks()
      } catch (error) {
        ElMessage.error('加载股票列表失败')
      } finally {
        loading.value = false
      }
    }

    // 格式化日期
    const formatDate = (dateString) => {
      if (!dateString) return '-'
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN')
    }

    // 处理选择变化
    const handleSelectionChange = (selection) => {
      selectedStocks.value = selection
    }

    // 重新初始化
    const handleInitialize = async () => {
      try {
        await ElMessageBox.confirm(
          '确定要重新初始化股票列表吗？此操作将清空现有数据。',
          '警告',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await stockApi.initializeStocks()
        ElMessage.success('初始化成功')
        loadStocks()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('初始化失败')
        }
      }
    }

    // 导入
    const handleImport = () => {
      importDialogVisible.value = true
    }

    // 导出
    const handleExport = async (format) => {
      try {
        const response = await stockApi.exportStocks(format)

        // 创建下载链接
        const url = window.URL.createObjectURL(new Blob([response], {
          type: format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }))

        const link = document.createElement('a')
        link.href = url
        link.download = `stocks_${format}_${Date.now()}${format === 'csv' ? '.csv' : '.xlsx'}`
        link.click()

        window.URL.revokeObjectURL(url)
        ElMessage.success('导出成功')
      } catch (error) {
        ElMessage.error('导出失败')
      }
    }

    // 文件变化
    const handleFileChange = (file) => {
      uploadFile.value = file.raw
    }

    // 确认导入
    const confirmImport = async () => {
      if (!uploadFile.value) {
        ElMessage.warning('请选择文件')
        return
      }

      loading.value = true
      try {
        await stockApi.importStocks(uploadFile.value)
        ElMessage.success('导入成功')
        importDialogVisible.value = false
        loadStocks()
      } catch (error) {
        ElMessage.error('导入失败')
      } finally {
        loading.value = false
      }
    }

    // 添加
    const handleAdd = () => {
      addForm.value = {
        code: '',
        name: '',
        is_a500: false
      }
      addDialogVisible.value = true
    }

    // 确认添加
    const confirmAdd = async () => {
      if (!addForm.value.code || !addForm.value.name) {
        ElMessage.warning('请填写完整信息')
        return
      }

      loading.value = true
      try {
        await stockApi.createStock(addForm.value)
        ElMessage.success('添加成功')
        addDialogVisible.value = false
        loadStocks()
      } catch (error) {
        ElMessage.error('添加失败')
      } finally {
        loading.value = false
      }
    }

    // 编辑
    const handleEdit = (stock) => {
      editForm.value = {
        code: stock.code,
        name: stock.name
      }
      editDialogVisible.value = true
    }

    // 确认编辑
    const confirmEdit = async () => {
      if (!editForm.value.name) {
        ElMessage.warning('请填写股票名称')
        return
      }

      loading.value = true
      try {
        await stockApi.updateStock(editForm.value.code, {
          name: editForm.value.name
        })
        ElMessage.success('更新成功')
        editDialogVisible.value = false
        loadStocks()
      } catch (error) {
        ElMessage.error('更新失败')
      } finally {
        loading.value = false
      }
    }

    // 删除
    const handleDelete = async (stock) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除股票 ${stock.code} (${stock.name}) 吗？`,
          '警告',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await stockApi.deleteStock(stock.code)
        ElMessage.success('删除成功')
        loadStocks()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败')
        }
      }
    }

    // 批量删除
    const handleBatchDelete = async () => {
      const codes = selectedStocks.value.map(s => s.code)

      try {
        await ElMessageBox.confirm(
          `确定要删除选中的 ${codes.length} 个股票吗？`,
          '警告',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await stockApi.batchOperation('delete', codes)
        ElMessage.success('批量删除成功')
        loadStocks()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('批量删除失败')
        }
      }
    }

    // 批量启用/禁用
    const handleBatchEnable = async (enabled) => {
      const codes = selectedStocks.value.map(s => s.code)
      const operation = enabled ? 'enable' : 'disable'

      try {
        await stockApi.batchOperation(operation, codes)
        ElMessage.success(`批量${enabled ? '启用' : '禁用'}成功`)
        loadStocks()
      } catch (error) {
        ElMessage.error(`批量${enabled ? '启用' : '禁用'}失败`)
      }
    }

    // 切换启用状态
    const handleToggleEnable = async (stock) => {
      try {
        await stockApi.enableStock(stock.code, !stock.enabled)
        ElMessage.success(`${stock.enabled ? '禁用' : '启用'}成功`)
        loadStocks()
      } catch (error) {
        ElMessage.error('操作失败')
      }
    }

    // 生命周期
    onMounted(() => {
      loadStocks()
    })

    return {
      stocks,
      loading,
      selectedStocks,
      searchQuery,
      filteredStocks,
      importDialogVisible,
      editDialogVisible,
      addDialogVisible,
      editForm,
      addForm,
      loadStocks,
      formatDate,
      handleSelectionChange,
      handleInitialize,
      handleImport,
      handleExport,
      handleFileChange,
      confirmImport,
      handleAdd,
      confirmAdd,
      handleEdit,
      confirmEdit,
      handleDelete,
      handleBatchDelete,
      handleBatchEnable,
      handleToggleEnable
    }
  }
}
</script>

<style scoped>
.stock-manager {
  padding: 20px;
}

.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 20px;
}

.toolbar .el-button {
  margin-right: 0;
}

.upload-demo {
  text-align: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
