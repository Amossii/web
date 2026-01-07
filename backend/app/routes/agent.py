"""
LLM Agent 路由
提供智能对话和房价预测功能
"""
from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.agent.llm_agent import (
    QwenClient, 
    PREDICT_HOUSE_PRICE_TOOL_SPEC, 
    TIME_TOOL_SPEC,
    call_tool
)
import json
import uuid
from datetime import datetime

agent_bp = Blueprint('agent', __name__, url_prefix='/api/agent')

# 存储会话信息（生产环境应使用Redis等持久化存储）
sessions = {}


@agent_bp.route('/chat', methods=['POST'])
def chat():
    """
    与Agent对话接口
    
    请求体:
    {
        "message": "用户消息",
        "session_id": "会话ID（可选，不提供则创建新会话）",
        "stream": true/false（是否流式输出，默认false）
    }
    
    返回:
    {
        "session_id": "会话ID",
        "response": "助手回复",
        "tool_calls": [...],  # 如果调用了工具
        "timestamp": "时间戳"
    }
    """
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        stream = data.get('stream', False)
        
        if not user_message:
            return jsonify({
                'error': '消息不能为空',
                'status': 'failed'
            }), 400
        
        # 获取或创建会话
        if not session_id or session_id not in sessions:
            session_id = str(uuid.uuid4())
            sessions[session_id] = {
                'messages': [
                    {
                        "role": "system",
                        "content": (
                            "你是一个智能房地产估价助手，可以与用户对话并帮助预测房价。\n"
                            "当用户询问与当前时间、现在几点等问题相关时，请使用工具 get_current_time。\n"
                            "当用户想要预测房价时，请使用工具 predict_house_price。用户需要提供房屋信息和模型ID列表。\n"
                            "房屋信息应包含：小区、成交时间、建筑面积、房屋户型、所在楼层、建成年代、装修情况、房屋朝向、区域、街道、城市等字段。\n"
                            "如果用户没有提供完整的房屋信息或模型ID，请礼貌地询问缺失的信息。\n"
                            "预测结果会包含加权平均的单价和总价，以及各个模型的详细预测信息。\n"
                            "请用友好、专业的语气回答用户问题。"
                        ),
                    }
                ],
                'created_at': datetime.now().isoformat()
            }
        
        session = sessions[session_id]
        
        # 添加用户消息
        session['messages'].append({
            "role": "user",
            "content": user_message
        })
        
        # 初始化客户端
        client = QwenClient()
        tools = [TIME_TOOL_SPEC, PREDICT_HOUSE_PRICE_TOOL_SPEC]
        
        # 调用大模型
        resp = client.chat(session['messages'], tools=tools, tool_choice="auto")
        msg = resp["choices"][0]["message"]
        
        # 情况1：模型直接回答（没有调用工具）
        if "tool_calls" not in msg:
            answer = msg.get("content", "")
            session['messages'].append({
                "role": "assistant",
                "content": answer
            })
            
            return jsonify({
                'session_id': session_id,
                'response': answer,
                'tool_calls': None,
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            })
        
        # 情况2：模型要调用工具
        tool_calls = msg["tool_calls"]
        session['messages'].append({
            "role": "assistant",
            "content": msg.get("content", ""),
            "tool_calls": tool_calls,
        })
        
        # 执行工具调用
        tool_results = []
        tool_results_messages = []
        
        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            arguments = tool_call["function"].get("arguments", "{}")
            tool_call_id = tool_call.get("id", "")
            
            # 调用工具
            result_str = call_tool(func_name, arguments)
            
            tool_results.append({
                'tool_name': func_name,
                'arguments': arguments,
                'result': result_str
            })
            
            # 添加工具执行结果
            tool_results_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": func_name,
                "content": result_str,
            })
        
        session['messages'].extend(tool_results_messages)
        
        # 第二次调用：获取最终回复
        resp2 = client.chat(session['messages'])
        final_msg = resp2["choices"][0]["message"]
        final_answer = final_msg.get("content", "")
        
        session['messages'].append({
            "role": "assistant",
            "content": final_answer
        })
        
        return jsonify({
            'session_id': session_id,
            'response': final_answer,
            'tool_calls': tool_results,
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'failed'
        }), 500


@agent_bp.route('/chat-stream', methods=['POST'])
def chat_stream():
    """
    流式对话接口（不支持工具调用时的流式）
    
    请求体:
    {
        "message": "用户消息",
        "session_id": "会话ID（可选）"
    }
    
    返回: Server-Sent Events (SSE) 流
    """
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not user_message:
            return jsonify({
                'error': '消息不能为空',
                'status': 'failed'
            }), 400
        
        # 获取或创建会话
        if not session_id or session_id not in sessions:
            session_id = str(uuid.uuid4())
            sessions[session_id] = {
                'messages': [
                    {
                        "role": "system",
                        "content": (
                            "你是一个智能房地产估价助手，可以与用户对话并帮助预测房价。\n"
                            "当用户询问与当前时间、现在几点等问题相关时，请使用工具 get_current_time。\n"
                            "当用户想要预测房价时，请使用工具 predict_house_price。用户需要提供房屋信息和模型ID列表。\n"
                            "房屋信息应包含用户提供的所有房屋信息，将其作为dict传入函数。\n"
                            "预测结果会包含加权平均的单价和总价，以及各个模型的详细预测信息。\n"
                            "请用友好、专业的语气回答用户问题。"
                        ),
                    }
                ],
                'created_at': datetime.now().isoformat()
            }
        
        def generate():
            """生成流式响应"""
            try:
                session = sessions[session_id]
                
                # 添加用户消息
                session['messages'].append({
                    "role": "user",
                    "content": user_message
                })
                
                # 初始化客户端
                client = QwenClient()
                tools = [TIME_TOOL_SPEC, PREDICT_HOUSE_PRICE_TOOL_SPEC]
                
                # 发送session_id
                yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
                
                # 调用大模型
                resp = client.chat(session['messages'], tools=tools, tool_choice="auto")
                msg = resp["choices"][0]["message"]
                
                # 检查是否需要调用工具
                if "tool_calls" in msg:
                    # 有工具调用，无法流式输出
                    yield f"data: {json.dumps({'type': 'tool_call', 'message': '正在调用工具...'})}\n\n"
                    
                    tool_calls = msg["tool_calls"]
                    session['messages'].append({
                        "role": "assistant",
                        "content": msg.get("content", ""),
                        "tool_calls": tool_calls,
                    })
                    
                    # 执行工具调用
                    tool_results_messages = []
                    for tool_call in tool_calls:
                        func_name = tool_call["function"]["name"]
                        arguments = tool_call["function"].get("arguments", "{}")
                        tool_call_id = tool_call.get("id", "")
                        
                        yield f"data: {json.dumps({'type': 'tool_executing', 'tool_name': func_name})}\n\n"
                        
                        # 调用工具
                        result_str = call_tool(func_name, arguments)
                        print("arguments")
                        print(arguments)
                        
                        tool_results_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": func_name,
                            "content": result_str,
                        })
                    
                    session['messages'].extend(tool_results_messages)
                    
                    # 获取最终回复
                    resp2 = client.chat(session['messages'])
                    final_msg = resp2["choices"][0]["message"]
                    final_answer = final_msg.get("content", "")
                    
                    session['messages'].append({
                        "role": "assistant",
                        "content": final_answer
                    })
                    
                    # 分块发送最终回复（模拟流式）
                    chunk_size = 20
                    for i in range(0, len(final_answer), chunk_size):
                        chunk = final_answer[i:i+chunk_size]
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                    
                else:
                    # 没有工具调用，直接输出
                    answer = msg.get("content", "")
                    session['messages'].append({
                        "role": "assistant",
                        "content": answer
                    })
                    
                    # 分块发送（模拟流式）
                    chunk_size = 20
                    for i in range(0, len(answer), chunk_size):
                        chunk = answer[i:i+chunk_size]
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                
                # 发送结束信号
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'failed'
        }), 500


@agent_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """
    获取会话历史
    
    返回:
    {
        "session_id": "会话ID",
        "messages": [...],
        "created_at": "创建时间"
    }
    """
    if session_id not in sessions:
        return jsonify({
            'error': '会话不存在',
            'status': 'failed'
        }), 404
    
    session = sessions[session_id]
    # 过滤掉系统消息
    user_messages = [
        msg for msg in session['messages'] 
        if msg['role'] in ['user', 'assistant']
    ]
    
    return jsonify({
        'session_id': session_id,
        'messages': user_messages,
        'created_at': session.get('created_at'),
        'message_count': len(user_messages),
        'status': 'success'
    })


@agent_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """
    删除会话
    
    返回:
    {
        "message": "会话已删除",
        "status": "success"
    }
    """
    if session_id not in sessions:
        return jsonify({
            'error': '会话不存在',
            'status': 'failed'
        }), 404
    
    del sessions[session_id]
    
    return jsonify({
        'message': '会话已删除',
        'session_id': session_id,
        'status': 'success'
    })


@agent_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """
    获取所有会话列表
    
    返回:
    {
        "sessions": [
            {
                "session_id": "...",
                "created_at": "...",
                "message_count": 10
            }
        ],
        "total": 5
    }
    """
    session_list = []
    for sid, session in sessions.items():
        # 过滤掉系统消息
        user_messages = [
            msg for msg in session['messages'] 
            if msg['role'] in ['user', 'assistant']
        ]
        session_list.append({
            'session_id': sid,
            'created_at': session.get('created_at'),
            'message_count': len(user_messages)
        })
    
    return jsonify({
        'sessions': session_list,
        'total': len(session_list),
        'status': 'success'
    })


@agent_bp.route('/predict', methods=['POST'])
def predict():
    """
    直接调用房价预测工具（不经过对话）
    
    请求体:
    {
        "house_info": {
            "小区": "...",
            "建筑面积": "100㎡",
            ...
        },
        "model_ids": [1, 2, 3]
    }
    
    返回:
    {
        "result": {...},  # 预测结果
        "status": "success"
    }
    """
    try:
        data = request.json
        house_info = data.get('house_info')
        model_ids = data.get('model_ids')
        
        if not house_info:
            return jsonify({
                'error': '房屋信息不能为空',
                'status': 'failed'
            }), 400
        
        if not model_ids:
            return jsonify({
                'error': '模型ID列表不能为空',
                'status': 'failed'
            }), 400
        
        # 调用工具
        result_str = call_tool('predict_house_price', json.dumps({
            'house_info': house_info,
            'model_ids': model_ids
        }))
        
        result = json.loads(result_str)
        
        return jsonify({
            'result': result,
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'failed'
        }), 500


@agent_bp.route('/health', methods=['GET'])
def health():
    """Agent服务健康检查"""
    return jsonify({
        'service': 'agent',
        'status': 'healthy',
        'active_sessions': len(sessions),
        'timestamp': datetime.now().isoformat()
    })

