import { useState, useEffect } from 'react'
import {
  Table,
  Button,
  Select,
  Space,
  message,
  Popconfirm,
  Tag,
  Card,
  Modal,
  Form,
  Input,
  Checkbox,
  Spin,
  Descriptions,
  Row,
  Col,
} from 'antd'
import {
  TeamOutlined,
  PlusOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  FundProjectionScreenOutlined,
} from '@ant-design/icons'
import { clientAPI, dataFileAPI, modelAPI } from '../services/api'

const { TextArea } = Input

const ClientsPage = () => {
  const [clients, setClients] = useState([])
  const [dataFiles, setDataFiles] = useState([])
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(false)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [trainModalVisible, setTrainModalVisible] = useState(false)
  const [evaluateModalVisible, setEvaluateModalVisible] = useState(false)
  const [currentClient, setCurrentClient] = useState(null)
  const [selectedClients, setSelectedClients] = useState([])
  const [trainingClients, setTrainingClients] = useState({}) // 记录正在训练的客户端
  const [createForm] = Form.useForm()
  const [trainForm] = Form.useForm()
  const [evaluateForm] = Form.useForm()

  // 加载所有数据
  const loadAllData = async () => {
    setLoading(true)
    try {
      await Promise.all([
        loadClients(),
        loadDataFiles(),
        loadModels(),
      ])
    } catch (error) {
      console.error('加载数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  // 加载客户端列表
  const loadClients = async () => {
    try {
      const response = await clientAPI.getList()
      console.log('客户端列表响应:', response)
      const clientData = response.data || response.clients || []
      setClients(clientData)
    } catch (error) {
      console.error('加载客户端列表失败:', error)
    }
  }

  // 加载数据文件列表
  const loadDataFiles = async () => {
    try {
      const response = await dataFileAPI.getList()
      const files = response.data || response.datafiles || []
      setDataFiles(files)
    } catch (error) {
      console.error('加载数据文件列表失败:', error)
    }
  }

  // 加载模型列表
  const loadModels = async () => {
    try {
      const response = await modelAPI.getList()
      const modelList = response.data || response.models || []
      setModels(modelList)
    } catch (error) {
      console.error('加载模型列表失败:', error)
    }
  }

  useEffect(() => {
    loadAllData()
  }, [])

  // 创建客户端
  const handleCreate = async (values) => {
    try {
      await clientAPI.create(values)
      message.success('创建成功')
      setCreateModalVisible(false)
      createForm.resetFields()
      loadClients()
    } catch (error) {
      console.error('创建失败:', error)
    }
  }

  // 删除客户端
  const handleDelete = async (id) => {
    try {
      await clientAPI.delete(id)
      message.success('删除成功')
      loadClients()
    } catch (error) {
      console.error('删除失败:', error)
    }
  }

  // 绑定数据文件
  const handleBindDataFile = async (clientId, datafileId) => {
    try {
      if (datafileId) {
        await clientAPI.bindDataFile(clientId, datafileId)
        message.success('数据文件绑定成功')
      } else {
        await clientAPI.unbindDataFile(clientId)
        message.success('数据文件解绑成功')
      }
      loadClients()
    } catch (error) {
      console.error('绑定数据文件失败:', error)
    }
  }

  // 绑定模型
  const handleBindModel = async (clientId, modelId) => {
    try {
      if (modelId) {
        await clientAPI.bindModel(clientId, modelId)
        message.success('模型绑定成功')
      } else {
        await clientAPI.unbindModel(clientId)
        message.success('模型解绑成功')
      }
      loadClients()
    } catch (error) {
      console.error('绑定模型失败:', error)
    }
  }

  // 训练客户端
  const handleTrain = async (client) => {
    setCurrentClient(client)
    trainForm.setFieldsValue({
      model_name: `${client.name}_trained_model`,
      model_type: 'lightgbm',
      description: `使用客户端 ${client.name} 的数据训练的模型`,
    })
    setTrainModalVisible(true)
  }

  // 提交训练
  const handleTrainSubmit = async (values) => {
    const clientId = currentClient.id
    
    // 设置训练状态
    setTrainingClients(prev => ({ ...prev, [clientId]: 'training' }))
    setTrainModalVisible(false)
    trainForm.resetFields()

    try {
      const response = await clientAPI.train(clientId, values)
      console.log('训练响应:', response)
      
      // 设置完成状态
      setTrainingClients(prev => ({ ...prev, [clientId]: 'completed' }))
      message.success('训练完成')
      
      // 1. 更新模型列表，添加新训练的模型
      if (response.data?.model) {
        const newModel = response.data.model
        setModels(prevModels => {
          // 检查模型是否已存在，如果存在则更新，否则添加
          const existingIndex = prevModels.findIndex(m => m.id === newModel.id)
          if (existingIndex >= 0) {
            // 更新已存在的模型
            const updatedModels = [...prevModels]
            updatedModels[existingIndex] = newModel
            return updatedModels
          } else {
            // 添加新模型到列表开头
            return [newModel, ...prevModels]
          }
        })
      }
      
      // 2. 更新客户端列表中的该客户端数据
      if (response.data?.client) {
        setClients(prevClients => 
          prevClients.map(client => 
            client.id === clientId ? response.data.client : client
          )
        )
      }
      
      // 3. 3秒后清除完成状态并完全刷新数据
      setTimeout(() => {
        setTrainingClients(prev => {
          const newState = { ...prev }
          delete newState[clientId]
          return newState
        })
        // 完全刷新所有数据确保同步
        loadClients()
        loadModels()
      }, 3000)
    } catch (error) {
      console.error('训练失败:', error)
      setTrainingClients(prev => {
        const newState = { ...prev }
        delete newState[clientId]
        return newState
      })
    }
  }

  // 评估
  const handleEvaluate = () => {
    if (selectedClients.length === 0) {
      message.warning('请至少选择一个客户端')
      return
    }
    setEvaluateModalVisible(true)
  }

  // 提交评估
  const handleEvaluateSubmit = async (values) => {
    try {
      // 去除首尾空格并解析JSON
      const trimmedData = values.house_data.trim()
      const houseData = JSON.parse(trimmedData)
      
      const response = await clientAPI.evaluate({
        client_ids: selectedClients,
        house_data: houseData,
      })
      
      console.log('评估响应:', response)
      
      // 显示评估结果
      Modal.success({
        title: '评估结果',
        width: 900,
        content: (
          <div>
            {/* 联邦学习汇总结果 */}
            {response.federated_results && (
              <Card 
                title={<span style={{ color: '#1890ff', fontWeight: 'bold' }}>📊 联邦学习加权平均预测</span>}
                style={{ marginBottom: 16 }}
                size="small"
              >
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Descriptions column={1} size="small" bordered>
                      <Descriptions.Item label="总价预测">
                        <Tag color="green" style={{ fontSize: 16, padding: '4px 12px' }}>
                          {response.federated_results.weighted_average_total_price?.toFixed(2)} 万元
                        </Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="单价预测">
                        <Tag color="blue" style={{ fontSize: 16, padding: '4px 12px' }}>
                          {response.federated_results.weighted_average_unit_price?.toFixed(2)} 万元/㎡
                        </Tag>
                      </Descriptions.Item>
                    </Descriptions>
                  </Col>
                  <Col span={12}>
                    <Descriptions column={1} size="small" bordered>
                      <Descriptions.Item label="参与客户端数">
                        {response.federated_results.participating_clients?.length}
                      </Descriptions.Item>
                      <Descriptions.Item label="总数据量">
                        {response.federated_results.total_data_count?.toLocaleString()}
                      </Descriptions.Item>
                    </Descriptions>
                  </Col>
                </Row>
              </Card>
            )}

            {/* 各客户端预测结果 */}
            <div style={{ marginTop: 16 }}>
              <div style={{ fontWeight: 'bold', marginBottom: 12, fontSize: 14 }}>
                🔍 各客户端模型预测详情
              </div>
              {response.results && response.results.map((result, index) => (
                <Card 
                  key={index} 
                  style={{ marginTop: index > 0 ? 12 : 0 }} 
                  size="small"
                  type={result.status === 'success' ? 'inner' : undefined}
                >
                  <Descriptions column={2} size="small" bordered>
                    <Descriptions.Item label="客户端" span={2}>
                      <Space>
                        <Tag color="purple">ID: {result.client_id}</Tag>
                        <span style={{ fontWeight: 'bold' }}>{result.client_name}</span>
                      </Space>
                    </Descriptions.Item>
                    
                    {result.status === 'success' && result.prediction ? (
                      <>
                        <Descriptions.Item label="总价预测">
                          <Tag color="green" style={{ fontSize: 14 }}>
                            {result.prediction.total_price?.toFixed(2)} 万元
                          </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="单价预测">
                          <Tag color="blue" style={{ fontSize: 14 }}>
                            {result.prediction.unit_price?.toFixed(2)} 万元/㎡
                          </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="模型类型">
                          <Tag color="orange">{result.prediction.model_type}</Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="训练数据量">
                          <Tag>{result.prediction.data_count?.toLocaleString()}</Tag>
                        </Descriptions.Item>
                        {response.federated_results?.participating_clients && (
                          <Descriptions.Item label="权重占比" span={2}>
                            {(() => {
                              const clientInfo = response.federated_results.participating_clients.find(
                                c => c.client_id === result.client_id
                              )
                              return clientInfo ? (
                                <Tag color="cyan">
                                  {(clientInfo.weight_ratio * 100).toFixed(2)}%
                                </Tag>
                              ) : '-'
                            })()}
                          </Descriptions.Item>
                        )}
                      </>
                    ) : (
                      <Descriptions.Item label="错误信息" span={2}>
                        <Tag color="red">{result.error || '预测失败'}</Tag>
                      </Descriptions.Item>
                    )}
                  </Descriptions>
                </Card>
              ))}
            </div>

            {/* 汇总统计 */}
            {response.summary && (
              <Card 
                title="汇总统计" 
                style={{ marginTop: 16 }} 
                size="small"
              >
                <Space size="large">
                  <span>总数: <Tag color="default">{response.summary.total}</Tag></span>
                  <span>成功: <Tag color="success">{response.summary.success}</Tag></span>
                  <span>失败: <Tag color="error">{response.summary.error}</Tag></span>
                  <span>跳过: <Tag color="warning">{response.summary.skipped}</Tag></span>
                </Space>
              </Card>
            )}
          </div>
        ),
      })
      
      setEvaluateModalVisible(false)
      evaluateForm.resetFields()
    } catch (error) {
      console.error('评估失败:', error)
      if (error instanceof SyntaxError) {
        message.error('JSON 格式错误，请检查输入的数据格式是否正确')
      } else {
        message.error('评估失败: ' + (error.message || '未知错误'))
      }
    }
  }

  // 获取训练按钮的状态
  const getTrainButtonContent = (clientId) => {
    const status = trainingClients[clientId]
    if (status === 'training') {
      return (
        <>
          <LoadingOutlined spin />
          <span style={{ marginLeft: 8 }}>训练中...</span>
        </>
      )
    }
    if (status === 'completed') {
      return (
        <>
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
          <span style={{ marginLeft: 8 }}>已完成</span>
        </>
      )
    }
    return (
      <>
        <PlayCircleOutlined />
        <span style={{ marginLeft: 8 }}>训练</span>
      </>
    )
  }

  const columns = [
    {
      title: '选择',
      key: 'select',
      width: 60,
      fixed: 'left',
      render: (_, record) => (
        <Checkbox
          checked={selectedClients.includes(record.id)}
          onChange={(e) => {
            if (e.target.checked) {
              setSelectedClients([...selectedClients, record.id])
            } else {
              setSelectedClients(selectedClients.filter(id => id !== record.id))
            }
          }}
          disabled={!record.model_id}
        />
      ),
    },
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '客户端名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (text) => (
        <Space>
          <TeamOutlined style={{ color: '#1890ff' }} />
          <span>{text}</span>
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text) => text || '-',
    },
    {
      title: '绑定数据文件',
      key: 'datafile',
      width: 250,
      render: (_, record) => (
        <Select
          style={{ width: '100%' }}
          placeholder="选择数据文件"
          value={record.datafile_id}
          onChange={(value) => handleBindDataFile(record.id, value)}
          allowClear
          onClear={() => handleBindDataFile(record.id, null)}
        >
          {dataFiles.map(file => (
            <Select.Option key={file.id} value={file.id}>
              {file.filename} ({(file.file_size / (1024 * 1024)).toFixed(2)} MB)
            </Select.Option>
          ))}
        </Select>
      ),
    },
    {
      title: '绑定模型',
      key: 'model',
      width: 250,
      render: (_, record) => (
        <Select
          style={{ width: '100%' }}
          placeholder="选择模型"
          value={record.model_id}
          onChange={(value) => handleBindModel(record.id, value)}
          allowClear
          onClear={() => handleBindModel(record.id, null)}
        >
          {models.map(model => (
            <Select.Option key={model.id} value={model.id}>
              {model.model_name} ({model.model_type})
            </Select.Option>
          ))}
        </Select>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_time',
      key: 'created_time',
      width: 180,
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            size="small"
            onClick={() => handleTrain(record)}
            disabled={!record.datafile_id || trainingClients[record.id] === 'training'}
            icon={trainingClients[record.id] ? null : <PlayCircleOutlined />}
          >
            {getTrainButtonContent(record.id)}
          </Button>
          <Popconfirm
            title="确认删除"
            description="确定要删除这个客户端吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger size="small" icon={<DeleteOutlined />}>
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
            <TeamOutlined />
            <span>客户端管理</span>
            {selectedClients.length > 0 && (
              <Tag color="blue">已选择 {selectedClients.length} 个客户端</Tag>
            )}
          </Space>
        }
        extra={
          <Space>
            <Button
              type="primary"
              icon={<FundProjectionScreenOutlined />}
              onClick={handleEvaluate}
              disabled={selectedClients.length === 0}
            >
              评估预测
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              创建客户端
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={clients}
          loading={loading}
          rowKey="id"
          scroll={{ x: 1400 }}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
          expandable={{
            expandedRowRender: (record) => (
              <div style={{ padding: '16px', background: '#fafafa' }}>
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Card title="绑定的数据文件" size="small">
                      {record.datafile_info ? (
                        <Descriptions column={1} size="small">
                          <Descriptions.Item label="文件名">
                            {record.datafile_info.filename}
                          </Descriptions.Item>
                          <Descriptions.Item label="文件大小">
                            {(record.datafile_info.file_size / (1024 * 1024)).toFixed(2)} MB
                          </Descriptions.Item>
                        </Descriptions>
                      ) : (
                        <Tag>未绑定数据文件</Tag>
                      )}
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card title="绑定的模型" size="small">
                      {record.model_info ? (
                        <Descriptions column={1} size="small">
                          <Descriptions.Item label="模型名称">
                            {record.model_info.model_name}
                          </Descriptions.Item>
                          <Descriptions.Item label="模型类型">
                            <Tag color="purple">{record.model_info.model_type}</Tag>
                          </Descriptions.Item>
                          <Descriptions.Item label="训练数据量">
                            {record.model_info.data_count?.toLocaleString()}
                          </Descriptions.Item>
                        </Descriptions>
                      ) : (
                        <Tag>未绑定模型</Tag>
                      )}
                    </Card>
                  </Col>
                </Row>
              </div>
            ),
          }}
        />
      </Card>

      {/* 创建客户端Modal */}
      <Modal
        title="创建客户端"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false)
          createForm.resetFields()
        }}
        footer={null}
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            name="name"
            label="客户端名称"
            rules={[{ required: true, message: '请输入客户端名称' }]}
          >
            <Input placeholder="请输入客户端名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="请输入客户端描述（可选）" />
          </Form.Item>
          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setCreateModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                创建
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 训练Modal */}
      <Modal
        title={`训练客户端: ${currentClient?.name}`}
        open={trainModalVisible}
        onCancel={() => {
          setTrainModalVisible(false)
          trainForm.resetFields()
        }}
        footer={null}
      >
        <Form form={trainForm} layout="vertical" onFinish={handleTrainSubmit}>
          <Form.Item
            name="model_name"
            label="模型名称"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="请输入模型名称" />
          </Form.Item>
          <Form.Item
            name="model_type"
            label="模型类型"
            rules={[{ required: true, message: '请输入模型类型' }]}
          >
            <Input placeholder="如：lightgbm, sklearn等" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="请输入模型描述（可选）" />
          </Form.Item>
          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setTrainModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                开始训练
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 评估Modal */}
      <Modal
        title="模型评估预测"
        open={evaluateModalVisible}
        onCancel={() => {
          setEvaluateModalVisible(false)
          evaluateForm.resetFields()
        }}
        footer={null}
        width={700}
      >
        <Form form={evaluateForm} layout="vertical" onFinish={handleEvaluateSubmit}>
          <Form.Item label="已选择的客户端">
            <Space wrap>
              {selectedClients.map(id => {
                const client = clients.find(c => c.id === id)
                return client ? (
                  <Tag key={id} color="blue">
                    {client.name} (ID: {id})
                  </Tag>
                ) : null
              })}
            </Space>
          </Form.Item>
          <Form.Item
            name="house_data"
            label="待预测数据 (JSON格式)"
            rules={[
              { required: true, message: '请输入待预测的数据' },
              {
                validator: (_, value) => {
                  if (!value) return Promise.resolve()
                  try {
                    // 去除首尾空格后再验证
                    const trimmedValue = value.trim()
                    JSON.parse(trimmedValue)
                    return Promise.resolve()
                  } catch (e) {
                    return Promise.reject(new Error('JSON格式错误: ' + e.message))
                  }
                },
              },
            ]}
            extra="请输入JSON格式的房屋数据（会自动去除首尾空格）"
          >
            <TextArea
              rows={12}
              placeholder={`示例：
{
  "城市": "大连",
  "区域": "高新园区",
  "街道": "凌水",
  "小区": "大有恬园公寓",
  "建筑面积": 35.72,
  "建筑类型": "塔楼",
  "房屋朝向": "南",
  "装修情况": "精装",
  "建筑结构": "钢混结构",
  "供暖方式": "集中供暖",
  "梯户比例": "四梯三十四户",
  "配备电梯": "有",
  "所在楼层": "高楼层 (共4层)",
  "成交时间": "2021.01.01 成交",
  "挂牌时间": "2020-04-20",
  "百度经纬": "121.518155,38.884228"
}`}
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setEvaluateModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                开始评估
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ClientsPage
