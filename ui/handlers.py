from typing import List, Tuple, Generator
from orchestrator import Orchestrator, logger
import gradio as gr
from ui.user import register_user, get_current_user

_orchestrator_instance = None

def init_models():
    logger.info("Handlers 初始化模型...")
    global _orchestrator_instance
    _orchestrator_instance = Orchestrator(enable_tts=True)
    logger.info("Handlers 模型初始化完成")

def get_orchestrator() -> Orchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        init_models()
    return _orchestrator_instance

def convert_chat_history_to_gradio3(chat_history: List) -> List:
    """
    将字典格式的聊天历史转换为 Gradio 3.x 兼容的列表格式
    Input: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "...", "metadata": {...}}]
    Output: [["user message", "assistant reply"], ...]
    """
    gradio3_history = []
    current_user_msg = None

    for msg in chat_history:
        if isinstance(msg, dict):
            role = msg.get("role", "")
            content = msg.get("content", "")
            metadata = msg.get("metadata", {})
            title = metadata.get("title", "")

            if role == "user":
                # 如果有标题（如"救场大师"），添加到内容前
                if title and title != "用户":
                    current_user_msg = f"**{title}**: {content}"
                else:
                    current_user_msg = content
            elif role == "assistant":
                # 如果有标题（角色名），添加到内容前
                if title:
                    formatted_content = f"**{title}**: {content}"
                else:
                    formatted_content = content

                # 将用户消息和助手回复组成一对
                if current_user_msg is not None:
                    gradio3_history.append([current_user_msg, formatted_content])
                    current_user_msg = None
                else:
                    # AI 主动发言（如开场白）
                    gradio3_history.append([None, formatted_content])
        elif isinstance(msg, (list, tuple)) and len(msg) == 2:
            # 如果已经是列表/元组格式，直接使用
            gradio3_history.append(list(msg))

    # 如果还有未配对的用户消息，添加一个空回复
    if current_user_msg is not None:
        gradio3_history.append([current_user_msg, None])

    return gradio3_history

def get_scenarios() -> List[Tuple[str, str]]:
    orch = get_orchestrator()
    # 山东饭局放第一位
    scenarios_list = []
    if 'shandong_dinner' in orch.scenarios:
        scenarios_list.append((orch.scenarios['shandong_dinner'].get('name', 'shandong_dinner'), 'shandong_dinner'))
    
    for sid, scenario in orch.scenarios.items():
        if sid != 'shandong_dinner':
            scenarios_list.append((scenario.get('name', sid), sid))
    
    return scenarios_list

def start_session(scenario_id: str):
    if not scenario_id:
        return "", [], "❌ 请先选择场景", 50, 50

    orch = get_orchestrator()
    session = orch.start_session(scenario_id)

    chat_history = []

    for name, text in session.chat_history:
        # 检测是否为多角色
        is_user = name == session.user_name

        # Gradio 6.2 字典格式
        if is_user:
            chat_history.append({"role": "user", "content": text})
        else:
            scenario = orch.scenarios.get(session.scenario_id, {})
            chars = scenario.get("characters", [])

            # 检查文本是否已经包含角色名前缀（如 "大舅: xxx"）
            text_has_character_name = any(
                (c['name'] + ":" in text or c['name'] + "：" in text)
                for c in chars
            )

            if text_has_character_name:
                # 文本已包含角色名，直接解析
                if ":" in text or "：" in text:
                    sep = ":" if ":" in text else "："
                    char_name, content = text.split(sep, 1)
                    char_name = char_name.strip()

                    # 查找角色头像
                    avatar = ""
                    for c in chars:
                        if c['name'] == char_name:
                            avatar = c.get('avatar', '')
                            break

                    title = f"{avatar} {char_name}" if avatar else char_name
                    formatted_text = f"**{title}**: {content.strip()}"
                    chat_history.append({"role": "assistant", "content": formatted_text})
            else:
                # 文本不包含角色名，使用name参数
                avatar = ""
                for c in chars:
                    if c['name'] == name:
                        avatar = c.get('avatar', '')
                        break

                title = f"{avatar} {name}" if avatar else name
                formatted_text = f"**{title}**: {text}"
                chat_history.append({"role": "assistant", "content": formatted_text})

    status = f"✓ 对局开始 | 场景: {orch.scenarios[scenario_id]['name']}"

    return session.session_id, chat_history, status, session.ai_dominance, session.user_dominance

def process_voice_input(session_id: str, audio_file, chat_history: List) -> Generator:
    logger.info(f"[语音输入] 收到音频: {audio_file}, session: {session_id}")
    
    if not session_id:
        logger.warning("[语音输入] 无session")
        yield chat_history, "", 50, 50, None, False
        return

    if audio_file is None:
        logger.warning("[语音输入] 音频文件为None")
        yield chat_history, "", 50, 50, None, False
        return

    orch = get_orchestrator()

    user_text = orch.transcribe_audio(audio_file)
    logger.info(f"[语音输入] 转录成功: {user_text}")

    if not user_text.strip():
        logger.warning("[语音输入] 转录结果为空")
        yield chat_history, "", 50, 50, None, False
        return
    
    for update in send_message(session_id, user_text, chat_history):
        yield update

def send_message(session_id: str, user_input: str, chat_history: List) -> Generator:
    if not session_id or not user_input.strip():
        yield chat_history, "", 50, 50, None, False
        return

    orch = get_orchestrator()

    # 检查session是否存在（可能已结束）
    if session_id not in orch.sessions:
        logger.warning(f"[发送消息] Session {session_id} 不存在或已结束")
        yield chat_history, "", 50, 50, None, False
        return

    session = orch.sessions[session_id]

    # 将 Gradio 3.x 格式转换回内部字典格式进行处理
    dict_history = []
    for msg in chat_history:
        if isinstance(msg, (list, tuple)) and len(msg) == 2:
            user_msg, ai_msg = msg
            if user_msg:
                dict_history.append({"role": "user", "content": user_msg})
            if ai_msg:
                dict_history.append({"role": "assistant", "content": ai_msg})
        elif isinstance(msg, dict):
            dict_history.append(msg)

    chat_history = dict_history
    # 如果不是由大师介入的建议，而是用户输入的，就正常添加
    if not user_input.startswith("💡 **(大师介入)**"):
        chat_history.append({"role": "user", "content": user_input})
    else:
        # 大师介入：AI 代替用户回答
        chat_history.append({"role": "user", "content": user_input.replace("💡 **(大师介入)**: ", ""), "metadata": {"title": "救场大师"}})
    
    thinking_msg_added = False
    think_start = None
    model_name = ""
    
    # 清理输入文本（去除展示用的前缀）
    actual_input = user_input.replace("💡 **(大师介入)**: ", "")
    
    for update in orch.process_turn_streaming(session_id, actual_input):
        stage = update["stage"]
        ai_dom = update["ai_dominance"]
        user_dom = update["user_dominance"]
        
        if stage == "user_sent":
            yield chat_history, "", ai_dom, user_dom, None, False

        elif stage == "ai_thinking":
            model_name = update.get("model_name", "")
            think_start = update.get("think_start")
            if not thinking_msg_added:
                chat_history.append({"role": "assistant", "content": f"🤔 **正在思考...** (模型: {model_name})"})
                thinking_msg_added = True
            yield chat_history, "", ai_dom, user_dom, None, False

        elif stage == "ai_responded":
            yield chat_history, "", ai_dom, user_dom, None, False

        elif stage == "complete":
            ai_text = update["ai_text"]
            audio_path = update["audio_path"]
            judgment = update.get("judgment", "")
            shift = update.get("dominance_shift", 0)
            game_over = update.get("game_over", False)
            game_result = update.get("game_result", None)

            shift_str = f"+{shift}" if shift > 0 else str(shift)
            
            # 处理多角色解析
            responses = []
            scenario = orch.scenarios.get(session.scenario_id, {})
            characters = scenario.get("characters", [])

            # 检查是否有角色名称出现（支持单行或多行）
            has_character_name = any(c['name'] + ":" in ai_text or c['name'] + "：" in ai_text for c in characters)

            if has_character_name:
                lines = ai_text.split('\n') if '\n' in ai_text else [ai_text]
                for line in lines:
                    if ":" in line or "：" in line:
                        sep = ":" if ":" in line else "："
                        name, text = line.split(sep, 1)
                        name_stripped = name.strip()

                        # 只接受配置的角色
                        valid_character_names = [c['name'] for c in characters]
                        if name_stripped not in valid_character_names:
                            continue

                        # 查找角色头像
                        avatar = ""
                        for c in characters:
                            if c['name'] == name_stripped:
                                avatar = c.get('avatar', '')
                                break
                        title = f"{avatar} {name_stripped}" if avatar else name_stripped
                        formatted_content = f"**{title}**: {text.strip()}"
                        responses.append({"role": "assistant", "content": formatted_content})
                    else:
                        if line.strip():
                            responses.append({"role": "assistant", "content": line.strip()})
            else:
                # 没有角色名称的情况（单角色场景）
                ai_name = session.ai_name
                avatar = ""
                if not characters and "avatar" in scenario:
                    avatar = scenario["avatar"]
                elif len(characters) == 1:
                    avatar = characters[0].get("avatar", "")

                title = f"{avatar} {ai_name}" if avatar else ai_name
                formatted_content = f"**{title}**: {ai_text}"
                responses.append({"role": "assistant", "content": formatted_content})

            # 替换思考消息
            if thinking_msg_added and chat_history and chat_history[-1].get("content", "").startswith("🤔"):
                chat_history.pop()

            # 合并多个角色的消息为一条，避免Gradio合并显示导致嵌套
            import time
            think_time = f"{time.time() - think_start:.1f}s" if think_start else ""

            if len(responses) > 1:
                # 多个角色：合并为一条消息
                combined_content = "\n\n---\n\n".join([r["content"] for r in responses])
                chat_history.append({"role": "assistant", "content": combined_content})
            elif len(responses) == 1:
                # 单个角色：直接添加
                chat_history.append(responses[0])

            yield chat_history, judgment, ai_dom, user_dom, audio_path, game_over

def handle_rescue(session_id: str, chat_history: List, txt_input: str) -> Tuple:
    """处理救场请求 - 生成高情商回复供用户参考"""
    if not session_id:
        return (chat_history, "❌ 请先开始对决", 50, 50, None, "")
    
    orch = get_orchestrator()
    session = orch.sessions[session_id]
    
    # 调用AI生成高情商回复建议
    suggestion = orch.get_rescue_suggestion(session_id)
    
    # 将建议填入输入框，由用户决定是否发送
    return (chat_history, "💡 已生成高情商回复建议，请查看输入框", session.ai_dominance, session.user_dominance, None, suggestion)

def end_session(session_id: str, chat_history: List):
    """结束对决，生成总结和建议"""
    if not session_id:
        return gr.update(visible=False), gr.update(visible=False), "❌ 请先开始对决"
    
    orch = get_orchestrator()
    
    if session_id not in orch.sessions:
        return gr.update(visible=False), gr.update(visible=False), "❌ 对决已结束或不存在"
    
    # 生成总结
    summary, file_path = orch.end_session_with_summary(session_id)
    
    summary_md = f"""
### 🏆 对决总结

{summary}
"""
    
    return (
        gr.update(value=summary_md, visible=True),
        gr.update(value=file_path, visible=True),
        "🏁 对决已结束"
    )

def handle_user_register(name: str, surname: str, email: str, message: str):
    """处理用户注册"""
    if not name.strip():
        return None
    
    user = register_user(
        name=name.strip(),
        surname=surname.strip(),
        email=email.strip(),
        message=message.strip()
    )
    
    logger.info(f"[用户注册] {user.display_name} (ID: {user.user_id})")
    return user