import torch  # Must preload before any other imports to resolve DLL deps

import streamlit as st
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Copy Streamlit Cloud secrets into os.environ for non-Streamlit modules
if hasattr(st, "secrets"):
    for k, v in st.secrets.items():
        if k not in os.environ:
            os.environ[k] = str(v)

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

st.set_page_config(
    page_title="园规通 — 风景园林设计规范智能助手",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ======== Design Tokens ========
       Primary: #2F6B55 (sage green)
       Bg page: #F5F7F5 | Sidebar: #EEF3EF
       Text: #1F2937 / #4B5563 / #9CA3AF
       Radius: 24px card, 14px button/input
       Transition: all .2s ease
    */
    :root {
        --primary: #2F6B55;
        --primary-hover: #255443;
        --bg-page: #F5F7F5;
        --bg-sidebar: #EEF3EF;
        --bg-card: #FFFFFF;
        --text-primary: #1F2937;
        --text-secondary: #4B5563;
        --text-muted: #9CA3AF;
        --border: #E4E8E4;
        --shadow-card: 0 10px 30px rgba(0,0,0,0.04);
        --shadow-button: 0 4px 12px rgba(47,107,85,0.12);
        --radius-card: 24px;
        --radius-btn: 14px;
    }

    /* ======== Global page ======== */
    [data-testid="stAppViewContainer"] {
        background: var(--bg-page);
    }
    [data-testid="stHeader"] {
        background: transparent;
    }

    /* ======== Title ======== */
    .main-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--text-primary);
        text-align: center;
        margin-bottom: 0.3rem;
        letter-spacing: 0.02em;
    }
    .sub-title {
        font-size: 0.9rem;
        color: var(--text-muted);
        text-align: center;
        margin-bottom: 2rem;
    }

    /* ======== Sidebar ======== */
    [data-testid="stSidebar"] {
        background-color: var(--bg-sidebar);
    }
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: var(--text-primary) !important;
        font-weight: 600;
        font-size: 0.95rem;
    }

    /* ======== Buttons ======== */
    .stButton > button {
        border-radius: var(--radius-btn) !important;
        transition: all .2s ease !important;
        font-weight: 500 !important;
        height: 44px !important;
    }
    /* Primary */
    .stButton > button[kind="primary"] {
        background: var(--primary) !important;
        border: none !important;
        color: #fff !important;
        box-shadow: var(--shadow-button) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--primary-hover) !important;
        box-shadow: 0 6px 16px rgba(47,107,85,0.18) !important;
        transform: translateY(-1px);
    }
    /* Secondary */
    .stButton > button[kind="secondary"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--primary) !important;
        height: 44px !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: #F0F5F1 !important;
        border-color: var(--primary) !important;
    }
    /* All buttons: uniform height + text overflow */
    .stButton button {
        height: 44px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        display: block !important;
    }
    .stButton button p {
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* ======== Chat Input ======== */
    [data-testid="stChatInput"] textarea {
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-btn) !important;
        padding: 14px 18px !important;
        transition: all .2s ease !important;
        font-size: 0.95rem !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 4px rgba(47,107,85,0.08) !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: #9CA3AF !important;
    }

    /* ======== Reference Block ======== */
    .ref-block {
        background: var(--bg-card);
        border-left: 4px solid var(--primary);
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0;
        font-size: 0.9rem;
        box-shadow: var(--shadow-card);
    }
    .ref-block .ref-header {
        font-weight: 600;
        color: var(--primary);
        margin-bottom: 6px;
    }
    .ref-block .ref-body {
        color: var(--text-secondary);
    }

    /* ======== Welcome Overlay ======== */
    .welcome-overlay {
        background: linear-gradient(135deg, #EEF5F0 0%, #E8F2EB 100%);
        border: 1px solid var(--border);
        border-radius: var(--radius-card);
        padding: 48px 56px;
        text-align: center;
        margin-bottom: 32px;
        box-shadow: var(--shadow-card);
    }
    .welcome-overlay h2 {
        color: var(--text-primary);
        font-weight: 700;
    }

    /* ======== KB Status Dot ======== */
    .kb-status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
    }
    .kb-status-dot.ready { background: var(--primary); }
    .kb-status-dot.busy { background: #D4A853; }

    /* ======== Chat Messages ======== */
    [data-testid="stChatMessage"] {
        background: var(--bg-card) !important;
        border-radius: var(--radius-btn) !important;
        box-shadow: var(--shadow-card) !important;
        padding: 16px 20px !important;
    }

    /* ======== Containers / Cards ======== */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--bg-card) !important;
        border-radius: var(--radius-card) !important;
        border: 1px solid var(--border) !important;
        box-shadow: var(--shadow-card) !important;
        padding: 24px !important;
    }

    /* ======== Expander ======== */
    [data-testid="stExpander"] {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
    }

    /* ======== Status / Info ======== */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
        border-left: 4px solid var(--primary) !important;
    }
    [data-testid="stAlert"][kind="info"] {
        background: #EEF5F0 !important;
        border-left-color: var(--primary) !important;
    }
    [data-testid="stAlert"][kind="info"] svg {
        color: var(--primary) !important;
    }
    [data-testid="stAlert"][kind="info"] .stMarkdown p {
        color: var(--text-secondary) !important;
    }
    [data-testid="stNotification"] {
        border-left-color: var(--primary) !important;
    }

    /* ======== Scrollbar ======== */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

FULL_NAMES = {
    "CJJ37": "城市道路绿化设计标准",
    "CJJ82": "园林绿化工程施工及验收规范",
    "CJJT91": "风景园林基本术语标准",
    "GB50016": "建筑设计防火规范",
    "GB50180": "城市居住区规划设计标准",
    "GB50420": "城市绿地设计规范",
    "GB50763": "无障碍设计规范",
    "GB51192": "公园设计规范",
    "GB55014": "园林绿化工程项目规范",
}


def init_session():
    defaults = {
        "messages": [],
        "kb": None,
        "kb_ready": False,
        "kb_building": False,
        "progress_log": [],
        "welcome_dismissed": False,
        "pinned_pair": None,  # (user_msg, assistant_msg) to pin at top
        "verified_code": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


LOADED_INVITE = None


def load_invite_codes():
    global LOADED_INVITE
    if LOADED_INVITE is None:
        import json
        path = project_root / "data" / "invite_codes.json"
        LOADED_INVITE = json.load(open(path, encoding="utf-8")) if path.exists() else {"codes": [], "daily_limit": 20}
    return LOADED_INVITE


def get_daily_usage(code: str) -> int:
    from utils.conversation_logger import get_daily_usage as _usage
    return _usage(code)



def check_model_cache() -> bool:
    model_path = project_root / "models" / "BAAI" / "bge-small-zh-v1___5"
    required = ["config.json", "pytorch_model.bin", "tokenizer.json"]
    if not model_path.exists():
        return False
    return all((model_path / f).exists() for f in required)


def _update_feedback_in_db(msg_idx: int, feedback: str, helpful: int):
    """Update Supabase with like/dislike feedback."""
    msgs = st.session_state.messages
    a_msg = msgs[msg_idx] if msg_idx < len(msgs) else {}
    ts = a_msg.get("log_ts", "")
    code = st.session_state.verified_code or ""
    if not ts or not code:
        return
    try:
        import json as _json
        from urllib import request, parse
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            return
        qts = parse.quote(ts)
        qcode = parse.quote(code)
        req = request.Request(
            f"{url}/rest/v1/conversations?timestamp=eq.{qts}&invite_code=eq.{qcode}",
            data=_json.dumps({"feedback": feedback, "helpful": helpful}).encode("utf-8"),
            headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Content-Type": "application/json", "Prefer": "return=minimal",
            },
            method="PATCH",
        )
        request.urlopen(req)
    except Exception:
        pass


def _render_thumbs(msg_idx: int):
    """Render like/dislike buttons for an assistant message."""
    fkey = f"feedback_{msg_idx}"
    if fkey not in st.session_state:
        st.session_state[fkey] = None
    fstate = st.session_state[fkey]

    if fstate is None:
        c1, c2, c3 = st.columns([1, 1, 6])
        with c1:
            if st.button("👍", key=f"like_{msg_idx}", help="有帮助"):
                st.session_state[fkey] = "like"
                _update_feedback_in_db(msg_idx, "有帮助", 1)
                st.rerun()
        with c2:
            if st.button("👎", key=f"dislike_{msg_idx}", help="有问题"):
                st.session_state[fkey] = "dislike"
                st.rerun()
    elif fstate == "like":
        st.caption("👍 感谢反馈！")
    elif fstate == "dislike":
        fb = st.text_area("请描述具体问题", placeholder="例如：条款号错误、答案不完整...", key=f"text_{msg_idx}", label_visibility="collapsed")
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button("提交", key=f"submit_{msg_idx}"):
                from utils.badcase_logger import log_badcase
                msgs = st.session_state.messages
                q = msgs[msg_idx - 1]["content"] if msg_idx > 0 else ""
                a = msgs[msg_idx]["content"]
                log_badcase(q, a, msgs[msg_idx].get("results", []), fb or "用户点踩")
                _update_feedback_in_db(msg_idx, fb or "用户点踩", -1)
                st.session_state[fkey] = "done"
                st.rerun()
        with c2:
            if st.button("取消", key=f"cancel_{msg_idx}"):
                st.session_state[fkey] = None
                st.rerun()
    elif fstate == "done":
        st.caption("已收到反馈，谢谢！")


def render_ref_block(meta: dict, content: str):
    code = meta.get("standard_code", "未知")
    name = meta.get("standard_name", "")
    clause = meta.get("clause_number", "")
    clause_str = f" 第{clause}条" if clause else ""
    header = f"{code} {name}{clause_str}"
    preview = content[:300] + ("..." if len(content) > 300 else "")
    st.markdown(f"""
    <div class="ref-block">
        <div class="ref-header">{header}</div>
        <div class="ref-body">{preview}</div>
    </div>
    """, unsafe_allow_html=True)


def main():
    init_session()

    # ---- Invite code gate ----
    if not st.session_state.verified_code:
        invite = load_invite_codes()
        st.markdown('<div class="main-title">园规通</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-title">风景园林设计规范智能助手</div>', unsafe_allow_html=True)
        st.markdown("")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            code_input = st.text_input("请输入邀请码", placeholder="YGT-XXXXXX", max_chars=10)
            if st.button("验证邀请码", type="primary", use_container_width=True):
                code = code_input.strip().upper()
                if code in invite.get("codes", []):
                    usage = get_daily_usage(code)
                    limit = invite.get("daily_limit", 20)
                    if usage >= limit:
                        st.error(f"今日已用 {usage}/{limit} 次，请明天再来")
                    else:
                        st.session_state.verified_code = code
                        st.rerun()
                else:
                    st.error("邀请码无效")
        return

    st.markdown('<div class="main-title">园规通</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">风景园林设计规范智能助手 · 9本规范 · 1168条条款</div>',
        unsafe_allow_html=True,
    )

    # ---- Welcome page ----
    if not st.session_state.welcome_dismissed:
        with st.status("正在检查系统状态...", expanded=True) as status:
            # Check model
            model_ok = check_model_cache()
            st.write("Embedding 模型: " + ("已缓存" if model_ok else "未下载"))
            # Check DB
            db_ok = False
            try:
                from rag.knowledge_base import KnowledgeBase
                kb_test = KnowledgeBase()
                db_count = kb_test.get_stats()["total_clauses"]
                db_ok = db_count > 0
                st.write(f"知识库: {db_count} 条条款" if db_ok else "知识库: 空")
            except Exception:
                st.write("知识库: 未初始化")
            status.update(label="系统检查完成", state="complete")

        st.markdown("""
        <div class="welcome-overlay">
            <h2>欢迎使用园规通！</h2>
            <p style="color:#374151;font-size:1rem;">
            覆盖 <b>9本</b> 风景园林核心国标/行标<br>
            <b>9本规范 · 1168条条款</b>
            </p>
        </div>
        """, unsafe_allow_html=True)

        if db_ok:
            if st.button("进入问答", type="primary", use_container_width=True):
                st.session_state.welcome_dismissed = True
                st.rerun()
        else:
            st.markdown(
                '<div style="background:#EEF5F0;border-left:4px solid #2F6B55;'
                'border-radius:12px;padding:14px 20px;color:#4B5563;font-size:0.95rem;'
                'text-align:center;margin:16px 0;">'
                '点击下方开始使用，加载预构建知识库</div>',
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                if st.button("开始使用", type="primary", use_container_width=True):
                    load_existing_kb()
        return

    # ---- Sidebar ----
    with st.sidebar:
        # Conversation history
        st.markdown("### 对话记录")
        if not st.session_state.messages:
            st.caption("暂无对话")
        else:
            user_msgs = [(i, m) for i, m in enumerate(st.session_state.messages)
                         if m["role"] == "user"]
            for idx, msg in user_msgs[-20:]:
                assistant_idx = idx + 1
                has_answer = (assistant_idx < len(st.session_state.messages)
                              and st.session_state.messages[assistant_idx]["role"] == "assistant")
                label = msg["content"][:20] + ("..." if len(msg["content"]) > 20 else "")
                btn_label = f"#{idx//2 + 1} {label}"
                if st.button(btn_label, key=f"hist_{idx}", use_container_width=True):
                    if has_answer:
                        st.session_state.pinned_pair = (idx, assistant_idx)
                    st.rerun()

        st.markdown("---")

        # KB controls
        st.markdown("### 知识库")

        if st.session_state.kb_ready and st.session_state.kb:
            stats = st.session_state.kb.get_stats()
            st.markdown(
                f'<span class="kb-status-dot ready"></span> '
                f'<b>就绪</b> · {stats["total_clauses"]} 条条款 · '
                f'{stats["mandatory_count"]} 条强制',
                unsafe_allow_html=True,
            )

            with st.expander("已加载规范"):
                for code, count in sorted(stats.get("standards", {}).items()):
                    name = FULL_NAMES.get(code, "")
                    st.text(f"{code} {name}  {count}条")
        else:
            st.markdown(
                '<span class="kb-status-dot busy"></span> <b>未加载</b>',
                unsafe_allow_html=True,
            )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("加载知识库", type="primary", use_container_width=True,
                         disabled=st.session_state.kb_building):
                load_existing_kb()
        with col2:
            if st.button("刷新", type="secondary", use_container_width=True,
                         disabled=st.session_state.kb_building):
                load_existing_kb()

        # Build progress — show in main area for visibility
        if st.session_state.kb_building:
            st.markdown("---")
            with st.status("正在初始化知识库...", expanded=True) as build_status:
                st.write("此过程包含 PDF 解析、条款切分、向量化，首次约需 10-20 分钟")
                st.write("进度将在完成后显示")
            # Note: real-time progress not possible due to Streamlit single-thread;
            # the build runs in load_and_build_kb() and shows result on completion.

        st.markdown("---")
        if st.button("清空对话", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # ---- Main chat area ----
    if st.session_state.kb_building:
        with st.spinner(""):
            st.markdown("### 🔧 正在初始化知识库...")
            st.caption("首次构建包含 PDF 解析、OCR 识别、条款切分、向量化")
            st.caption("请耐心等待，完成后将自动显示聊天界面")
        return

    if not st.session_state.kb_ready:
        st.markdown(
            '<div style="background:#EEF5F0;border-left:4px solid #2F6B55;'
            'border-radius:12px;padding:16px 20px;color:#4B5563;font-size:0.95rem;">'
            '在侧边栏点击「加载知识库」开始使用。</div>',
            unsafe_allow_html=True,
        )
        return

    # Filter mode: show only pinned conversation
    if st.session_state.pinned_pair is not None:
        ui, ai = st.session_state.pinned_pair
        msgs = st.session_state.messages
        u_msg = msgs[ui]
        a_msg = msgs[ai] if ai < len(msgs) else None
        q_num = ui // 2 + 1

        if st.button("← 返回全部对话", key="dismiss_pin"):
            st.session_state.pinned_pair = None
            st.rerun()

        st.caption(f"定位到对话 #{q_num}")
        with st.chat_message("user"):
            st.markdown(u_msg["content"])
        if a_msg:
            with st.chat_message("assistant"):
                st.markdown(a_msg.get("content", ""))
                results = a_msg.get("results", [])
                if results:
                    for r in results:
                        render_ref_block(r.get("metadata", {}), r.get("content", ""))
        return

    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and "results" in msg:
                st.markdown(msg["content"])
                _render_thumbs(idx)
            else:
                st.markdown(msg["content"])

    if prompt := st.chat_input("输入规范查询问题，如：居住区绿地率最低要求是多少？"):
        # Daily limit check
        invite = load_invite_codes()
        usage = get_daily_usage(st.session_state.verified_code)
        limit = invite.get("daily_limit", 20)
        if usage >= limit:
            st.error(f"今日已提问 {usage}/{limit} 次，请明天再来")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                    status = st.status("处理中...", expanded=False)
                    try:
                        status.update(label="正在检索...", state="running")
                        results = st.session_state.kb.search(prompt, top_k=5)

                        status.update(label="正在生成回答...", state="running")
                        from utils.llm_client import LLMClient
                        from utils.answer_generator import AnswerGenerator

                        llm = LLMClient()
                        gen = AnswerGenerator(llm)
                        answer = gen.generate(prompt, results)
                        answer = answer.replace("~", "～")
                        status.update(label="完成", state="complete")

                        st.markdown(answer)

                        from utils.conversation_logger import log
                        _ts = log(prompt, answer, results, invite_code=st.session_state.verified_code or "")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "results": results,
                            "log_ts": _ts,
                        })
                        st.rerun()

                    except Exception as e:
                        status.update(label=f"失败", state="error")
                        error_msg = f"查询失败: {e}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg,
                            "results": [],
                        })


def load_and_build_kb():
    try:
        from rag.pdf_parser import HAS_FITZ
        if not HAS_FITZ:
            st.warning("线上版不支持初始化知识库，请在本地构建后上传。")
            return
    except ImportError:
        st.warning("线上版不支持初始化知识库，请在本地构建后上传。")
        return

    st.session_state.kb_building = True
    st.session_state.progress_log = []

    try:
        from rag.knowledge_base import KnowledgeBase

        def on_progress(step, detail, current, total):
            label = {"parse": "解析", "embed": "嵌入", "done": "完成"}.get(step, step)
            entry = f"[{label}] {detail}"
            if entry not in st.session_state.progress_log:
                st.session_state.progress_log.append(entry)

        kb = KnowledgeBase()
        kb.build(progress_callback=on_progress)
        st.session_state.kb = kb
        st.session_state.kb_ready = True
        st.session_state.kb_building = False
        st.session_state.progress_log.append("[完成] 构建完毕")
        st.rerun()
    except Exception as e:
        st.session_state.kb_building = False
        st.session_state.progress_log.append(f"[错误] {e}")
        st.error(f"构建失败: {e}")


def load_existing_kb():
    with st.spinner("正在加载知识库..."):
        try:
            from rag.knowledge_base import KnowledgeBase
            kb = KnowledgeBase()
            stats = kb.get_stats()
            if stats["total_clauses"] == 0:
                st.warning("知识库为空，请先点击「初始化」构建")
            else:
                st.session_state.kb = kb
                st.session_state.kb_ready = True
                st.success(f"已加载 {stats['total_clauses']} 条条款 · "
                          f"{len(stats['standards'])} 本规范")
        except Exception as e:
            st.error(f"加载失败: {e}")


if __name__ == "__main__":
    main()
