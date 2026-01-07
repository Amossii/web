import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App.jsx'
import './index.css'
import { testAPIConnection } from './utils/apiTest'

// 在开发环境中，将测试函数暴露到全局
if (import.meta.env.DEV) {
  window.testAPI = testAPIConnection
  console.log('💡 提示: 在控制台运行 testAPI() 可以测试 API 连接')
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ConfigProvider locale={zhCN}>
        <App />
      </ConfigProvider>
    </BrowserRouter>
  </React.StrictMode>,
)

