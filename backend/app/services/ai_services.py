from openai import OpenAI

from app.config import settings
from app.common.exceptions import BusinessExceptions
from app.schemas.ai import ChatRequest
from app.services import kb_services

SYSTEM_PROMPT = """你是智能实验室预约系统的助手，回答要简洁。如果下面提供了实验室资料，请依据资料回答，不要编造资料里没有的时间、规则、设备。工你目前查不到真实的实验室空闲、设备库存、预约记录。
如果用户问现在哪些实验室能约、某台设备此刻有没有空，请说明去「实验室列表」查看。除了实验室相关的问题之外,不要回复用户无关的问题"""
Tools = [
    {
        "type": "funtion",
        "funtion": {
            "name": "list_open_labs",
            "description": "查询当前开放中实验室列表，可以按名称关键词进行筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "实验室的名称关键字,可以为空",
                    }
                },
            },
        },
    },
    {
        "type": "funtion",
        "funtion": {
            "name": "list_lab_equipments",
            "description": "查询某个实验室下的设备列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "实验室的名称关键字,可以为空",
                    }
                },
            },
        },
    },
]


# 创建OpenAi客户端
def get_client():
    if not settings.LLM_API_KEY:
        raise BusinessExceptions(message="为获取到ApiKey")
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)


def chat_llm(data: ChatRequest):

    # 对话
    if not data.messages:
        raise BusinessExceptions(message="对话内容不能为空")
    history = []  # 创建历史对话
    for message in data.messages:
        if message.role in ("student", "user", "assistant") and message.content.strip():
            role = "user" if message.role in ("student", "user") else "assistant"
            history.append({"role": role, "content": message.content.strip()})
    if not history:
        raise BusinessExceptions(message="对话内容为空")
    # 取出用户最新的一条提问内容
    question = next(
        (item["content"] for item in reversed(history) if item["role"] == "user"), ""
    )
    knowlege = kb_services.search(query=question)
    print(knowlege, "knowlege")
    system_prompt = SYSTEM_PROMPT
    if knowlege:
        system_prompt += "\n\n以下是检索到的实验室资料" + knowlege
    client = get_client()
    try:
        res = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *history,
            ],
        )
        content = res.choices[0].message.content
        if not content:
            raise BusinessExceptions(message="大模型没有返回任何内容！")
        return content
    except Exception:
        raise BusinessExceptions(message="大模型调用失败~")
