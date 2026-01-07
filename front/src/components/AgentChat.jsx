import { useState, useRef, useEffect } from 'react'
import { Button, Input, Card, Avatar, Space, Radio, Spin, message as antMessage, Badge, Tooltip } from 'antd'
import { SendOutlined, CloseOutlined, MessageOutlined, RobotOutlined, UserOutlined, DeleteOutlined } from '@ant-design/icons'
import { agentAPI } from '../services/api'
import './AgentChat.css'

const { TextArea } = Input

const AgentChat = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [mode, setMode] = useState('stream') // 'stream' 或 'normal'
  const [unreadCount, setUnreadCount] = useState(0)
  
  const messagesEndRef = useRef(null)
  const chatContainerRef = useRef(null)

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 窗口打开时清除未读数
  useEffect(() => {
    if (isOpen) {
      setUnreadCount(0)
    }
  }, [isOpen])

  // 处理流式响应
  const handleStreamResponse = async (message) => {
    setIsLoading(true)
    
    // 添加用户消息
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])

    // 添加一个空的助手消息用于流式更新
    const assistantMessageIndex = messages.length + 1
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true
    }])

    try {
      const response = await agentAPI.chatStream(message, sessionId)
      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      let assistantContent = ''
      let newSessionId = sessionId
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // 将新数据添加到缓冲区
        buffer += decoder.decode(value, { stream: true })
        
        // 按行分割
        const lines = buffer.split('\n')
        
        // 保留最后一行（可能不完整）
        buffer = lines.pop() || ''

        for (const line of lines) {
          let trimmedLine = line.trim()
          if (!trimmedLine) continue

          // 处理SSE格式的 "data: " 前缀
          if (trimmedLine.startsWith('data: ')) {
            trimmedLine = trimmedLine.slice(6).trim()
          }

          // 跳过空数据
          if (!trimmedLine) continue

          try {
            const parsed = JSON.parse(trimmedLine)
            
            // 处理session_id
            if (parsed.session_id && !newSessionId) {
              newSessionId = parsed.session_id
              setSessionId(newSessionId)
            }

            // 处理不同类型的消息
            if (parsed.type === 'content' && parsed.content) {
              assistantContent += parsed.content
              
              // 实时更新消息
              setMessages(prev => {
                const newMessages = [...prev]
                newMessages[assistantMessageIndex] = {
                  role: 'assistant',
                  content: assistantContent,
                  timestamp: new Date().toISOString(),
                  isStreaming: true
                }
                return newMessages
              })
            } else if (parsed.type === 'tool_call' || parsed.type === 'tool_executing') {
              // 显示工具调用
              const toolName = parsed.tool_name || '未知工具'
              assistantContent += `\n\n🔧 正在调用工具: ${toolName}`
              if (parsed.tool_args) {
                assistantContent += `\n参数: ${JSON.stringify(parsed.tool_args, null, 2)}`
              }
              
              // 更新UI显示工具调用
              setMessages(prev => {
                const newMessages = [...prev]
                newMessages[assistantMessageIndex] = {
                  role: 'assistant',
                  content: assistantContent,
                  timestamp: new Date().toISOString(),
                  isStreaming: true
                }
                return newMessages
              })
            } else if (parsed.type === 'tool_result') {
              // 显示工具结果
              assistantContent += `\n📊 工具执行完成\n\n`
              
              setMessages(prev => {
                const newMessages = [...prev]
                newMessages[assistantMessageIndex] = {
                  role: 'assistant',
                  content: assistantContent,
                  timestamp: new Date().toISOString(),
                  isStreaming: true
                }
                return newMessages
              })
            } else if (parsed.type === 'done') {
              // 流式输出完成
              console.log('流式输出完成')
            } else if (parsed.type === 'error') {
              // 错误处理
              antMessage.error(parsed.message || '发生错误')
            }

          } catch (e) {
            console.warn('解析JSON失败:', trimmedLine, e)
          }
        }
      }

      // 完成流式输出
      setMessages(prev => {
        const newMessages = [...prev]
        newMessages[assistantMessageIndex] = {
          role: 'assistant',
          content: assistantContent || '(无回复)',
          timestamp: new Date().toISOString(),
          isStreaming: false
        }
        return newMessages
      })

      if (!isOpen) {
        setUnreadCount(prev => prev + 1)
      }

    } catch (error) {
      console.error('流式对话错误:', error)
      antMessage.error('对话失败，请重试')
      // 移除失败的消息
      setMessages(prev => prev.slice(0, -1))
    } finally {
      setIsLoading(false)
    }
  }

  // 处理普通响应
  const handleNormalResponse = async (message) => {
    setIsLoading(true)

    // 添加用户消息
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])

    try {
      const response = await agentAPI.chat({
        message,
        session_id: sessionId
      })

      if (response.session_id && !sessionId) {
        setSessionId(response.session_id)
      }

      // 添加助手消息
      const assistantMessage = {
        role: 'assistant',
        content: response.message || response.response || '抱歉，我没有理解',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, assistantMessage])

      if (!isOpen) {
        setUnreadCount(prev => prev + 1)
      }

    } catch (error) {
      console.error('对话错误:', error)
      antMessage.error('对话失败，请重试')
      // 移除失败的用户消息
      setMessages(prev => prev.slice(0, -1))
    } finally {
      setIsLoading(false)
    }
  }

  // 发送消息
  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return

    const message = inputValue.trim()
    setInputValue('')

    if (mode === 'stream') {
      await handleStreamResponse(message)
    } else {
      await handleNormalResponse(message)
    }
  }

  // 清空对话
  const handleClear = () => {
    setMessages([])
    setSessionId(null)
    antMessage.success('对话已清空')
  }

  // 处理Enter键发送
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 渲染消息
  const renderMessage = (msg, index) => {
    const isUser = msg.role === 'user'
    
    return (
      <div 
        key={index} 
        className={`message-wrapper ${isUser ? 'user-message' : 'assistant-message'}`}
      >
        <Space align="start" size={8}>
          {!isUser && (
            <Avatar 
              icon={<RobotOutlined />} 
              style={{ backgroundColor: '#1890ff', flexShrink: 0 }}
            />
          )}
          <div className={`message-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
            <div className="message-content">
              {msg.content || (msg.isStreaming ? '思考中...' : '')}
              {msg.isStreaming && <span className="cursor-blink">▋</span>}
            </div>
          </div>
          {isUser && (
            <Avatar 
              icon={<UserOutlined />} 
              style={{ backgroundColor: '#52c41a', flexShrink: 0 }}
            />
          )}
        </Space>
      </div>
    )
  }

  return (
    <>
      {/* 悬浮按钮 */}
      {!isOpen && (
        <Badge count={unreadCount} offset={[-5, 5]}>
          <Tooltip title="AI助手" placement="left">
            <Button
              type="primary"
              shape="circle"
              size="large"
              icon={<MessageOutlined />}
              onClick={() => setIsOpen(true)}
              className="floating-chat-button"
            />
          </Tooltip>
        </Badge>
      )}

      {/* 聊天窗口 */}
      {isOpen && (
        <Card
          className="chat-window"
          title={
            <Space>
              <RobotOutlined style={{ fontSize: '18px' }} />
              <span>AI助手</span>
            </Space>
          }
          extra={
            <Space>
              <Tooltip title="清空对话">
                <Button
                  type="text"
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={handleClear}
                  disabled={messages.length === 0}
                />
              </Tooltip>
              <Button
                type="text"
                size="small"
                icon={<CloseOutlined />}
                onClick={() => setIsOpen(false)}
              />
            </Space>
          }
        >
          {/* 消息列表 */}
          <div className="messages-container" ref={chatContainerRef}>
            {messages.length === 0 ? (
              <div className="empty-chat">
                <RobotOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
                <p>你好！我是AI助手，有什么可以帮你的吗？</p>
              </div>
            ) : (
              messages.map((msg, index) => renderMessage(msg, index))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div className="chat-input-area">
            {/* 模式切换 */}
            <div className="mode-selector">
              <Radio.Group 
                value={mode} 
                onChange={(e) => setMode(e.target.value)}
                size="small"
                disabled={isLoading}
              >
                <Radio.Button value="stream">流式模式</Radio.Button>
                <Radio.Button value="normal">普通模式</Radio.Button>
              </Radio.Group>
            </div>

            {/* 输入框 */}
            <Space.Compact style={{ width: '100%' }}>
              <TextArea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入消息... (Shift+Enter换行)"
                autoSize={{ minRows: 1, maxRows: 4 }}
                disabled={isLoading}
              />
              <Button
                type="primary"
                icon={isLoading ? <Spin size="small" /> : <SendOutlined />}
                onClick={handleSend}
                disabled={isLoading || !inputValue.trim()}
                style={{ height: 'auto' }}
              />
            </Space.Compact>
          </div>
        </Card>
      )}
    </>
  )
}

export default AgentChat

