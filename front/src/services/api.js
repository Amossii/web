import axios from 'axios'
import { message } from 'antd'

const api = axios.create({
    baseURL: '/api',
    timeout: 30000,
})

// 请求拦截器
api.interceptors.request.use(
    (config) => {
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// 响应拦截器
api.interceptors.response.use(
    (response) => {
        // 对于blob类型的响应，直接返回
        if (response.config.responseType === 'blob') {
            return response.data
        }
        return response.data
    },
    (error) => {
        console.error('API请求错误:', error)
        let errorMessage = '请求失败'

        if (error.response?.data) {
            // 如果是blob类型的错误响应，需要转换
            if (error.response.data instanceof Blob) {
                error.response.data.text().then(text => {
                    try {
                        const json = JSON.parse(text)
                        message.error(json.message || json.error || '请求失败')
                    } catch {
                        message.error(text || '请求失败')
                    }
                })
            } else {
                errorMessage = error.response.data.message || error.response.data.error || '请求失败'
                message.error(errorMessage)
            }
        } else {
            errorMessage = error.message || '网络错误'
            message.error(errorMessage)
        }

        return Promise.reject(error)
    }
)

// 数据文件相关API
export const dataFileAPI = {
    // 上传CSV文件
    upload: (formData) => {
        return api.post('/datafiles/', formData)
    },
    // 获取所有数据文件列表
    getList: () => {
        return api.get('/datafiles/')
    },
    // 获取指定数据文件信息
    getById: (id) => {
        return api.get(`/datafiles/${id}`)
    },
    // 预览CSV文件内容
    preview: (id, rows = 10) => {
        return api.get(`/datafiles/${id}/preview`, {
            params: { rows }
        })
    },
    // 下载CSV文件
    download: (id) => {
        return api.get(`/datafiles/${id}/download`, {
            responseType: 'blob'
        })
    },
    // 删除数据文件
    delete: (id) => {
        return api.delete(`/datafiles/${id}`)
    }
}

// 模型相关API
export const modelAPI = {
    // 上传模型文件
    upload: (formData) => {
        return api.post('/models/', formData)
    },
    // 获取所有模型列表
    getList: () => {
        return api.get('/models/')
    },
    // 获取指定模型信息
    getById: (id) => {
        return api.get(`/models/${id}`)
    },
    // 下载模型文件
    download: (id) => {
        return api.get(`/models/${id}/download`, {
            responseType: 'blob'
        })
    },
    // 更新模型信息
    update: (id, data) => {
        return api.put(`/models/${id}`, data)
    },
    // 删除模型
    delete: (id) => {
        return api.delete(`/models/${id}`)
    }
}

// 客户端相关API
export const clientAPI = {
    // 创建客户端
    create: (data) => {
        return api.post('/clients/', data)
    },
    // 获取所有客户端列表
    getList: () => {
        return api.get('/clients/')
    },
    // 获取指定客户端信息
    getById: (id) => {
        return api.get(`/clients/${id}`)
    },
    // 删除客户端
    delete: (id) => {
        return api.delete(`/clients/${id}`)
    },
    // 绑定数据文件
    bindDataFile: (id, datafileId) => {
        return api.post(`/clients/${id}/bind-datafile`, {
            datafile_id: datafileId
        })
    },
    // 解绑数据文件
    unbindDataFile: (id) => {
        return api.post(`/clients/${id}/unbind-datafile`)
    },
    // 绑定模型
    bindModel: (id, modelId) => {
        return api.post(`/clients/${id}/bind-model`, {
            model_id: modelId
        })
    },
    // 解绑模型
    unbindModel: (id) => {
        return api.post(`/clients/${id}/unbind-model`)
    },
    // 训练客户端
    train: (id, data) => {
        return api.post(`/clients/${id}/train`, data)
    },
    // 评测接口
    evaluate: (data) => {
        return api.post('/clients/evaluate', data)
    }
}

// Agent相关API
export const agentAPI = {
    // 普通对话
    chat: (data) => {
        return api.post('/agent/chat', data)
    },
    // 流式对话（返回EventSource）
    chatStream: (message, sessionId) => {
        const baseURL = api.defaults.baseURL
        const url = new URL('/api/agent/chat-stream', window.location.origin)
        return fetch(url.toString(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                session_id: sessionId
            })
        })
    },
    // 获取所有会话列表
    getSessions: () => {
        return api.get('/agent/sessions')
    },
    // 获取指定会话历史
    getSession: (sessionId) => {
        return api.get(`/agent/sessions/${sessionId}`)
    },
    // 删除会话
    deleteSession: (sessionId) => {
        return api.delete(`/agent/sessions/${sessionId}`)
    },
    // Agent健康检查
    health: () => {
        return api.get('/agent/health')
    }
}

export default api

