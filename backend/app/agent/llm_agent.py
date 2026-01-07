import os
import requests
from dotenv import load_dotenv

load_dotenv()

QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_API_BASE = os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")



class QwenClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        self.api_key = api_key or QWEN_API_KEY
        self.base_url = (base_url or QWEN_API_BASE).rstrip("/")
        self.model = model or QWEN_MODEL

        if not self.api_key:
            raise ValueError("缺少 QWEN_API_KEY，请在 .env 中配置")

    def chat(self, messages: list[dict], tools: list[dict] | None = None, tool_choice: str | dict | None = None):
        """
        messages: [{"role": "user"|"assistant"|"system", "content": "..."}]
        tools: 工具列表（函数描述），用来做 function calling
        tool_choice: 可以是 "auto" / "none" / {"type": "function", "function": {"name": "..."}}
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data

def simple_chat():
    client = QwenClient()

    messages = [
        {"role": "system", "content": "你是一个友好的中文助手。"},
    ]

    while True:
        user_input = input("你：").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("结束对话。")
            break

        messages.append({"role": "user", "content": user_input})

        resp = client.chat(messages)
        choice = resp["choices"][0]
        answer = choice["message"]["content"]

        print("助手：", answer)

        messages.append({"role": "assistant", "content": answer})

import datetime
import json
import joblib
import io


def get_current_time(city: str | None = None) -> str:
    """
    一个简单的工具：返回当前时间（你可以忽略 city，或者以后扩展成根据城市时区返回）
    """
    now = datetime.datetime.now()
    if city:
        # 这里先不做真正的时区转换，只做演示
        return f"{city} 当前时间（本地时间）是 {now.strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        # return f"呵呵，我才不告诉你时间"
        return f"当前时间（本地时间）是 {now.strftime('%Y-%m-%d %H:%M:%S')}"


def predict_house_price(house_info: dict | str, model_ids: list | str) -> str:
    """
    预测房价的工具函数
    
    参数:
        house_info: 房屋信息字典（或JSON字符串），包含小区、成交时间、建筑面积等特征
        model_ids: 要使用的模型ID列表（或JSON字符串），会从数据库加载这些模型进行预测并加权平均
    
    返回:
        预测结果的JSON字符串
    """
    from app.models.model import MLModel
    from app.train.eval import federated_predict_house
    from app.train.train_dp import eval_house_by_dict
    print("大模型工具调用")
    print(house_info)
    print(model_ids)
    try:
        # 处理参数类型（可能是字符串或字典/列表）
        if isinstance(house_info, str):
            house_info = json.loads(house_info)
        if isinstance(model_ids, str):
            model_ids = json.loads(model_ids)
        
        # 验证输入
        if not house_info:
            return json.dumps({
                "error": "房屋信息不能为空",
                "status": "failed"
            }, ensure_ascii=False)
        
        if not model_ids or len(model_ids) == 0:
            return json.dumps({
                "error": "至少需要指定一个模型ID",
                "status": "failed"
            }, ensure_ascii=False)
        
        # 收集所有模型的预测结果
        results = []
        
        for model_id in model_ids:
            try:
                # 确保 model_id 是整数
                model_id = int(model_id)
                
                # 从数据库加载模型
                ml_model = MLModel.query.get(model_id)
                
                if ml_model is None:
                    results.append({
                        "status": "failed",
                        "client_id": model_id,
                        "client_name": f"Model_{model_id}",
                        "error": f"模型ID {model_id} 不存在"
                    })
                    continue
                
                # 反序列化模型
                model_bytes = ml_model.get_model_content()
                model = joblib.load(io.BytesIO(model_bytes))
                
                # 进行预测
                print("开始预测",len(house_info))
                unit_price, total_price = eval_house_by_dict(house_info, model)
                
                # 添加预测结果
                results.append({
                    "status": "success",
                    "client_id": model_id,
                    "client_name": ml_model.model_name,
                    "prediction": {
                        "data_count": ml_model.data_count,
                        "total_price": total_price if total_price else 0,
                        "unit_price": unit_price
                    }
                })
                
            except Exception as e:
                results.append({
                    "status": "failed",
                    "client_id": model_id,
                    "client_name": f"Model_{model_id}",
                    "error": str(e)
                })
        
        # 使用联邦学习方式融合多个模型的预测结果
        final_result = federated_predict_house(results)
        
        # 添加详细的预测信息
        final_result["individual_predictions"] = results
        final_result["status"] = "success"
        
        return json.dumps(final_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"预测过程出错: {str(e)}",
            "status": "failed"
        }, ensure_ascii=False)


# 给大模型看的"工具 schema"
TIME_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "获取当前时间，可以指定城市名称。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，比如 北京、上海、London 等",
                }
            },
            "required": [],
        },
    },
}

# 房价预测工具的 schema
PREDICT_HOUSE_PRICE_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "predict_house_price",
        "description": "预测房价的工具。根据房屋信息和指定的模型ID列表，预测房屋的单价和总价。支持使用多个模型进行加权平均预测。",
        "parameters": {
            "type": "object",
            "properties": {
                "house_info": {
                    "type": "object",
                    "description": "房屋信息字典，需要包含以下字段：小区、成交时间、建筑面积、房屋户型、所在楼层、建成年代、装修情况、房屋朝向、区域、街道、城市等。例如: {\"小区\": \"某小区\", \"建筑面积\": \"100㎡\", \"房屋户型\": \"3室2厅\", \"建成年代\": 2010, ...}",
                },
                "model_ids": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "要使用的模型ID列表，例如 [1, 2, 3]。系统会从数据库加载这些模型并进行加权平均预测。",
                }
            },
            "required": ["house_info", "model_ids"],
        },
    },
}


# 工具名字到真实 Python 函数的映射
TOOL_NAME_TO_FUNC = {
    "get_current_time": get_current_time,
    "predict_house_price": predict_house_price,
}


def call_tool(name: str, arguments_json: str) -> str:
    """
    根据模型给的 name + arguments，调用对应的 Python 函数，并返回字符串结果。
    """
    if name not in TOOL_NAME_TO_FUNC:
        return f"错误：未知工具 {name}"

    func = TOOL_NAME_TO_FUNC[name]
    try:
        args = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        args = {}

    # 简单处理：只接受关键字参数
    result = func(**args)
    # 为了方便传给模型，我们统一转成字符串
    if not isinstance(result, str):
        result = str(result)
    return result
def run_agent():
    client = QwenClient()

    tools = [TIME_TOOL_SPEC, PREDICT_HOUSE_PRICE_TOOL_SPEC]

    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "你是一个智能房地产估价助手，可以与用户对话并帮助预测房价。\n"
                "当用户询问与当前时间、现在几点等问题相关时，请使用工具 get_current_time。\n"
                "当用户想要预测房价时，请使用工具 predict_house_price。用户需要提供房屋信息和模型ID列表。\n"
                "房屋信息应包含：小区、成交时间、建筑面积、房屋户型、所在楼层、建成年代、装修情况、房屋朝向、区域、街道、城市等字段。\n"
                "如果用户没有提供完整的房屋信息，请礼貌地询问缺失的信息。\n"
                "预测结果会包含加权平均的单价和总价，以及各个模型的详细预测信息。\n"
                "用户提供的信息中可能会包含房屋单价和总价，没关系，在模型预测时这些数据已经被屏蔽。\n"
            ),
        }
    ]

    while True:
        user_input = input("你：").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("结束对话。")
            break

        messages.append({"role": "user", "content": user_input})

        # 第一次调用：让模型决定要不要用工具
        resp = client.chat(messages, tools=tools, tool_choice="auto")
        msg = resp["choices"][0]["message"]
        print("resp",resp)
        print("msg",msg)
        # 情况1：模型直接用自然语言回答（没有调用工具）
        if "tool_calls" not in msg:
            answer = msg["content"]
            print("助手：", answer)
            messages.append({"role": "assistant", "content": answer})
            continue

        # 情况2：模型要调用一个或多个工具
        tool_calls = msg["tool_calls"]
        messages.append({
            "role": "assistant",
            "content": msg.get("content", ""),
            "tool_calls": tool_calls,
        })

        tool_results_messages = []

        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            arguments = tool_call["function"].get("arguments", "{}")
            tool_call_id = tool_call.get("id", "")

            print(f"[debug] 模型请求调用工具: {func_name}({arguments})")

            result_str = call_tool(func_name, arguments)

            # 把工具执行结果作为一条 "tool" 消息加入对话
            tool_results_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": func_name,
                "content": result_str,
            })

        messages.extend(tool_results_messages)

        # 第二次调用：把工具执行结果交给模型，让它产出最终自然语言回复
        resp2 = client.chat(messages)
        final_msg = resp2["choices"][0]["message"]
        final_answer = final_msg["content"]
        print("助手：", final_answer)
        messages.append({"role": "assistant", "content": final_answer})


def run_agent_with_app_context():
    """
    在 Flask 应用上下文中运行 agent
    用于需要访问数据库的场景
    """
    from app import create_app
    app = create_app()
    
    with app.app_context():
        run_agent()


if __name__ == "__main__":
    # 如果需要使用房价预测功能，请使用 run_agent_with_app_context()
    # 否则使用 run_agent() 即可
    run_agent_with_app_context()