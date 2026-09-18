import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

st.set_page_config(page_title="装备管理系统", page_icon="🎒", layout="wide")
st.title("🎒 装备管理系统 (云端同步版)")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(ttl="0s")
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

# 关键改动：不再静默吞掉错误，直接在页面上显示
try:
    equipment_data = load_data()
except Exception as e:
    st.error(f"读取 Google Sheet 失败：{e}")
    st.stop()

with st.sidebar:
    st.header("⚙️ 管理面板")
    with st.form("add_equipment_form", clear_on_submit=True):
        new_eq = st.text_input("新增装备名称", placeholder="如：数码背包")
        submitted = st.form_submit_button("➕ 添加装备", use_container_width=True)
        if submitted:
            if new_eq.strip():
                if new_eq not in equipment_data:
                    equipment_data[new_eq] = []
                    try:
                        save_data(equipment_data)
                        st.success(f"已成功添加装备：{new_eq}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存失败：{e}")
                else:
                    st.warning("该装备已存在！")
            else:
                st.warning("请输入有效的装备名称！")

if not equipment_data:
    st.info("目前还没有任何装备，请在左侧边栏添加你的第一项装备！")
else:
    cols = st.columns(3)
    for index, (eq_name, items) in enumerate(list(equipment_data.items())):
        col = cols[index % 3]
        with col:
            with st.container(border=True):
                st.subheader(f"📦 {eq_name}")

                # 用 form 包住，加了 clear_on_submit，避免重复触发
                with st.form(key=f"form_{eq_name}", clear_on_submit=True):
                    quick_item = st.text_input(
                        "添加物品",
                        key=f"input_{eq_name}",
                        placeholder="输入物品名称后按 Enter"
                    )
                    add_item_submitted = st.form_submit_button("添加")
                    if add_item_submitted and quick_item.strip():
                        items.append({"name": quick_item.strip(), "checked": False})
                        equipment_data[eq_name] = items
                        try:
                            save_data(equipment_data)
                            st.rerun()
                        except Exception as e:
                            st.error(f"保存物品失败：{e}")

                updated_items = []
                item_to_delete = None
                for i, item in enumerate(items):
                    item_col1, item_col2 = st.columns([0.85, 0.15])
                    with item_col1:
                        is_checked = st.checkbox(
                            item["name"],
                            value=item.get("checked", False),
                            key=f"check_{eq_name}_{i}"
                        )
                    with item_col2:
                        if st.button("❌", key=f"del_item_{eq_name}_{i}"):
                            item_to_delete = i

                    if item_to_delete != i:
                        updated_items.append({"name": item["name"], "checked": is_checked})

                if item_to_delete is not None:
                    equipment_data[eq_name] = updated_items
                    try:
                        save_data(equipment_data)
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除物品失败：{e}")
                elif updated_items != items:
                    equipment_data[eq_name] = updated_items
                    try:
                        save_data(equipment_data)
                        st.rerun()
                    except Exception as e:
                        st.error(f"更新状态失败：{e}")

                st.divider()

                if st.button(f"🗑️ 删除装备 ({eq_name})", key=f"del_eq_{eq_name}", type="secondary", use_container_width=True):
                    del equipment_data[eq_name]
                    try:
                        save_data(equipment_data)
                        st.success(f"已删除装备：{eq_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除装备失败：{e}")
