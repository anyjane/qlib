import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/stocks'
  },
  {
    path: '/stocks',
    name: 'StockManager',
    component: () => import('./components/StockManager.vue')
  },
  {
    path: '/data',
    name: 'DataManager',
    component: () => import('./components/DataManager.vue')
  },
  {
    path: '/predict',
    name: 'PredictionModule',
    component: () => import('./components/PredictionModule.vue')
  },
  {
    path: '/positions',
    name: 'PositionManager',
    component: () => import('./components/PositionManager.vue')
  },
  {
    path: '/agent',
    name: 'AgentManager',
    component: () => import('./components/AgentManager.vue')
  },
  {
    path: '/logs',
    name: 'LogManager',
    component: () => import('./components/LogManager.vue')
  },
  {
    path: '/backtest',
    name: 'BacktestManager',
    component: () => import('./components/BacktestManager.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
