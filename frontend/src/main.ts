/**
 * 文件说明：项目文件 main.ts 的核心逻辑实现。
 */

import { createApp } from 'vue'
import { VueQueryPlugin } from '@tanstack/vue-query'
import App from './App.vue'
import router from './router'
import { queryClient } from './app/queryClient'
import { pinia } from './stores/pinia'
import './style.css'

// Create app instance
const app = createApp(App)

// Install plugins
app.use(pinia)
app.use(router)
app.use(VueQueryPlugin, { queryClient })

// Mount app
app.mount('#app')
