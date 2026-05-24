<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <router-link class="brand" to="/projects">AI 短视频运营</router-link>
      <nav class="nav-links">
        <router-link to="/projects">项目档案</router-link>
        <router-link to="/history">生成历史</router-link>
        <router-link to="/admin/gateway-providers">模型网关</router-link>
      </nav>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>
