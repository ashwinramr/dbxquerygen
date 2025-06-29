import streamlit as st
import pandas as pd

# --- Helper functions ---

def load_table_info(excel_file):
    # Expecting sheets: 'tables', 'columns'
    tables_df = pd.read_excel(excel_file, sheet_name='tables')
    columns_df = pd.read_excel(excel_file, sheet_name='columns')
    return tables_df, columns_df

def build_insert_query(catalog, schema, table, columns, values):
    cols = ", ".join(columns)
    vals = ", ".join([f"'{v}'" for v in values])
    query = f"INSERT INTO {catalog}.{schema}.{table} ({cols}) VALUES ({vals});"
    return query

def build_update_query(catalog, schema, table, set_columns, set_values, where_column, where_value):
    set_expr = ", ".join([f"{col}='{val}'" for col, val in zip(set_columns, set_values)])
    query = f"UPDATE {catalog}.{schema}.{table} SET {set_expr} WHERE {where_column}='{where_value}';"
    return query

# --- Streamlit UI ---

st.title("Databricks Query Generator")

uploaded_file = st.file_uploader("Upload Excel with Table & Column Metadata", type="xlsx")
if uploaded_file:
    tables_df, columns_df = load_table_info(uploaded_file)
    
    # --- Table Selection ---
    selected_table = st.selectbox("Select Table", tables_df['table_name'].unique())
    table_info = tables_df[tables_df['table_name'] == selected_table].iloc[0]
    
    catalog = st.text_input("Catalog", value=table_info['catalog_name'])
    schema = st.text_input("Schema", value=table_info['schema_name'])
    
    # --- Columns for Insert ---
    table_columns = columns_df[columns_df['table_name'] == selected_table]['column_name'].tolist()
    st.subheader("Insert Query")
    insert_values = []
    for col in table_columns:
        val = st.text_input(f"Value for {col} (Insert)", key=f"insert_{col}")
        insert_values.append(val)
    
    if st.button("Generate Insert Query"):
        insert_query = build_insert_query(catalog, schema, selected_table, table_columns, insert_values)
        st.code(insert_query, language='sql')
    
    # --- Columns for Update ---
    st.subheader("Update Query")
    set_columns = st.multiselect("Columns to Update", table_columns, key="update_cols")
    set_values = []
    for col in set_columns:
        val = st.text_input(f"Value for {col} (Update)", key=f"update_{col}")
        set_values.append(val)
    
    where_column = st.selectbox("WHERE Column", table_columns, key="where_col")
    where_value = st.text_input(f"Value for {where_column} (WHERE)", key="where_val")
    
    if st.button("Generate Update Query"):
        update_query = build_update_query(catalog, schema, selected_table, set_columns, set_values, where_column, where_value)
        st.code(update_query, language='sql')
else:
    st.info("Please upload an Excel file with sheets named 'tables' and 'columns'.")
