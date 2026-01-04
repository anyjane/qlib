<template>
  <div class="position-manager">
    <el-card shadow="hover">
      <!-- 工具栏 -->
      <div class="toolbar">
        <el-button type="primary" @click="handleImport">
          <i class="el-icon-upload2"></i>
          导入持仓
        </el-button>

        <el-button type="success" icon="el-icon-refresh" @click="handleSync">
          <i class="el-icon-refresh"></i>
          同步持仓
        </el-button>

        <el-button type="warning" icon="el-icon-plus" @click="handleAdd">添加</el-button>

        <el-button
          type="danger"
          :disabled="selectedPositions.length === 0"
          @click="handleBatchDelete"
        >
          <i class="el-icon-delete"></i>
          批量删除
        </el-button>
      </div>

      <!-- 持仓表格 -->
      <el-table
        :data="positions"
        v-loading="loading"
        style="width: 100%; margin-top: 20px"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55"></el-table-column>

        <el-table-column prop="code" label="股票代码" width="120"></el-table-column>

        <el-table-column prop="name" label="股票名称" width="150"></el-table-column>

        <el-table-column prop="quantity" label="持仓数量" width="100"></el-table-column>

        <el-table-column prop="cost_price" label="成本价" width="100">
          <template #default="{ row }">
            ¥{{ row.cost_price?.toFixed(2) || '0.00' }}
          </template>
        </el-table-column>

        <el-table-column prop="market_value" label="市值" width="120">
          <template #default="{ row }">
            ¥{{ row.market_value?.toFixed(2) || '0.00' }}
          </template>
        </el-table-column>

        <el-table-column prop="pnl" label="盈亏" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.pnl >= 0 ? '#67c23a' : '#f56c6c' }">
              ¥{{ row.pnl?.toFixed(2) || '0.00' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="pnl_percent" label="盈亏%" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.pnl_percent >= 0 ? '#67c23a' : '#f56c6c' }">
              {{ row.pnl_percent?.toFixed(2) || '0.00' }}%
            </span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" type="primary" icon="el-icon-edit" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button size="small" type="danger" icon="el-icon-delete" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'

export default {
  name: 'PositionManager',
  setup() {
    const positions = ref([])
    const loading = ref(false)
    const selectedPositions = ref([])

    const loadPositions = async () => {
      loading.value = true
      try {
        positions.value = await request.get('/api/positions/')
      } catch (error) {
        ElMessage.error('加载持仓列表失败')
      } finally {
        loading.value = false
      }
    }

    const handleSelectionChange = (selection) => {
      selectedPositions.value = selection
    }

    const handleSync = async () => {
      try {
        await request.post('/api/positions/sync')
        ElMessage.success('同步持仓成功')
        loadPositions()
      } catch (error) {
        ElMessage.error('同步持仓失败')
      }
    }

    const handleImport = () => {
      ElMessage.info('导入功能待实现')
    }

    const handleAdd = () => {
      ElMessage.info('添加功能待实现')
    }

    const handleEdit = (position) => {
      ElMessage.info('编辑功能待实现')
    }

    const handleDelete = async (position) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除持仓 ${position.code} 吗？`,
          '警告',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await request.delete(`/api/positions/${position.code}`)
        ElMessage.success('删除成功')
        loadPositions()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败')
        }
      }
    }

    const handleBatchDelete = async () => {
      const codes = selectedPositions.value.map(p => p.code)

      try {
        await ElMessageBox.confirm(
          `确定要删除选中的 ${codes.length} 个持仓吗？`,
          '警告',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await request.post('/api/positions/batch', {
          codes,
          operation: 'delete'
        })
        ElMessage.success('批量删除成功')
        loadPositions()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('批量删除失败')
        }
      }
    }

    onMounted(() => {
      loadPositions()
    })

    return {
      positions,
      loading,
      selectedPositions,
      loadPositions,
      handleSelectionChange,
      handleSync,
      handleImport,
      handleAdd,
      handleEdit,
      handleDelete,
      handleBatchDelete
    }
  }
}
</script>

<style scoped>
.position-manager {
  padding: 20px;
}

.toolbar {
  display: flex;
  gap: 10px;
}
</style>
