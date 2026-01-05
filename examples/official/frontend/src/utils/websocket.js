/**
 * WebSocket 客户端服务
 * 用于与后端建立实时通信，接收任务状态更新
 */

class WebSocketClient {
  constructor(clientId) {
    this.clientId = clientId
    this.ws = null
    this.messageHandlers = new Map()
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.isConnected = false
  }

  /**
   * 连接到 WebSocket 服务器
   * @param {string} url - WebSocket 服务器地址，如 'ws://localhost:8000'
   */
  connect(url) {
    try {
      this.ws = new WebSocket(`${url}/ws/tasks/${this.clientId}`)
      
      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.isConnected = true
        this.reconnectAttempts = 0
      }
      
      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.isConnected = false
      }
      
      this.ws.onclose = () => {
        console.log('WebSocket closed')
        this.isConnected = false
        this.attemptReconnect()
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      this.isConnected = false
    }
  }

  /**
   * 尝试重连
   */
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      setTimeout(() => {
        console.log(`Reconnecting... attempt ${this.reconnectAttempts}`)
        this.connect('ws://localhost:8000')
      }, this.reconnectDelay * this.reconnectAttempts)
    } else {
      console.warn('Max reconnection attempts reached')
    }
  }

  /**
   * 注册消息处理器
   * @param {string} eventType - 事件类型，如 'task_update'
   * @param {Function} handler - 消息处理函数
   */
  on(eventType, handler) {
    if (!this.messageHandlers.has(eventType)) {
      this.messageHandlers.set(eventType, [])
    }
    this.messageHandlers.get(eventType).push(handler)
  }

  /**
   * 处理接收到的消息
   * @param {Object} message - 消息对象
   */
  handleMessage(message) {
    const handlers = this.messageHandlers.get(message.type) || []
    handlers.forEach(handler => {
      try {
        handler(message)
      } catch (error) {
        console.error('Error in message handler:', error)
      }
    })
  }

  /**
   * 移除消息处理器
   * @param {string} eventType - 事件类型
   * @param {Function} handler - 要移除的处理函数
   */
  off(eventType, handler) {
    if (this.messageHandlers.has(eventType)) {
      const handlers = this.messageHandlers.get(eventType)
      const index = handlers.indexOf(handler)
      if (index > -1) {
        handlers.splice(index, 1)
      }
    }
  }

  /**
   * 断开 WebSocket 连接
   */
  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
      this.isConnected = false
      console.log('WebSocket disconnected by user')
    }
  }

  /**
   * 发送消息到服务器
   * @param {Object} data - 要发送的数据对象
   */
  send(data) {
    if (this.ws && this.isConnected) {
      try {
        this.ws.send(JSON.stringify(data))
      } catch (error) {
        console.error('Failed to send message:', error)
      }
    } else {
      console.warn('WebSocket not connected')
    }
  }

  /**
   * 获取连接状态
   * @returns {boolean} 是否已连接
   */
  isReady() {
    return this.isConnected
  }
}

// 创建全局 WebSocket 客户端实例
// 使用时间戳和随机字符串确保唯一性
const wsClient = new WebSocketClient(
  `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
)

export default wsClient
