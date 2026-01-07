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
  Drawer,
} from 'antd'
import {
  UploadOutlined,
  DeleteOutlined,
  EyeOutlined,
  DownloadOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import { dataFileAPI } from '../services/api'

const DataFilesPage = () => {
  const [dataFiles, setDataFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [uploadModalVisible, setUploadModalVisible] = useState(false)
  const [previewDrawerVisible, setPreviewDrawerVisible] = useState(false)
  const [previewData, setPreviewData] = useState(null)
  const [form] = Form.useForm()

  // 加载数据文件列表
  const loadDataFiles = async () => {
    setLoading(true)
    try {
      const response = await dataFileAPI.getList()
      console.log('数据文件列表响应:', response)
      // 处理不同的响应格式
      if (Array.isArray(response)) {
        setDataFiles(response)
      } else if (response.data) {
        setDataFiles(response.data)
      } else if (response.datafiles) {
        setDataFiles(response.datafiles)
      } else {
        setDataFiles([])
      }
    } catch (error) {
      console.error('加载数据文件列表失败:', error)
      message.error('加载数据文件列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDataFiles()
  }, [])

  // 处理文件上传
  const handleUpload = async (values) => {
    console.log('上传表单值:', values)
    const { file, description } = values
    
    // 检查文件是否存在
    if (!file || !file[0]) {
      message.error('请选择文件')
      return
    }

    const formData = new FormData()
    const fileObj = file[0].originFileObj
    console.log('上传的文件:', fileObj)
    formData.append('file', fileObj)
    if (description) {
      formData.append('description', description)
    }

    try {
      const result = await dataFileAPI.upload(formData)
      console.log('上传成功响应:', result)
      message.success('文件上传成功')
      setUploadModalVisible(false)
      form.resetFields()
      loadDataFiles()
    } catch (error) {
      console.error('文件上传失败:', error)
      console.error('错误详情:', error.response)
    }
  }

  // 删除数据文件
  const handleDelete = async (id) => {
    try {
      await dataFileAPI.delete(id)
      message.success('删除成功')
      loadDataFiles()
    } catch (error) {
      console.error('删除失败:', error)
    }
  }

  // 预览文件
  const handlePreview = async (id) => {
    try {
      const data = await dataFileAPI.preview(id, 10)
      setPreviewData(data)
      setPreviewDrawerVisible(true)
    } catch (error) {
      console.error('预览失败:', error)
    }
  }

  // 下载文件
  const handleDownload = async (id, filename) => {
    try {
      const blob = await dataFileAPI.download(id)
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
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      ellipsis: true,
      render: (text) => (
        <Space>
          <FileTextOutlined style={{ color: '#1890ff' }} />
          <span>{text}</span>
        </Space>
      ),
    },
    {
      title: '文件大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 120,
      render: (size) => {
        if (size < 1024) return `${size} B`
        if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`
        return `${(size / (1024 * 1024)).toFixed(2)} MB`
      },
    },
    {
      title: '行数',
      dataIndex: 'row_count',
      key: 'row_count',
      width: 100,
      render: (count) => <Tag color="blue">{count?.toLocaleString() || '-'}</Tag>,
    },
    {
      title: '列数',
      dataIndex: 'column_count',
      key: 'column_count',
      width: 100,
      render: (count) => <Tag color="green">{count || '-'}</Tag>,
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
      width: 220,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {/* <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record.id)}
          >
            预览
          </Button> */}
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => handleDownload(record.id, record.filename)}
          >
            下载
          </Button>
          <Popconfirm
            title="确认删除"
            description="确定要删除这个数据文件吗？"
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
            <FileTextOutlined />
            <span>数据文件管理</span>
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => setUploadModalVisible(true)}
          >
            上传文件
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={dataFiles}
          loading={loading}
          rowKey="id"
          scroll={{ x: 1200 }}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      {/* 上传文件Modal */}
      <Modal
        title="上传CSV文件"
        open={uploadModalVisible}
        onCancel={() => {
          setUploadModalVisible(false)
          form.resetFields()
        }}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleUpload}>
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
            <Upload
              maxCount={1}
              beforeUpload={() => false}
              accept=".csv"
            >
              <Button icon={<UploadOutlined />}>选择CSV文件</Button>
            </Upload>
          </Form.Item>
          <Form.Item name="description" label="文件描述">
            <Input.TextArea rows={3} placeholder="请输入文件描述（可选）" />
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

      {/* 预览Drawer */}
      <Drawer
        title="文件预览"
        placement="right"
        width={800}
        onClose={() => setPreviewDrawerVisible(false)}
        open={previewDrawerVisible}
      >
        {previewData && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <strong>列名：</strong>
                  {previewData.columns?.join(', ')}
                </div>
                <div>
                  <strong>数据预览（前 {previewData.preview?.length || 0} 行）：</strong>
                </div>
              </Space>
            </div>
            <Table
              columns={previewData.columns?.map((col) => ({
                title: col,
                dataIndex: col,
                key: col,
                ellipsis: true,
              }))}
              dataSource={previewData.preview?.map((row, index) => ({
                key: index,
                ...row,
              }))}
              pagination={false}
              scroll={{ x: 'max-content' }}
              size="small"
            />
          </div>
        )}
      </Drawer>
    </div>
  )
}

export default DataFilesPage

