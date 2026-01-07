import { useState, useEffect } from 'react'
import {
  Table,
  Button,
  Upload,
  Modal,
  Form,
  Input,
  Space,
  message,
  Popconfirm,
  Tag,
  Card,
  InputNumber,
  Descriptions,
} from 'antd'
import {
  UploadOutlined,
  DeleteOutlined,
  EyeOutlined,
  DownloadOutlined,
  RobotOutlined,
  EditOutlined,
} from '@ant-design/icons'
import { modelAPI } from '../services/api'

const ModelsPage = () => {
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(false)
  const [uploadModalVisible, setUploadModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [currentModel, setCurrentModel] = useState(null)
  const [uploadForm] = Form.useForm()
  const [editForm] = Form.useForm()

  // 加载模型列表
  const loadModels = async () => {
    setLoading(true)
    try {
      const response = await modelAPI.getList()
      console.log('模型列表响应:', response)
      // 处理不同的响应格式
      if (Array.isArray(response)) {
        setModels(response)
      } else if (response.data) {
        setModels(response.data)
      } else if (response.models) {
        setModels(response.models)
      } else {
        setModels([])
      }
    } catch (error) {
      console.error('加载模型列表失败:', error)
      message.error('加载模型列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadModels()
  }, [])

  // 处理文件上传
  const handleUpload = async (values) => {
    console.log('上传表单值:', values)
    const { file, model_name, data_count, description, model_type } = values
    
    // 检查文件是否存在
    if (!file || !file[0]) {
      message.error('请选择文件')
      return
    }

    const formData = new FormData()
    const fileObj = file[0].originFileObj
    console.log('上传的文件:', fileObj)
    formData.append('file', fileObj)
    formData.append('model_name', model_name)
    formData.append('data_count', data_count.toString())
    if (description) {
      formData.append('description', description)
    }
    if (model_type) {
      formData.append('model_type', model_type)
    }

    try {
      const result = await modelAPI.upload(formData)
      console.log('上传成功响应:', result)
      message.success('模型上传成功')
      setUploadModalVisible(false)
      uploadForm.resetFields()
      loadModels()
    } catch (error) {
      console.error('模型上传失败:', error)
      console.error('错误详情:', error.response)
    }
  }

  // 删除模型
  const handleDelete = async (id) => {
    try {
      await modelAPI.delete(id)
      message.success('删除成功')
      loadModels()
    } catch (error) {
      console.error('删除失败:', error)
    }
  }

  // 查看详情
  const handleViewDetail = async (record) => {
    try {
      const data = await modelAPI.getById(record.id)
      setCurrentModel(data)
      setDetailModalVisible(true)
    } catch (error) {
      console.error('获取详情失败:', error)
    }
  }

  // 编辑模型
  const handleEdit = (record) => {
    setCurrentModel(record)
    editForm.setFieldsValue({
      model_name: record.model_name,
      data_count: record.data_count,
      description: record.description,
      model_type: record.model_type,
    })
    setEditModalVisible(true)
  }

  // 更新模型信息
  const handleUpdate = async (values) => {
    try {
      await modelAPI.update(currentModel.id, values)
      message.success('更新成功')
      setEditModalVisible(false)
      editForm.resetFields()
      loadModels()
    } catch (error) {
      console.error('更新失败:', error)
    }
  }

  // 下载模型
  const handleDownload = async (id, filename) => {
    try {
      const blob = await modelAPI.download(id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      message.success('下载成功')
    } catch (error) {
      console.error('下载失败:', error)
    }
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '模型名称',
      dataIndex: 'model_name',
      key: 'model_name',
      ellipsis: true,
      render: (text) => (
        <Space>
          <RobotOutlined style={{ color: '#52c41a' }} />
          <span>{text}</span>
        </Space>
      ),
    },
    // 注意：后端返回的数据中没有 filename 字段，暂时隐藏此列
    // {
    //   title: '文件名',
    //   dataIndex: 'filename',
    //   key: 'filename',
    //   ellipsis: true,
    // },
    {
      title: '模型类型',
      dataIndex: 'model_type',
      key: 'model_type',
      width: 120,
      render: (text) => <Tag color="purple">{text || '未指定'}</Tag>,
    },
    {
      title: '训练数据量',
      dataIndex: 'data_count',
      key: 'data_count',
      width: 120,
      render: (count) => <Tag color="blue">{count?.toLocaleString() || '-'}</Tag>,
    },
    {
      title: '模型大小',
      dataIndex: 'model_size',
      key: 'model_size',
      width: 120,
      render: (size) => {
        if (!size) return '-'
        if (size < 1024) return `${size} B`
        if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`
        return `${(size / (1024 * 1024)).toFixed(2)} MB`
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text) => text || '-',
    },
    {
      title: '上传时间',
      dataIndex: 'upload_time',
      key: 'upload_time',
      width: 180,
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {/* <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button> */}
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => handleDownload(record.id, record.model_name + '.pkl')}
          >
            下载
          </Button>
          <Popconfirm
            title="确认删除"
            description="确定要删除这个模型吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card
        title={
          <Space>
            <RobotOutlined />
            <span>模型管理</span>
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => setUploadModalVisible(true)}
          >
            上传模型
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={models}
          loading={loading}
          rowKey="id"
          scroll={{ x: 1400 }}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      {/* 上传模型Modal */}
      <Modal
        title="上传模型文件"
        open={uploadModalVisible}
        onCancel={() => {
          setUploadModalVisible(false)
          uploadForm.resetFields()
        }}
        footer={null}
        width={600}
      >
        <Form form={uploadForm} layout="vertical" onFinish={handleUpload}>
          <Form.Item
            name="file"
            label="选择文件"
            rules={[{ required: true, message: '请选择要上传的文件' }]}
            valuePropName="fileList"
            getValueFromEvent={(e) => {
              if (Array.isArray(e)) {
                return e
              }
              return e?.fileList
            }}
          >
            <Upload maxCount={1} beforeUpload={() => false}>
              <Button icon={<UploadOutlined />}>选择模型文件</Button>
            </Upload>
          </Form.Item>
          <Form.Item
            name="model_name"
            label="模型名称"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="请输入模型名称" />
          </Form.Item>
          <Form.Item
            name="data_count"
            label="训练数据量"
            rules={[{ required: true, message: '请输入训练数据量' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={1}
              placeholder="请输入训练数据量"
            />
          </Form.Item>
          <Form.Item name="model_type" label="模型类型">
            <Input placeholder="如：sklearn、pytorch、lightgbm等（可选）" />
          </Form.Item>
          <Form.Item name="description" label="模型描述">
            <Input.TextArea rows={3} placeholder="请输入模型描述（可选）" />
          </Form.Item>
          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setUploadModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                上传
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑模型Modal */}
      <Modal
        title="编辑模型信息"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false)
          editForm.resetFields()
        }}
        footer={null}
        width={600}
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdate}>
          <Form.Item
            name="model_name"
            label="模型名称"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="请输入模型名称" />
          </Form.Item>
          <Form.Item
            name="data_count"
            label="训练数据量"
            rules={[{ required: true, message: '请输入训练数据量' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={1}
              placeholder="请输入训练数据量"
            />
          </Form.Item>
          <Form.Item name="model_type" label="模型类型">
            <Input placeholder="如：sklearn、pytorch、lightgbm等" />
          </Form.Item>
          <Form.Item name="description" label="模型描述">
            <Input.TextArea rows={3} placeholder="请输入模型描述" />
          </Form.Item>
          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setEditModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                更新
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情Modal */}
      <Modal
        title="模型详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={700}
      >
        {currentModel && (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="模型ID">{currentModel.id}</Descriptions.Item>
            <Descriptions.Item label="模型名称">
              {currentModel.model_name}
            </Descriptions.Item>
            <Descriptions.Item label="模型类型">
              <Tag color="purple">{currentModel.model_type || '未指定'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="训练数据量">
              {currentModel.data_count?.toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="模型大小">
              {currentModel.model_size
                ? `${(currentModel.model_size / (1024 * 1024)).toFixed(2)} MB`
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="上传时间">
              {currentModel.upload_time}
            </Descriptions.Item>
            <Descriptions.Item label="描述">
              {currentModel.description || '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

export default ModelsPage

