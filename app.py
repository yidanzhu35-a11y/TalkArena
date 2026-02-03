"""
TalkArena - 主应用
"""
import gradio as gr
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from ui.handlers import (
    get_scenarios, start_session, send_message,
    process_voice_input, end_session, init_models,
    handle_user_register, handle_rescue
)
from ui.theme import CUSTOM_CSS
from ui.components import (
    render_aura_dashboard, render_avatar_section,
    render_visual_stage, render_critique_box, render_aura_sidebar
)
from ui.user import get_current_user, register_user

SCENARIOS = {
    "negotiation": {"name": "商务谈判", "desc": "与王总进行一场商务价格谈判"},
    "debate": {"name": "辩论赛", "desc": "与反方辩手进行一场激烈辩论"},
    "interview": {"name": "压力面试", "desc": "挑战刷人的HR总监压力面试"},
    "shandong_dinner": {"name": "山东人的饭桌", "desc": "挑战大舅的劝酒功力和酒桌规矩"},
}

# 成员候选池（更丰富的角色列表）
MEMBERS_POOL = [
    ("👴", "大舅", "主陪·长辈·灵魂人物", "鲁中地区德高望重的长辈，热情但极讲规矩，擅长情感绑架和逻辑劝酒…"),
    ("👵", "大妗子", "旁观者·数杯人", "大舅的老伴，明着劝你别喝，实则数着你喝了几杯，为大舅再敬你找理由…"),
    ("👨", "表哥", "副陪·起哄能手", "大舅的儿子，负责活跃气氛，最擅长说'我陪一个'然后让你干了…"),
    ("👨‍💼", "王局长", "主陪·局领导·威压全场", "深谙官场礼仪，对座次、敬酒顺序极为讲究，用话语掌控节奏…"),
    ("👔", "李总", "副陪·商界老板·副驾驶", "能言善辩，擅长活跃气氛，总能找到话题接茬，能左右逢源…"),
    ("👩", "小赵", "实诚晚辈·新手", "性格耿直但缺乏饭局经验，善于酒桌踩雷，为了替领导撑面子…"),
    ("🧔", "老张", "酒桌老炮·段子手", "三句不离酒，满嘴都是段子，最擅长用俗语和顺口溜劝酒…"),
    ("👨‍🦳", "二叔", "话唠长辈·回忆杀", "喜欢翻旧账，动不动就说'当年你还小的时候'，情感攻势一流…"),
    ("👧", "表妹", "气氛组·起哄专家", "负责烘托气氛，最爱说'姐你喝不喝我都干了'，然后逼你也干…"),
    ("🧑‍💼", "老同学", "同辈·攀比狂魔", "总爱炫耀自己混得好，用激将法让你多喝，'咱俩谁跟谁啊'…"),
    ("👨‍🎓", "小舅", "文化人·掉书袋", "喜欢引经据典，用诗词歌赋劝酒，'酒逢知己千杯少'挂嘴边…"),
    ("👱‍♀️", "嫂子", "和事佬·双面人", "表面劝你少喝，转头就跟别人说'他酒量好着呢'，典型的捧一踩一…")
]


def create_ui():
    init_models()
    scenarios_data = get_scenarios()

    with gr.Blocks(title="TalkArena") as demo:
        session_id = gr.State("")
        current_scene = gr.State({"name": "", "sid": ""})
        mic_visible = gr.State(False)

        # ========== Page 1: 场景选择页 ==========
        with gr.Column(visible=True, elem_classes="scene-select-page") as page_select:
            gr.HTML('<div class="brand-title">TalkArena</div>')
            gr.HTML('<div class="brand-subtitle">选择挑战场景</div>')

            scenario_buttons = []
            
            # 场景对应的emoji
            scenario_emojis = {
                "shandong_dinner": "🍺",
                "negotiation": "💼",
                "debate": "🗣️",
                "interview": "🎯"
            }
            
            # 创建两列布局
            with gr.Row(elem_classes="scenario-grid"):
                with gr.Column(scale=1):
                    for i, (display_name, sid) in enumerate(scenarios_data):
                        if i % 2 == 0:  # 左列
                            is_active = (sid == "shandong_dinner")
                            cfg = SCENARIOS.get(sid, {"name": display_name, "desc": "开始挑战！"})
                            emoji = scenario_emojis.get(sid, "📋")
                            btn_label = f"{emoji} {cfg['name']}" + ("" if is_active else " (建设中)")
                            btn = gr.Button(
                                value=f"{btn_label}\n{cfg['desc']}",
                                elem_classes="scenario-card",
                                interactive=is_active
                            )
                            scenario_buttons.append((btn, sid, cfg["name"], cfg["desc"]))
                
                with gr.Column(scale=1):
                    for i, (display_name, sid) in enumerate(scenarios_data):
                        if i % 2 == 1:  # 右列
                            is_active = (sid == "shandong_dinner")
                            cfg = SCENARIOS.get(sid, {"name": display_name, "desc": "开始挑战！"})
                            emoji = scenario_emojis.get(sid, "📋")
                            btn_label = f"{emoji} {cfg['name']}" + ("" if is_active else " (建设中)")
                            btn = gr.Button(
                                value=f"{btn_label}\n{cfg['desc']}",
                                elem_classes="scenario-card",
                                interactive=is_active
                            )
                            scenario_buttons.append((btn, sid, cfg["name"], cfg["desc"]))



       # ========== Page 2: 角色配置页 (仅山东饭局) ==========
        with gr.Column(visible=False, elem_classes="config-page") as page_config:
            gr.HTML('<div class="config-page-title">山东人的饭桌</div>')
            gr.HTML('<div class="config-page-subtitle">选择你的饭局战场</div>')
            
            # 场景选择区
            gr.HTML('<div class="section-title">选择场景</div>')
            with gr.Row(elem_classes="scenario-cards-row"):
                scene_cards = []
                for scene in ["家庭聚会", "单位聚餐", "商务宴请", "同学聚会", "招待客户"]:
                    classes = "scene-card scene-card-selected" if scene == "商务宴请" else "scene-card"
                    btn = gr.Button(scene, elem_classes=classes)
                    scene_cards.append(btn)
            
            selected_scene = gr.State("商务宴请")

            # 场景描述区域
            with gr.Column(elem_classes="scene-desc-container"):
                scene_desc = gr.Textbox(
                    label="场景描述",
                    value="高端局，主陪副陪分清，话权要巧妙抓住，让话题走在你的节奏。",
                    lines=2,
                    max_lines=3,
                    interactive=False,
                    show_label=True
                )
            
            # 饭局成员区
            gr.HTML('<div class="section-title">饭局成员 <span class="ai-badge">AI生成</span></div>')

            # 成员选择状态
            member_selected = [gr.State(True), gr.State(True), gr.State(True)]  # 默认全选

            # 当前显示的成员（用State存储，初始为前3个）
            current_members = gr.State([MEMBERS_POOL[0], MEMBERS_POOL[1], MEMBERS_POOL[2]])

            with gr.Row(elem_classes="roster-row"):
                member_buttons = []
                for i in range(3):
                    btn = gr.Button(
                        value=f"{MEMBERS_POOL[i][0]}\n{MEMBERS_POOL[i][1]}\n{MEMBERS_POOL[i][2]}\n{MEMBERS_POOL[i][3]}",
                        elem_classes="roster-card roster-card-selected",
                        scale=1
                    )
                    member_buttons.append(btn)
            
            with gr.Row():
                regenerate_btn = gr.Button("🔄 随机换人", elem_classes="secondary-btn")
                edit_btn = gr.Button("✏️ 手动编辑", elem_classes="secondary-btn")
            
            start_game_btn = gr.Button("🍺 入席开整", variant="primary", elem_classes="start-game-btn")
            back_to_scenes = gr.Button("← 返回场景选择", elem_classes="back-link-btn")

        # ========== Page 3: 对话页 ==========
        with gr.Column(visible=False, elem_classes="chat-page") as page_chat:
            with gr.Column(elem_classes="chat-page-inner"):
                # 视觉舞台区 (集成气场条)
                visual_stage = gr.HTML("", elem_id="visual-stage")
                
                with gr.Row():
                    # 侧边控制栏 (缩小)
                    with gr.Column(scale=1, min_width=120, elem_classes="side-controls"):
                        rescue_btn = gr.Button("🆘 救场", variant="secondary", elem_classes="summon-btn-styled")
                        end_btn = gr.Button("🏁 结束对决", elem_classes="end-btn")
                        back_btn = gr.Button("↩ 返回场景选择", elem_classes="back-btn", visible=False)
                        status_display = gr.Markdown("", elem_id="status-display")
                        
                        # 侧边气场条 (新位置)
                        aura_sidebar = gr.HTML(render_aura_sidebar(50, 50))

                    # 主对话区 (占满)
                    with gr.Column(scale=9, elem_classes="main-chat-col"):
                        # 判定反馈框 (顶部，可隐藏)
                        critique_display = gr.HTML(render_critique_box("正在分析局势..."), visible=False)
                        
                        # 聊天记录区（中间，可滚动）
                        chatbot = gr.Chatbot(
                            show_label=False,
                            elem_classes="chat-box-container",
                            height=500
                        )
                                
                        # 总结区域（初始隐藏，结束时显示）
                        summary_display = gr.Markdown(visible=False, elem_classes="summary-box")
                        
                        # 语音输入浮动层（隐藏状态）
                        with gr.Column(visible=False, elem_classes="mic-container-floating") as mic_box:
                            mic = gr.Audio(
                                sources=["microphone", "upload"],
                                type="filepath",
                                label="🎙️ 语音输入",
                                container=False
                            )
                                
                        # 输入区（固定底部）
                        with gr.Row(elem_classes="input-row"):
                            mic_toggle = gr.Button("🎙️", scale=0, min_width=40, elem_classes="mic-toggle-btn")
                            txt = gr.Textbox(
                                show_label=False,
                                placeholder="输入消息...",
                                container=False,
                                scale=10
                            )
                            btn_send = gr.Button("发送", scale=0, min_width=60, elem_classes="send-btn")
                            
                    audio_player = gr.Audio(visible=False, autoplay=True)
        
        # ========== Page 4: 复盘报告页 ==========
        with gr.Column(visible=False, elem_classes="report-page") as page_report:
            report_html = gr.HTML("", elem_id="game-report")

            with gr.Row(elem_classes="report-buttons"):
                menu_btn = gr.Button("🏠 返回菜单", elem_classes="btn-light")
                share_btn = gr.Button("📤 分享成绩", elem_classes="btn-purple")

            # 下载文件组件
            download_file = gr.File(label="📥 点击下载报告", visible=True, elem_classes="download-file")
        
        # ========== 事件处理 ==========

        def on_select_scene(sid, name, desc):
            # 如果是山东饭局，跳转到配置页
            if sid == "shandong_dinner":
                return (
                    gr.update(visible=False),  # 隐藏场景选择页
                    gr.update(visible=True),   # 显示配置页
                    gr.update(visible=False),  # 隐藏对话页
                    sid  # 保存场景ID
                )
            
            # 其他场景直接开始
            sess, hist, _, ai_d, user_d = start_session(sid)
            user = get_current_user()
            
            from ui.handlers import get_orchestrator
            orch = get_orchestrator()
            scene_cfg = orch.scenarios.get(sid, {})
            theme_color = scene_cfg.get("theme_color", "#4A90E2")
            characters = scene_cfg.get("characters")
            
            return (
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
                sess,
                {"name": name, "sid": sid, "theme_color": theme_color, "characters": characters},
                hist,
                render_visual_stage(characters, None, user_d, ai_d),
                render_aura_sidebar(user_d, ai_d),
                gr.update(value=render_critique_box("开始对决"), visible=True),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False)
            )

        pending_scenario = gr.State("")
        
        for btn, sid, name, desc in scenario_buttons:
            if sid == "shandong_dinner":
                btn.click(
                    fn=lambda s=sid, n=name, d=desc: on_select_scene(s, n, d),
                    outputs=[page_select, page_config, page_chat, pending_scenario]
                )
            else:
                btn.click(
                    fn=lambda s=sid, n=name, d=desc: on_select_scene(s, n, d),
                    outputs=[page_select, page_config, page_chat, session_id, current_scene, chatbot, 
                             visual_stage, aura_sidebar, critique_display, summary_display, end_btn, back_btn]
                )
        
        # 配置页场景选择事件
        scene_descriptions = {
            "家庭聚会": "家族聚餐，长辈当家，晚辈要有眼力见儿，敬酒规矩不能乱。",
            "单位聚餐": "同事聚餐，领导在场，注意场合和分寸，别让气氛尴尬。",
            "商务宴请": "高端局，主陪副陪分清，话权要巧妙抓住，让话题走在你的节奏。",
            "同学聚会": "老同学见面，有炫耀有攀比，要拿捏好尺度，别显得太势利。",
            "招待客户": "重要客户，以礼相待，既要显诚意又要有分寸，酒桌上谈生意。"
        }

        def update_scene(idx):
            all_scenes = ["家庭聚会", "单位聚餐", "商务宴请", "同学聚会", "招待客户"]
            scene_name = all_scenes[idx]
            desc = scene_descriptions.get(scene_name, "")
            import logging
            logging.info(f"[DEBUG] 场景选择: idx={idx}, {scene_name} - {desc}")

            # 返回：选中场景, 场景描述, 以及5个按钮的更新状态
            return (
                scene_name,
                gr.update(value=desc),
                gr.update(elem_classes="scene-card scene-card-selected" if idx == 0 else "scene-card"),
                gr.update(elem_classes="scene-card scene-card-selected" if idx == 1 else "scene-card"),
                gr.update(elem_classes="scene-card scene-card-selected" if idx == 2 else "scene-card"),
                gr.update(elem_classes="scene-card scene-card-selected" if idx == 3 else "scene-card"),
                gr.update(elem_classes="scene-card scene-card-selected" if idx == 4 else "scene-card")
            )

        # 为每个场景按钮绑定点击事件
        scene_cards[0].click(
            fn=lambda: update_scene(0),
            outputs=[selected_scene, scene_desc, scene_cards[0], scene_cards[1], scene_cards[2], scene_cards[3], scene_cards[4]]
        )
        scene_cards[1].click(
            fn=lambda: update_scene(1),
            outputs=[selected_scene, scene_desc, scene_cards[0], scene_cards[1], scene_cards[2], scene_cards[3], scene_cards[4]]
        )
        scene_cards[2].click(
            fn=lambda: update_scene(2),
            outputs=[selected_scene, scene_desc, scene_cards[0], scene_cards[1], scene_cards[2], scene_cards[3], scene_cards[4]]
        )
        scene_cards[3].click(
            fn=lambda: update_scene(3),
            outputs=[selected_scene, scene_desc, scene_cards[0], scene_cards[1], scene_cards[2], scene_cards[3], scene_cards[4]]
        )
        scene_cards[4].click(
            fn=lambda: update_scene(4),
            outputs=[selected_scene, scene_desc, scene_cards[0], scene_cards[1], scene_cards[2], scene_cards[3], scene_cards[4]]
        )

        # 成员卡片点击事件
        def toggle_member(idx, current_states):
            import logging
            new_states = list(current_states)
            new_states[idx] = not new_states[idx]
            logging.info(f"[DEBUG] 点击成员 {idx}, 选中状态: {new_states}")

            # 返回更新后的状态和所有按钮的样式
            updates = tuple(new_states)  # 三个State的新值
            button_updates = []
            for i in range(3):
                if new_states[i]:
                    button_updates.append(gr.update(elem_classes="roster-card roster-card-selected"))
                else:
                    button_updates.append(gr.update(elem_classes="roster-card"))

            return updates + tuple(button_updates)

        # 为每个成员按钮绑定点击事件
        member_buttons[0].click(
            fn=lambda s0, s1, s2: toggle_member(0, (s0, s1, s2)),
            inputs=member_selected,
            outputs=member_selected + member_buttons
        )
        member_buttons[1].click(
            fn=lambda s0, s1, s2: toggle_member(1, (s0, s1, s2)),
            inputs=member_selected,
            outputs=member_selected + member_buttons
        )
        member_buttons[2].click(
            fn=lambda s0, s1, s2: toggle_member(2, (s0, s1, s2)),
            inputs=member_selected,
            outputs=member_selected + member_buttons
        )

        # 随机换人按钮
        def regenerate_roster():
            import logging
            import random

            # 从候选池随机抽取3个不同的成员
            selected = random.sample(MEMBERS_POOL, 3)
            logging.info(f"[DEBUG] 随机换人: {[m[1] for m in selected]}")

            # 返回：选中状态（全选） + 新成员State + 3个按钮的更新
            button_updates = []
            for member in selected:
                avatar, name, role, desc = member
                button_updates.append(
                    gr.update(
                        value=f"{avatar}\n{name}\n{role}\n{desc}",
                        elem_classes="roster-card roster-card-selected"
                    )
                )

            return (True, True, True, selected) + tuple(button_updates)

        regenerate_btn.click(
            fn=regenerate_roster,
            outputs=member_selected + [current_members] + member_buttons
        )

        # 编辑模态框
        with gr.Column(visible=False, elem_id="edit-modal") as edit_modal:
            with gr.Column(elem_classes="modal-content"):
                gr.HTML('<div class="modal-header">手动编辑饭局成员</div>')
                
                # 成员编辑表单
                member_editors = []
                for i in range(3):
                    with gr.Row(elem_classes="member-editor-row"):
                        name_input = gr.Textbox(label=f"成员{i+1}姓名", elem_classes="member-name-input")
                        role_input = gr.Textbox(label="角色", elem_classes="member-role-input")
                        desc_input = gr.Textbox(label="描述", lines=3, elem_classes="member-desc-input")
                        avatar_input = gr.Textbox(label="头像", placeholder="输入emoji", elem_classes="member-avatar-input")
                        member_editors.append((name_input, role_input, desc_input, avatar_input))
                
                # 操作按钮
                with gr.Row(elem_classes="modal-buttons"):
                    save_btn = gr.Button("保存", variant="primary", elem_classes="save-btn")
                    cancel_btn = gr.Button("取消", elem_classes="cancel-btn")

        # 手动编辑按钮功能
        def edit_roster():
            import logging
            logging.info("[DEBUG] 点击了手动编辑按钮")
            # 显示编辑模态框
            return gr.update(visible=True)

        # 取消编辑
        def cancel_edit():
            return gr.update(visible=False)

        # 保存编辑
        def save_edit(name1, role1, desc1, avatar1, name2, role2, desc2, avatar2, name3, role3, desc3, avatar3):
            import logging
            logging.info("[DEBUG] 保存编辑")
            
            # 构建新的成员列表，确保名字不为空并去除空格
            new_members = [
                (avatar1 or "👤", (name1 or "").strip() or f"成员1", (role1 or "").strip() or "角色", (desc1 or "").strip() or "描述"),
                (avatar2 or "👤", (name2 or "").strip() or f"成员2", (role2 or "").strip() or "角色", (desc2 or "").strip() or "描述"),
                (avatar3 or "👤", (name3 or "").strip() or f"成员3", (role3 or "").strip() or "角色", (desc3 or "").strip() or "描述")
            ]
            
            logging.info(f"[DEBUG] 保存成员: {[m[1] for m in new_members]}")
            
            # 准备按钮更新
            button_updates = []
            for member in new_members:
                avatar, name, role, desc = member
                button_updates.append(
                    gr.update(
                        value=f"{avatar}\n{name}\n{role}\n{desc}",
                        elem_classes="roster-card roster-card-selected"
                    )
                )
            
            # 隐藏模态框并更新成员状态和按钮
            return [gr.update(visible=False), new_members] + button_updates

        # 绑定事件
        edit_btn.click(fn=edit_roster, outputs=[edit_modal])
        cancel_btn.click(fn=cancel_edit, outputs=[edit_modal])
        save_btn.click(
            fn=save_edit, 
            inputs=[inp for editor in member_editors for inp in editor], 
            outputs=[edit_modal, current_members] + member_buttons
        )

        # 配置页返回场景选择
        def back_from_config():
            return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)

        back_to_scenes.click(
            fn=back_from_config,
            outputs=[page_select, page_config, page_chat]
        )
        
        # 配置页开始游戏
        def start_from_config(sid, scene_name, member_sel_0, member_sel_1, member_sel_2, current_members_list):
            import logging
            logging.info(f"[DEBUG] 开始游戏: sid={sid}, scene_name={scene_name}, members={[member_sel_0, member_sel_1, member_sel_2]}")
            logging.info(f"[DEBUG] 当前显示的成员: {[m[1] for m in current_members_list]}")

            # 获取orchestrator并修改场景配置
            from ui.handlers import get_orchestrator
            orch = get_orchestrator()

            # 如果sid为空，使用shandong_dinner作为基础场景
            if not sid or sid not in orch.scenarios:
                sid = "shandong_dinner"
                logging.info(f"[DEBUG] 使用默认场景ID: {sid}")

            scene_cfg = orch.scenarios.get(sid, {}).copy()

            # 根据当前显示的成员和选择状态构建角色列表
            member_selections = [member_sel_0, member_sel_1, member_sel_2]
            filtered_characters = []

            for i, (avatar, name, role, desc) in enumerate(current_members_list):
                if i < len(member_selections) and member_selections[i]:
                    # 构建角色字典，用于orchestrator
                    char_dict = {
                        "name": name,
                        "avatar": avatar,
                        "bio": f"{role} - {desc}"
                    }
                    filtered_characters.append(char_dict)

            logging.info(f"[DEBUG] 选中的角色: {[c['name'] for c in filtered_characters]}")

            # 更新scenario配置
            scene_cfg["characters"] = filtered_characters
            orch.scenarios[sid]["characters"] = filtered_characters

            # **关键修复：动态生成system_prompt，替换硬编码的角色名**
            characters_info = "\n".join([
                f"{i+1}. {c['name']} ({c['avatar']}): {c['bio']}"
                for i, c in enumerate(filtered_characters)
            ])

            dynamic_system_prompt = f"""场景：{scene_name}，山东饭局。用户（你）作为晚辈/同事坐在这场酒局中。

酒桌角色：
{characters_info}

任务：你现在要同时扮演这些AI角色与用户对决。

【严格规则 - 必须遵守】：
1. **每一轮只能1个角色说话**
2. **禁止替用户说话！绝对不能出现"你:"或"用户:"开头的内容**
3. 角色要轮流随机发言，避免每次都是同一个人
4. 每个角色台词简短有力，不超过60字
5. 保持浓重的鲁中口音（昂、木有、杠好、养鱼）

【输出格式】：
{filtered_characters[0]['name']}: [台词内容]

**严禁多个角色同时发言！只能1个角色！**
**绝对禁止**：你: [任何内容]"""

            scene_cfg["system_prompt"] = dynamic_system_prompt
            orch.scenarios[sid]["system_prompt"] = dynamic_system_prompt
            logging.info(f"[DEBUG] 更新system_prompt，角色：{[c['name'] for c in filtered_characters]}")

            # 使用AI根据场景+角色动态生成开场白
            if len(filtered_characters) >= 2:
                logging.info(f"[DEBUG] 开始生成AI开场白...")

                # 构建角色信息描述
                characters_desc = "\n".join([
                    f"- {c['name']} ({c['avatar']}): {c['bio']}"
                    for c in filtered_characters
                ])

                # 场景描述
                scene_desc_map = {
                    "家庭聚会": "过年期间的家族聚餐，长辈要给晚辈敬酒，气氛热闹但讲究规矩",
                    "单位聚餐": "职场饭局，领导和同事在一起，新人需要懂规矩会敬酒",
                    "商务宴请": "商务宴请，主陪副陪分工明确，讲究礼节和分寸",
                    "同学聚会": "老同学见面，叙旧加攀比，气氛轻松但暗藏较劲",
                    "招待客户": "招待重要客户，东道主热情周到，要让客人感受到诚意"
                }
                scene_context = scene_desc_map.get(scene_name, "山东饭局，酒桌文化浓厚")

                # AI生成开场白的prompt
                opening_prompt = f"""你是山东饭局场景生成器。请为以下饭局生成开场白对话。

【场景】{scene_name} - {scene_context}

【角色】
{characters_desc}

【任务】
生成这个饭局的开场白，只有第一个角色发言。要求：
1. 完全符合角色的性格和身份特征
2. 体现浓重的鲁中口音和饭局文化（昂、木有、杠好等）
3. 第一个角色起头敬酒，开启饭局
4. 台词生动自然，有动作描写（用括号）
5. 输出格式严格为：角色名: 台词内容（含动作）
6. 台词不超过60字
7. **只能1个角色说话**

请直接输出对话，不要任何解释："""

                try:
                    ai_opening = orch.llm.generate(opening_prompt, max_new_tokens=300)
                    # 清理可能的多余内容
                    ai_opening = ai_opening.strip()
                    logging.info(f"[DEBUG] AI生成开场白: {ai_opening[:100]}...")

                    scene_cfg["opening"] = ai_opening
                    orch.scenarios[sid]["opening"] = ai_opening
                except Exception as e:
                    logging.error(f"[DEBUG] AI生成开场白失败: {e}, 使用默认开场白")
                    # 失败时使用简化的默认开场白
                    char1_name = filtered_characters[0]["name"]
                    char2_name = filtered_characters[1]["name"]
                    fallback = f"{char1_name}: 来来来，今天这个局，咱得好好唠唠！先干为敬！\n{char2_name}: 对对对，我也陪一个！"
                    scene_cfg["opening"] = fallback
                    orch.scenarios[sid]["opening"] = fallback

            sess, hist, _, ai_d, user_d = start_session(sid)
            theme_color = scene_cfg.get("theme_color", "#4A90E2")
            characters = filtered_characters

            return (
                gr.update(visible=False),
                gr.update(visible=True),
                sess,
                {"name": f"山东人的饭桌 - {scene_name}", "sid": sid, "theme_color": theme_color, "characters": characters},
                hist,
                render_visual_stage(characters, None, user_d, ai_d),
                render_aura_sidebar(user_d, ai_d),
                gr.update(value=render_critique_box("开始对决"), visible=True),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False)
            )

        start_game_btn.click(
            fn=start_from_config,
            inputs=[pending_scenario, selected_scene] + member_selected + [current_members],
            outputs=[page_config, page_chat, session_id, current_scene, chatbot,
                     visual_stage, aura_sidebar, critique_display, summary_display, end_btn, back_btn]
        )

        def toggle_mic(is_visible):
            new_visible = not is_visible
            return gr.update(visible=new_visible), new_visible

        mic_toggle.click(fn=toggle_mic, inputs=[mic_visible], outputs=[mic_box, mic_visible])

        def handle_rescue_ui(sess, scene, history):
            """救场按钮 - 生成高情商回复建议填入输入框"""
            import logging
            logging.info(f"[DEBUG] 救场按钮被点击: sess={sess}, scene={scene}")

            if not sess:
                logging.warning(f"[DEBUG] session_id为空，无法救场")
                return (history, "❌ 请先开始对决", "", "", "", None, "")

            characters = scene.get("characters") if scene else []
            logging.info(f"[DEBUG] 开始调用handle_rescue，characters={[c['name'] if isinstance(c, dict) else c for c in characters]}")
            chat_result, status, ai_d, user_d, audio, suggestion = handle_rescue(sess, history, "")
            
            return (
                chat_result,
                status,
                render_visual_stage(characters, None, user_d, ai_d),
                render_aura_sidebar(user_d, ai_d),
                render_critique_box("💡 已生成高情商回复建议"),
                audio,
                suggestion
            )

        rescue_btn.click(
            fn=handle_rescue_ui,
            inputs=[session_id, current_scene, chatbot],
            outputs=[chatbot, status_display, visual_stage, aura_sidebar, critique_display, audio_player, txt]
        )

        def on_end(sess, scene, history):
            """结束对决，生成复盘报告"""
            if not sess:
                yield (
                    gr.update(visible=False),  # 隐藏对话页
                    gr.update(visible=True),   # 显示报告页
                    "⚠️ 请先开始对决"  # 报告内容
                )
                return
                    
            from ui.handlers import get_orchestrator
            orch = get_orchestrator()
                    
            if sess not in orch.sessions:
                yield (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    "⚠️ 对决已结束"
                )
                return
                    
            # 显示加载界面
            loading_messages = [
                "正在复盘饭局细节...",
                "正在请教饭局高人...",
                "正在为你的人生捏一把汗...",
                "正在回收全场酒瓶...",
                "正在生成饭局勋章..."
            ]
                    
            loading_html = f'''
            <div style="width: 100%; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; background: #2c313c; color: white;">
                <div style="width: 50px; height: 50px; border: 5px solid rgba(255,255,255,0.1); border-top: 5px solid #4a5dca; border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 20px;"></div>
                <div id="loading-text" style="font-size: 18px;">{loading_messages[0]}</div>
                <style>
                    @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}
                </style>
            </div>
            '''
                    
            yield (
                gr.update(visible=False),
                gr.update(visible=True),
                loading_html
            )
                    
            # 获取场景信息
            scene_name = scene.get("name", "山东人的饭桌")
            scenario_id = scene.get("sid", "")
            scenario_config = orch.scenarios.get(scenario_id, {})
            characters = scenario_config.get("characters", [])
            npc_list = [{"name": c.get("name", "NPC"), "avatar": c.get("avatar", "👤")} for c in characters]
                    
            # 生成报告
            try:
                report_data = orch.generate_game_report(sess, scene_name, npc_list)
                        
                # 渲染HTML
                from ui.report import render_report_card
                report_html_content = render_report_card(
                    scene_name=report_data["scene_name"],
                    medal=report_data["medal"],
                    scores=report_data["scores"],
                    summary=report_data["summary"],
                    npc_os_list=report_data["npc_os_list"],
                    suggestion=report_data["suggestion"]
                )
                        
                yield (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    report_html_content
                )
                        
            except Exception as e:
                import traceback
                error_html = f'''
                <div style="padding: 40px; text-align: center; color: #e74c3c;">
                    <h2>⚠️ 生成报告失败</h2>
                    <p>{str(e)}</p>
                    <pre style="text-align: left; background: #f5f5f5; padding: 10px; border-radius: 5px; overflow: auto;">{traceback.format_exc()}</pre>
                </div>
                '''
                yield (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    error_html
                )
        
        end_btn.click(
            fn=on_end,
            inputs=[session_id, current_scene, chatbot],
            outputs=[page_chat, page_report, report_html]
        )

        def on_back():
            """返回场景选择"""
            return (
                gr.update(visible=True),   # 显示场景页
                gr.update(visible=False),  # 隐藏对话页
                "",                        # 清空session
                {"name": "", "sid": ""},   # 清空场景
                []                         # 清空聊天
            )

        back_btn.click(
            fn=on_back,
            outputs=[page_select, page_chat, session_id, current_scene, chatbot]
        )

        def handle_msg(sess, scene, text, history):
            if not sess:
                return history, "", "", "", None, gr.update(), gr.update(), ""
            user = get_current_user()
            theme_color = scene.get("theme_color", "#4A90E2")
            characters = scene.get("characters")
            game_over_detected = False
            for chat, judgment, ai_dom, user_dom, audio, game_over in send_message(sess, text, history):
                game_over_detected = game_over
                # 尝试解析当前讲话者
                last_msg = chat[-1]["content"] if chat and len(chat) > 0 else ""
                last_title = chat[-1].get("metadata", {}).get("title", "") if chat and len(chat) > 0 and chat[-1] else ""

                # 去除头像前缀
                speaker = last_title.split(' ')[-1] if ' ' in last_title else last_title

                # 使用send_message返回的judgment信息
                if not judgment:
                    judgment = "对局中"

                yield (
                    chat, "",
                    render_visual_stage(characters, speaker, user_dom, ai_dom),
                    render_aura_sidebar(user_dom, ai_dom),
                    render_critique_box(judgment),
                    audio,
                    gr.update(),
                    gr.update(),
                    ""
                )

                # 检测到游戏结束后立即break，然后处理
                if game_over:
                    break

            # 游戏结束时自动触发结束对局
            if game_over_detected:
                import time
                time.sleep(2)  # 短暂延迟让用户看到最后的气场变化

                # 显示加载界面
                loading_html = '''
                <div style="width: 100%; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; background: #2c313c; color: white;">
                    <div style="width: 60px; height: 60px; border: 6px solid rgba(255,255,255,0.1); border-top: 6px solid #4a5dca; border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 24px;"></div>
                    <div style="font-size: 20px; font-weight: 600; margin-bottom: 8px;">🎯 游戏结束</div>
                    <div style="font-size: 16px; color: #a0aec0;">正在生成复盘报告...</div>
                    <style>
                        @keyframes spin { 100% { transform: rotate(360deg); } }
                    </style>
                </div>
                '''

                yield (
                    chat, "",
                    render_visual_stage(characters, speaker, user_dom, ai_dom),
                    render_aura_sidebar(user_dom, ai_dom),
                    render_critique_box(judgment),
                    audio,
                    gr.update(visible=False),  # 隐藏对话页
                    gr.update(visible=True),   # 显示报告页
                    loading_html
                )

                from ui.handlers import get_orchestrator
                orch = get_orchestrator()

                if sess in orch.sessions:
                    # 使用与handle_end相同的方式生成报告
                    scene_name = scene.get("name", "山东人的饭桌")
                    scenario_id = scene.get("sid", "")
                    scenario_config = orch.scenarios.get(scenario_id, {})
                    characters = scenario_config.get("characters", [])
                    npc_list = [{"name": c.get("name", "NPC"), "avatar": c.get("avatar", "👤")} for c in characters]

                    try:
                        report_data = orch.generate_game_report(sess, scene_name, npc_list)

                        # 渲染HTML
                        from ui.report import render_report_card
                        report_html_content = render_report_card(
                            scene_name=report_data["scene_name"],
                            medal=report_data["medal"],
                            scores=report_data["scores"],
                            summary=report_data["summary"],
                            npc_os_list=report_data["npc_os_list"],
                            suggestion=report_data["suggestion"]
                        )

                        yield (
                            chat, "",
                            render_visual_stage(characters, speaker, user_dom, ai_dom),
                            render_aura_sidebar(user_dom, ai_dom),
                            render_critique_box(judgment),
                            audio,
                            gr.update(visible=False),  # 隐藏对话页
                            gr.update(visible=True),   # 显示报告页
                            report_html_content
                        )
                    except Exception as e:
                        import traceback
                        logger.error(f"[自动结束] 生成报告失败: {e}")
                        logger.error(traceback.format_exc())
                        # 发生错误时保持在对话页面
                        yield (
                            chat, "",
                            render_visual_stage(characters, speaker, user_dom, ai_dom),
                            render_aura_sidebar(user_dom, ai_dom),
                            render_critique_box(judgment),
                            audio,
                            gr.update(),
                            gr.update(),
                            ""
                        )

        def handle_voice(sess, scene, audio_path, history):
            if not sess or not audio_path:
                return history, "", "", "", "", None, gr.update(), gr.update(), ""
            user = get_current_user()
            theme_color = scene.get("theme_color", "#4A90E2")
            characters = scene.get("characters")
            game_over_detected = False
            for chat, judgment, ai_dom, user_dom, audio, game_over in process_voice_input(sess, audio_path, history):
                game_over_detected = game_over
                last_title = chat[-1].get("metadata", {}).get("title", "") if chat and len(chat) > 0 and chat[-1] else ""
                speaker = last_title.split(' ')[-1] if ' ' in last_title else last_title

                # 使用process_voice_input返回的judgment信息
                if not judgment:
                    judgment = "对局中"

                yield (
                    chat, "",
                    render_visual_stage(characters, speaker, user_dom, ai_dom),
                    render_aura_sidebar(user_dom, ai_dom),
                    render_critique_box(judgment),
                    audio,
                    gr.update(),
                    gr.update(),
                    ""
                )

                # 检测到游戏结束后立即break
                if game_over:
                    break

            # 游戏结束时自动触发结束对局
            if game_over_detected:
                import time
                time.sleep(0.5)

                # 显示加载界面
                loading_html = '''
                <div style="width: 100%; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; background: #2c313c; color: white;">
                    <div style="width: 60px; height: 60px; border: 6px solid rgba(255,255,255,0.1); border-top: 6px solid #4a5dca; border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 24px;"></div>
                    <div style="font-size: 20px; font-weight: 600; margin-bottom: 8px;">🎯 游戏结束</div>
                    <div style="font-size: 16px; color: #a0aec0;">正在生成复盘报告...</div>
                    <style>
                        @keyframes spin { 100% { transform: rotate(360deg); } }
                    </style>
                </div>
                '''

                yield (
                    chat, "",
                    render_visual_stage(characters, speaker, user_dom, ai_dom),
                    render_aura_sidebar(user_dom, ai_dom),
                    render_critique_box(judgment),
                    audio,
                    gr.update(visible=False),  # 隐藏对话页
                    gr.update(visible=True),   # 显示报告页
                    loading_html
                )

                from ui.handlers import get_orchestrator
                orch = get_orchestrator()

                if sess in orch.sessions:
                    # 使用与handle_end相同的方式生成报告
                    scene_name = scene.get("name", "山东人的饭桌")
                    scenario_id = scene.get("sid", "")
                    scenario_config = orch.scenarios.get(scenario_id, {})
                    characters = scenario_config.get("characters", [])
                    npc_list = [{"name": c.get("name", "NPC"), "avatar": c.get("avatar", "👤")} for c in characters]

                    try:
                        report_data = orch.generate_game_report(sess, scene_name, npc_list)

                        # 渲染HTML
                        from ui.report import render_report_card
                        report_html_content = render_report_card(
                            scene_name=report_data["scene_name"],
                            medal=report_data["medal"],
                            scores=report_data["scores"],
                            summary=report_data["summary"],
                            npc_os_list=report_data["npc_os_list"],
                            suggestion=report_data["suggestion"]
                        )

                        yield (
                            chat, "",
                            render_visual_stage(characters, speaker, user_dom, ai_dom),
                            render_aura_sidebar(user_dom, ai_dom),
                            render_critique_box(judgment),
                            audio,
                            gr.update(visible=False),  # 隐藏对话页
                            gr.update(visible=True),   # 显示报告页
                            report_html_content
                        )
                    except Exception as e:
                        import traceback
                        logger.error(f"[自动结束-语音] 生成报告失败: {e}")
                        logger.error(traceback.format_exc())
                        yield (
                            chat, "",
                            render_visual_stage(characters, speaker, user_dom, ai_dom),
                            render_aura_sidebar(user_dom, ai_dom),
                            render_critique_box(judgment),
                            audio,
                            gr.update(),
                            gr.update(),
                            ""
                        )

        txt.submit(
            fn=handle_msg,
            inputs=[session_id, current_scene, txt, chatbot],
            outputs=[chatbot, txt, visual_stage, aura_sidebar, critique_display, audio_player, page_chat, page_report, report_html]
        )
        btn_send.click(
            fn=handle_msg,
            inputs=[session_id, current_scene, txt, chatbot],
            outputs=[chatbot, txt, visual_stage, aura_sidebar, critique_display, audio_player, page_chat, page_report, report_html]
        )
        mic.change(
            fn=handle_voice,
            inputs=[session_id, current_scene, mic, chatbot],
            outputs=[chatbot, txt, visual_stage, aura_sidebar, critique_display, audio_player, page_chat, page_report, report_html]
        )
        
        # ========== 报告页按钮事件 ==========

        def on_back_to_menu():
            """返回菜单 - 返回场景选择页"""
            import logging
            logging.info("[DEBUG] 返回菜单按钮被点击")
            return (
                gr.update(visible=True),   # page_select 显示场景选择页
                gr.update(visible=False),  # page_report 隐藏报告页
                gr.update(visible=False),  # page_chat 隐藏对话页
                gr.update(visible=False),  # page_config 隐藏配置页
                "",                        # session_id
                {"name": "", "sid": ""},   # current_scene
                []                         # chatbot
            )
        
        def on_share(sess, scene):
            """分享成绩 - 保存报告为HTML文件"""
            import logging
            import os
            from datetime import datetime

            if not sess:
                logging.warning("[分享] 无有效session")
                return gr.update(value=None)

            try:
                from ui.handlers import get_orchestrator
                orch = get_orchestrator()

                # 生成报告数据
                scenario_id = scene.get("sid", "")
                scenario_config = orch.scenarios.get(scenario_id, {})
                scene_name = scene.get("name", "TalkArena")
                characters = scenario_config.get("characters", [])
                npc_list = [{"name": c.get("name", "NPC"), "avatar": c.get("avatar", "👤")} for c in characters]

                report_data = orch.generate_game_report(sess, scene_name, npc_list)

                # 渲染HTML
                from ui.report import render_report_card
                report_html_content = render_report_card(
                    scene_name=report_data["scene_name"],
                    medal=report_data["medal"],
                    scores=report_data["scores"],
                    summary=report_data["summary"],
                    npc_os_list=report_data["npc_os_list"],
                    suggestion=report_data["suggestion"]
                )

                # 保存为文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = "outputs/reports"
                os.makedirs(output_dir, exist_ok=True)
                file_path = os.path.abspath(f"{output_dir}/report_{timestamp}.html")

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(report_html_content)

                logging.info(f"[分享] 报告已保存: {file_path}")
                return gr.update(value=file_path)

            except Exception as e:
                import traceback
                logging.error(f"[分享] 生成报告失败: {e}")
                logging.error(traceback.format_exc())
                return gr.update(value=None)
        
        menu_btn.click(
            fn=on_back_to_menu,
            outputs=[page_select, page_report, page_chat, page_config, session_id, current_scene, chatbot],
            js="() => { setTimeout(() => window.location.reload(), 200); }"
        )
        
        share_btn.click(
            fn=on_share,
            inputs=[session_id, current_scene],
            outputs=[download_file]
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        css=CUSTOM_CSS,
        show_error=True,
        # 注意：Gradio 6.x 暂不完全支持自动重载，建议使用 gradio app.py 命令启动
    )
