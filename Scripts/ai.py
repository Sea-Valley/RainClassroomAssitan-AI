from openai import OpenAI
from Scripts.Utils import get_config_path
import json

def get_ai_config():
    """获取AI配置信息"""
    try:
        config_path = get_config_path()
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # 如果配置中没有AI相关配置，则返回默认值
        if "ai_config" not in config:
            return {"api_key": "", "base_url": "https://api.deepseek.com"}
        
        return config["ai_config"]
    except Exception as e:
        print(f"获取AI配置出错: {e}")
        return {"api_key": "", "base_url": "https://api.deepseek.com"}

def get_openai_client():
    """获取OpenAI客户端实例"""
    ai_config = get_ai_config()
    api_key = ai_config.get("api_key", "")
    base_url = ai_config.get("base_url", "https://api.deepseek.com")
    
    if not api_key:
        print("未设置API密钥，请在配置中设置")
    
    return OpenAI(api_key=api_key, base_url=base_url)

def ai_calc(problem_type, body, options):
    """
    使用大模型计算题目答案
    
    参数:
    problem_type (int): 问题类型 (1:单选题, 2:多选题, 3:投票题)
    body (str): 题目题干
    options (list): 选项列表，每个选项是一个字典，包含key和value
    
    返回:
    list: 计算出的答案，格式为选项的key列表，如 ['A']、['A', 'C', 'D'] 等
    """
    # 构建选项文本
    options_text = ""
    for option in options:
        options_text += f"{option['key']}: {option['value']}\n"
    
    # 根据问题类型构建不同的提示
    if problem_type == 1:  # 单选题
        instruction = "这是一道单选题，请选择一个最合适的选项。只需回答选项字母，如'A'。"
    elif problem_type == 2:  # 多选题
        instruction = "这是一道多选题，请选择所有正确的选项（至少两个）。只需回答选项字母，如'A,C,D'。至少有两个选项是正确的，并且宁可少选（如只选最有可能的两项）也不要多选错误选项（如选了三项但有一项是错误的），因为错选或者多选不给分，少选却有一半的分数。"
    elif problem_type == 3:  # 投票题
        instruction = "这是一道投票题，类似单选题，请选择一个最合适的选项。只需回答选项字母，如'A'。"
    else:
        instruction = "请分析这个问题，并选择正确的选项。只需回答选项字母。"
    
    # 构建完整提示
    prompt = f"""请回答以下题目，{instruction}
    
题目：{body}

选项：
{options_text}

请直接回答选项字母，不要有任何解释或其他文字。例如：A 或 A,B,C"""
    
    try:
        # 获取AI客户端
        client = get_openai_client()
        
        # 调用大模型API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的答题助手，只回答选项字母，不做任何解释。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.15,  # 降低随机性，使回答更确定
            stream=False
        )
        
        # 获取回答
        answer_text = response.choices[0].message.content.strip()
        
        # 处理回答，转换为列表格式
        # 移除可能的空格、标点符号等
        answer_text = answer_text.replace(' ', '').replace('，', ',').replace('、', ',').replace(';', ',').replace('；', ',')
        
        # 如果回答包含逗号，说明是多选题
        if ',' in answer_text:
            answers = answer_text.split(',')
        else:
            answers = [answer_text]
        
        # 过滤掉非选项字母的内容
        valid_options = [opt['key'] for opt in options]
        answers = [ans for ans in answers if ans in valid_options]
        
        # 确保多选题至少有两个答案
        if problem_type == 2 and len(answers) < 2 and len(valid_options) >= 2:
            # 如果答案少于2个，随机添加一个不同的选项
            import random
            remaining_options = [opt for opt in valid_options if opt not in answers]
            if remaining_options:
                answers.append(random.choice(remaining_options))
        
        return answers
        
    except Exception as e:
        print(f"调用AI模型出错: {e}")
        # 出错时返回空列表
        return []

# 测试代码
if __name__ == "__main__":
    # 测试多选题
    print("\n测试多选题：")
    problem_type = 2
    body = "以下哪些学说或发现是马克思恩格斯创立他们学说的自然科学基础:"
    options = [
        {"key": "A", "value": "细胞学说"},
        {"key": "B", "value": "自然辩证法"},
        {"key": "C", "value": "分子进化学说"},
        {"key": "D", "value": "日心说"},
        {"key": "E", "value": "生物进化论"},
        {"key": "F", "value": "能量守恒与转化定律"}
    ]
    result = ai_calc(problem_type, body, options)
    print(f"多选题答案: {result}")
    
    # 测试单选题
    print("\n测试单选题：")
    problem_type = 1
    body = "马克思、恩格斯出生前的德国总体上来说是落后的、黑暗的、反动的，但是莱茵地区却已经成为了德国甚至是欧洲资本主义工业先进地区。"
    options = [
        {"key": "A", "value": "正确"},
        {"key": "B", "value": "错误"}
    ]
    result = ai_calc(problem_type, body, options)
    print(f"单选题答案: {result}")
    
    # 测试投票题
    print("\n测试投票题：")
    problem_type = 3
    body = "马克思主义是什么？"
    options = [
        {"key": "A", "value": "马克思和恩格斯的思想"},
        {"key": "B", "value": "列宁的思想"},
        {"key": "C", "value": "关于无产阶级和人类解放的学说"},
        {"key": "D", "value": "中国特色社会主义"}
    ]
    result = ai_calc(problem_type, body, options)
    print(f"投票题答案: {result}") 