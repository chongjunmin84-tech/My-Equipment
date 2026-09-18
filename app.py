import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# 设置页面标题与布局
st.set_page_config(page_title="装备管理系统", page_icon="🎒", layout="wide")

st.title("🎒 装备管理系统 (云端同步版)")

# 建立 Google Sheets 连接
conn = st.connection("gsheets", type=GSheetsConnection)

# 从 Google Sheets 读取数据
def load_data():
    try:
        df = conn.read(ttl="0s") # ttl="0s" 确保每次都读取最新数据，不使用缓存
        if df.empty or "Equipment" not in df.columns or "Items" not in df.columns:
            return {}
        
        data = {}
        for _, row in df.iterrows():
            eq_name = str(row["Equipment"])
            try:
                items = json.loads(row["Items"]) if isinstance(row["Items"], str) else []
            except:
                items = []
            data[eq_name] = items
        return data
    except Exception as e:
        return {}

# 保存数据到 Google Sheets
def save_data(data):
    rows = []
    for eq_name, items in data.items():
        rows.append({
            "Equipment": eq_name,
            "Items": json.dumps(items, ensure_ascii=False)
        })
    df = pd.DataFrame(rows if rows else [{"Equipment": "", "Items": ""}])
    conn.update(data=df)

# 获取当前最新数据
equipment_data = load_data()

# 侧边栏：添加新装备
with st.sidebar:
    st.header("⚙️ 管理面板")
    new_eq = st.text_input("新增装备名称", placeholder="如：数码背包")
    if st.button("➕ 添加装备", use_container_width=True):
        if new_eq.strip():
            if new_eq not in equipment_data:
                equipment_data[new_eq] = []
                save_data(equipment_data)
                st.success(f"已成功添加装备：{new_eq}")
                st.rerun()
            else:
                st.warning("该装备已存在！")
        else:
            st.warning("请输入有效的装备名称！")

# 主界面：展示装备卡片
if not equipment_data:
    st.info("目前还没有任何装备，请在左侧边栏添加你的第一项装备！")
else:
    cols = st.columns(3)
    for index, (eq_name, items) in enumerate(list(equipment_data.items())):
        col = cols[index % 3]
        with col:
            with st.container(border=True):
                st.subheader(f"📦 {eq_name}")
                
                # 快速添加物品输入框
                quick_item = st.text_input(
                    "添加物品", 
                    key=f"input_{eq_name}", 
                    placeholder="输入物品名称后按 Enter"
                )
                if quick_item:
                    items.append({"name": quick_item, "checked": False})
                    equipment_data[eq_name] = items
                    save_data(equipment_data)
                    st.rerun()

                # 物品列表与勾选
                updated_items = []
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
                            continue # 跳过该物品即表示删除
                    
                    updated_items.append({"name": item["name"], "checked": is_checked})
                
                # 如果物品状态发生改变，更新数据
                if updated_items != items:
                    equipment_data[eq_name] = updated_items
                    save_data(equipment_data)
                    st.rerun()

                st.divider()
                
                # 删除整个装备按钮
                if st.button(f"🗑️ 删除装备 ({eq_name})", key=f"del_eq_{eq_name}", type="secondary", use_container_width=True):
                    del equipment_data[eq_name]
                    save_data(equipment_data)
                    st.success(f"已删除装备：{eq_name}")
                    st.rerun()