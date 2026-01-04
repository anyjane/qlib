<template>
  <div id="app">
    <el-container style="height: 100vh">
      <el-header>
        <h1>量化投资管理系统</h1>
      </el-header>
      <el-container>
        <el-aside width="200px">
          <el-menu
            default-active="1"
            class="el-menu-vertical-demo"
            router
          >
            <el-menu-item index="/stocks">
              <i class="el-icon-document"></i>
              <span>代码管理</span>
            </el-menu-item>
            <el-menu-item index="/data">
              <i class="el-icon-download"></i>
              <span>数据管理</span>
            </el-menu-item>
            <el-menu-item index="/predict">
              <i class="el-icon-data-analysis"></i>
              <span>预测结果</span>
            </el-menu-item>
            <el-menu-item index="/positions">
              <i class="el-icon-wallet"></i>
              <span>持仓管理</span>
            </el-menu-item>
            <el-menu-item index="/agent">
              <i class="el-icon-setting"></i>
              <span>代理管理</span>
            </el-menu-item>
            <el-menu-item index="/logs">
              <i class="el-icon-folder-opened"></i>
              <span>日志管理</span>
            </el-menu-item>
          </el-menu>
        </el-aside>
        <el-main>
          <router-view></router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
}
</style>
