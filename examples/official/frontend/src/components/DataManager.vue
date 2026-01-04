<template>
  <div class="data-manager">
    <el-card shadow="hover">
      <div class="header">
        <h2>数据管理</h2>
        <el-button type="primary" icon="el-icon-download" @click="handleDownload">
          下载数据
        </el-button>
        <el-button type="success" icon="el-icon-refresh" @click="handleUpdate">
          增量更新
        </el-button>
      </div>

      <el-divider></el-divider>

      <div class="info">
        <p><strong>最新数据日期：</strong>{{ latestDate || '暂无数据' }}</p>
        <p>从腾讯财经 API 下载数据，支持初始下载和增量更新</p>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

export default {
  name: 'DataManager',
  setup() {
    const latestDate = ref('')

    const loadLatestDate = async () => {
      try {
        const data = await request.get('/api/data/latest_date')
        latestDate.value = data.latest_date
      } catch (error) {
        ElMessage.error('获取数据日期失败')
      }
    }

    const handleDownload = async () => {
      try {
        await request.post('/api/data/download', {
          start_date: '2015-01-01',
          end_date: null
        })
        ElMessage.success('下载任务已创建')
      } catch (error) {
        ElMessage.error('创建下载任务失败')
      }
    }

    const handleUpdate = async () => {
      try {
        await request.post('/api/data/update')
        ElMessage.success('更新任务已创建')
      } catch (error) {
        ElMessage.error('创建更新任务失败')
      }
    }

    onMounted(() => {
      loadLatestDate()
    })

    return {
      latestDate,
      handleDownload,
      handleUpdate
    }
  }
}
</script>

<style scoped>
.data-manager {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info {
  margin-top: 20px;
  color: #606266;
}

.info p {
  margin: 10px 0;
}
</style>
