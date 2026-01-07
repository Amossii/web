// API 连接测试工具
import axios from 'axios'

export const testAPIConnection = async () => {
  const results = {
    health: { status: 'pending', message: '' },
    datafiles: { status: 'pending', message: '', data: null },
    models: { status: 'pending', message: '', data: null },
  }

  // 测试健康检查
  try {
    const healthResponse = await axios.get('/health')
    results.health.status = 'success'
    results.health.message = '服务正常'
    results.health.data = healthResponse.data
    console.log('✅ 健康检查成功:', healthResponse.data)
  } catch (error) {
    results.health.status = 'error'
    results.health.message = error.message
    console.error('❌ 健康检查失败:', error)
  }

  // 测试数据文件列表
  try {
    const datafilesResponse = await axios.get('/api/datafiles/')
    results.datafiles.status = 'success'
    results.datafiles.message = '获取成功'
    results.datafiles.data = datafilesResponse.data
    console.log('✅ 数据文件列表获取成功:', datafilesResponse.data)
  } catch (error) {
    results.datafiles.status = 'error'
    results.datafiles.message = error.message
    results.datafiles.error = error.response?.data
    console.error('❌ 数据文件列表获取失败:', error)
    console.error('响应数据:', error.response?.data)
  }

  // 测试模型列表
  try {
    const modelsResponse = await axios.get('/api/models/')
    results.models.status = 'success'
    results.models.message = '获取成功'
    results.models.data = modelsResponse.data
    console.log('✅ 模型列表获取成功:', modelsResponse.data)
  } catch (error) {
    results.models.status = 'error'
    results.models.message = error.message
    results.models.error = error.response?.data
    console.error('❌ 模型列表获取失败:', error)
    console.error('响应数据:', error.response?.data)
  }

  return results
}

// 在浏览器控制台运行此函数来测试 API 连接
// window.testAPI = testAPIConnection

