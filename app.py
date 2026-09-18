import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

st.set_page_config(page_title="装备管理系统", page_icon="🎒", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# ---------- 数据层（已加入缓存，彻底解决 429 报错）----------

@st.cache_data(ttl=600, show_spinner=False)
def load_cached_data():
    # 内部执行实际的读取
    df = conn.read()
    return df

def load_data():
    # 每次需要刷新时可以调用此函数，或直接读缓存
    df = load_cached_data()
    if df.empty or "Equipment" not in df.columns or "Items" not in df.columns:
        return {}
    data = {}
    for _, row in df.iterrows():
        if pd.isna(row["Equipment"]) or str(row["Equipment"]).strip() == "":
            continue
        eq_name = str(row["Equipment"])
        try:
            items = json.loads(row["Items"]) if isinstance(row["Items"], str) and row["Items"].strip() else []
        except Exception:
            items = []
        # 兼容旧数据结构（只有 name/checked），补齐新字段
        for it in items:
            it.setdefault("quantity", "")
            it.setdefault("color", "")
            it.setdefault("notes", "")
            it.setdefault("checked", False)
        data[eq_name] = items
    return data

def save_data(data):
    rows = []
    for eq_name, items in data.items():
        rows.append({
            "Equipment": eq_name,
            "Items": json.dumps(items, ensure_ascii=False)
        })
    df = pd.DataFrame(rows if rows else [{"Equipment": "", "Items": ""}])
    conn.update(data=df)
    # 关键：每次保存数据后，必须清除缓存，确保下次读取到最新数据
    st.cache_data.clear()

def safe_save(data):
    try:
        save_data(data)
        return True
    except Exception as e:
        st.error(f"保存失败：{e}")
        return False

# ---------- 初始化 session_state ----------

if "page" not in st.session_state:
    st.session_state.page = "home"
if "selected_equipment" not in st.session_state:
    st.session_state.selected_equipment = None
if "edit_equipment_mode" not in st.session_state:
    st.session_state.edit_equipment_mode = False
if "edit_items_mode" not in st.session_state:
    st.session_state.edit_items_mode = False

try:
    equipment_data = load_data()
except Exception as e:
    st.error(f"读取 Google Sheet 失败：{e}")
    st.stop()

def go_home():
    st.session_state.page = "home"
    st.session_state.selected_equipment = None
    st.session_state.edit_items_mode = False
    st.rerun()

def go_detail(eq_name):
    st.session_state.page = "detail"
    st.session_state.selected_equipment = eq_name
    st.session_state.edit_items_mode = False
    st.rerun()

# ==================== 主页 ====================
if st.session_state.page == "home":

    top_left, top_right = st.columns([0.8, 0.2])
    with top_left:
        st.title("🎒 我的装备")
    with top_right:
        st.write("")
        if st.button("✏️ 编辑装备" if not st.session_state.edit_equipment_mode else "✅ 完成编辑",
                     use_container_width=True):
            st.session_state.edit_equipment_mode = not st.session_state.edit_equipment_mode
            st.rerun()

    # 搜索框：搜物品在哪个装备里
    search_query = st.text_input("🔍 搜索物品", placeholder="输入物品名称，查找它放在哪个装备里")

    if search_query.strip():
        st.subheader(f"搜索结果：「{search_query}」")
        found_any = False
        for eq_name, items in equipment_data.items():
            matches = [it for it in items if search_query.strip().lower() in it["name"].lower()]
            for m in matches:
                found_any = True
                with st.container(border=True):
                    c1, c2 = st.columns([0.7, 0.3])
                    with c1:
                        status = "✅ 已放入" if m.get("checked") else "⬜ 未放入"
                        detail_bits = []
                        if m.get("quantity"):
                            detail_bits.append(f"数量：{m['quantity']}")
                        if m.get("color"):
                            detail_bits.append(f"颜色：{m['color']}")
                        if m.get("notes"):
                            detail_bits.append(f"备注：{m['notes']}")
                        detail_str = " ".join(detail_bits)
                        st.markdown(f"**{m['name']}** {status} · 在「{eq_name}」")
                        if detail_str:
                            st.caption(detail_str)
                    with c2:
                        if st.button("前往该装备 →", key=f"goto_{eq_name}_{m['name']}", use_container_width=True):
                            go_detail(eq_name)
        if not found_any:
            st.info("没有找到匹配的物品。")

    else:
        # 添加新装备（编辑模式下显示）
        if st.session_state.edit_equipment_mode:
            with st.form("add_equipment_form", clear_on_submit=True):
                c1, c2 = st.columns([0.8, 0.2])
                with c1:
                    new_eq = st.text_input("新增装备名称", placeholder="如：数码背包", label_visibility="collapsed")
                with c2:
                    add_submitted = st.form_submit_button("➕ 添加", use_container_width=True)
                if add_submitted:
                    if new_eq.strip():
                        if new_eq not in equipment_data:
                            equipment_data[new_eq] = []
                            if safe_save(equipment_data):
                                st.success(f"已添加装备：{new_eq}")
                                st.rerun()
                        else:
                            st.warning("该装备已存在！")
                    else:
                        st.warning("请输入有效的装备名称！")

        st.divider()

        if not equipment_data:
            st.info("目前还没有任何装备。点击右上角「✏️ 编辑装备」来添加第一项装备。")
        else:
            cols = st.columns(3)
            for index, (eq_name, items) in enumerate(equipment_data.items()):
                col = cols[index % 3]
                with col:
                    with st.container(border=True):
                        packed = sum(1 for it in items if it.get("checked"))
                        total = len(items)

                        if st.session_state.edit_equipment_mode:
                            # 编辑模式：改名 + 删除
                            new_name = st.text_input(
                                "装备名称", value=eq_name, key=f"rename_{eq_name}"
                            )
                            rc1, rc2 = st.columns(2)
                            with rc1:
                                if st.button("💾 改名", key=f"save_rename_{eq_name}", use_container_width=True):
                                    if new_name.strip() and new_name != eq_name:
                                        if new_name in equipment_data:
                                            st.warning("已存在同名装备！")
                                        else:
                                            equipment_data[new_name] = equipment_data.pop(eq_name)
                                            if safe_save(equipment_data):
                                                st.rerun()
                            with rc2:
                                if st.button("🗑️ 删除", key=f"del_eq_{eq_name}", use_container_width=True, type="secondary"):
                                    del equipment_data[eq_name]
                                    if safe_save(equipment_data):
                                        st.success(f"已删除装备：{eq_name}")
                                        st.rerun()
                        else:
                            st.subheader(f"📦 {eq_name}")
                            st.caption(f"{packed}/{total} 已放入" if total else "暂无物品")
                            if st.button("查看 →", key=f"open_{eq_name}", use_container_width=True):
                                go_detail(eq_name)

# ==================== 装备详情页 ====================
elif st.session_state.page == "detail":
    eq_name = st.session_state.selected_equipment

    if eq_name not in equipment_data:
        st.warning("该装备不存在，可能已被删除。")
        if st.button("⬅ 返回主页"):
            go_home()
        st.stop()

    items = equipment_data[eq_name]

    top_left, top_mid, top_right = st.columns([0.25, 0.5, 0.25])
    with top_left:
        if st.button("⬅ 返回主页", use_container_width=True):
            go_home()
    with top_mid:
        st.markdown(f"<h2 style='text-align:center'>📦 {eq_name}</h2>", unsafe_allow_html=True)
    with top_right:
        if st.button("✏️ 编辑物品" if not st.session_state.edit_items_mode else "✅ 完成编辑",
                     use_container_width=True):
            st.session_state.edit_items_mode = not st.session_state.edit_items_mode
            st.rerun()

    st.divider()

    if st.session_state.edit_items_mode:
        # ---------- 编辑模式：增删改物品 ----------
        st.markdown("#### ➕ 添加新物品")
        with st.form(f"add_item_form_{eq_name}", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([0.3, 0.2, 0.2, 0.3])
            with c1:
                i_name = st.text_input("物品名称")
            with c2:
                i_qty = st.text_input("数量")
            with c3:
                i_color = st.text_input("颜色")
            with c4:
                i_notes = st.text_input("备注")
            add_item_submitted = st.form_submit_button("添加物品", use_container_width=True)
            if add_item_submitted:
                if i_name.strip():
                    items.append({
                        "name": i_name.strip(),
                        "quantity": i_qty.strip(),
                        "color": i_color.strip(),
                        "notes": i_notes.strip(),
                        "checked": False
                    })
                    equipment_data[eq_name] = items
                    if safe_save(equipment_data):
                        st.rerun()
                else:
                    st.warning("请输入物品名称！")

        st.markdown("#### 📋 现有物品")
        if not items:
            st.info("这个装备里还没有物品。")
        else:
            def update_item_field(eq_name, index, field, widget_key):
                fresh_data = load_data()
                if eq_name in fresh_data and index < len(fresh_data[eq_name]):
                    fresh_data[eq_name][index][field] = st.session_state[widget_key]
                    save_data(fresh_data)

            item_to_delete = None
            for i, item in enumerate(items):
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([0.28, 0.15, 0.15, 0.27, 0.15])
                    with c1:
                        k = f"name_{eq_name}_{i}"
                        st.text_input("名称", value=item["name"], key=k,
                                     on_change=update_item_field, args=(eq_name, i, "name", k))
                    with c2:
                        k = f"qty_{eq_name}_{i}"
                        st.text_input("数量", value=item.get("quantity", ""), key=k,
                                     on_change=update_item_field, args=(eq_name, i, "quantity", k))
                    with c3:
                        k = f"color_{eq_name}_{i}"
                        st.text_input("颜色", value=item.get("color", ""), key=k,
                                     on_change=update_item_field, args=(eq_name, i, "color", k))
                    with c4:
                        k = f"notes_{eq_name}_{i}"
                        st.text_input("备注", value=item.get("notes", ""), key=k,
                                     on_change=update_item_field, args=(eq_name, i, "notes", k))
                    with c5:
                        st.write("")
                        if st.button("🗑️ 删除", key=f"del_item_{eq_name}_{i}", use_container_width=True):
                            item_to_delete = i

            if item_to_delete is not None:
                del items[item_to_delete]
                equipment_data[eq_name] = items
                if safe_save(equipment_data):
                    st.rerun()

    else:
        # ---------- 查看模式：勾选是否已放入 ----------
        if not items:
            st.info("这个装备里还没有物品。点击右上角「✏️ 编辑物品」来添加。")
        else:
            changed = False
            for i, item in enumerate(items):
                with st.container(border=True):
                    c1, c2 = st.columns([0.15, 0.85])
                    with c1:
                        is_checked = st.checkbox("已放入", value=item.get("checked", False),
                                                key=f"check_{eq_name}_{i}", label_visibility="visible")
                    with c2:
                        detail_bits = []
                        if item.get("quantity"):
                            detail_bits.append(f"数量：{item['quantity']}")
                        if item.get("color"):
                            detail_bits.append(f"颜色：{item['color']}")
                        if item.get("notes"):
                            detail_bits.append(f"备注：{item['notes']}")
                        detail_str = " | ".join(detail_bits)
                        st.markdown(f"**{item['name']}**")
                        if detail_str:
                            st.caption(detail_str)
                    if is_checked != item.get("checked", False):
                        item["checked"] = is_checked
                        changed = True
            if changed:
                equipment_data[eq_name] = items
                if safe_save(equipment_data):
                    st.rerun()
                    
