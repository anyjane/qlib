<template>
  <div class="log-manager">
    <el-card shadow="hover">
      <h2>日志管理</h2>
      <el-divider></el-divider>

      <el-table :data="logs" style="width: 100%">
        <el-table-column prop="filename" label="文件名" width="300"></el-table-column>

        <el-table-column prop="size" label="文件大小" width="120">
          <template #default="{ row }">
            {{ formatSize(row.size) }}
          </template>
        </el-table-column>

        <el-table-column prop="modified" label="修改时间" width="200">
          <template #default="{ row }">
            {{ formatDate(row.modified) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" type="primary" icon="el-icon-download" @click="handleDownload(row.filename)">
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

export default {
  name: 'LogManager',
  setup() {
    const logs = ref([])

    const loadLogs = async () => {
      try {
        logs.value = await request.get('/api/logs/')
      } catch (error) {
        ElMessage.error('加载日志列表失败')
      }
    }

    const formatSize = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
    }

    const formatDate = (date) => {
      return new Date(date).toLocaleString('zh-CN')
    }

    const handleDownload = async (filename) => {
      try {
        const response = await request.get(`/api/logs/download/${filename}`, {
          responseType: 'blob'
        })

        const url = window.URL.createObjectURL(new Blob([response]))
        const link = document.createElement('a')
        link.href = url
        link.download = filename
        link.click()

        window.URL.revokeObjectURL(url)
        ElMessage.success('下载成功')
      } catch (error) {
        ElMessage.error('下载失败')
      }
    }

    onMounted(() => {
      loadLogs()
    })

    return {
      logs,
      formatSize,
      formatDate,
      handleDownload
    }
  }
}
</script>

<style scoped>
.log-manager {
  padding: 20px;
}
</style>
