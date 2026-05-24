import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import { installElementPlus } from './plugins/elementPlus'
import { router } from './router'

const app = createApp(App)
const pinia = createPinia()

installElementPlus(app)
app.use(pinia).use(router).mount('#app')
