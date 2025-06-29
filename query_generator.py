import streamlit as st
import pandas as pd
import sqlparse
import io

# --- Helper functions ---

def load_table_info(excel_file):
    tables_df = pd.read_excel(excel_file, sheet_name='tables')
    columns_df = pd.read_excel(excel_file, sheet_name='columns')
    return tables_df, columns_df

def build_insert_query(catalog, schema, table, columns, values, param_mode=False):
    cols = ", ".join(columns)
    if param_mode:
        vals = ", ".join(["?" for _ in values])
    else:
        vals = ", ".join([f"'{v}'" for v in values])
    query = f"INSERT INTO {catalog}.{schema}.{table} ({cols}) VALUES ({vals});"
    return query

def build_update_query(catalog, schema, table, set_columns, set_values, where_column, where_value, param_mode=False):
    if param_mode:
        set_expr = ", ".join([f"{col}=?" for col in set_columns])
        where_expr = f"{where_column}=?"
    else:
        set_expr = ", ".join([f"{col}='{val}'" for col, val in zip(set_columns, set_values)])
        where_expr = f"{where_column}='{where_value}'"
    query = f"UPDATE {catalog}.{schema}.{table} SET {set_expr} WHERE {where_expr};"
    return query

def is_valid_sql(query: str) -> bool:
    try:
        parsed = sqlparse.parse(query)
        return bool(parsed) and all(token.is_group for token in parsed)
    except Exception as e:
        st.error(f"SQL validation error: {e}")
        return False

def generate_sample_excel():
    tables_df = pd.DataFrame({
        "table_name": ["my_table"],
        "catalog_name": ["my_catalog"],
        "schema_name": ["my_schema"]
    })
    columns_df = pd.DataFrame({
        "table_name": ["my_table", "my_table"],
        "column_name": ["id", "name"],
        "data_type": ["int", "string"]
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        tables_df.to_excel(writer, sheet_name='tables', index=False)
        columns_df.to_excel(writer, sheet_name='columns', index=False)
    output.seek(0)
    return output

# --- Streamlit UI ---

st.title("Databricks Query Generator with SQL Validation & Parameterization")

with st.expander("ℹ️ How to Use the Databricks Query Generator"):
    st.markdown("""
    This tool helps you **generate valid SQL `INSERT` and `UPDATE` queries** for your Databricks tables using table metadata from an Excel file.

    ### ✅ Step 1 — Download the Template
    - Click the **“📥 Download Excel Template”** button below.
    - Open the downloaded `sample_metadata.xlsx`.
    - Fill in:
      - **Sheet `tables`:** Add your table names along with their catalog and schema.
      - **Sheet `columns`:** For each table, list the columns you plan to use, including column names and data types.

    ### ✅ Step 2 — Upload Your Metadata
    - Upload your filled Excel file by clicking **Upload Excel with Table & Column Metadata**.
    - The app will read your tables and columns.

    ### ✅ Step 3 — Generate Queries
    1. Select your table from the dropdown.
    2. Confirm or edit the **Catalog** and **Schema** fields.
    3. For **INSERT Queries**:
       - Enter values for each column.
       - Click **Generate Insert Query**.
       - The app will validate and display your SQL query.
    4. For **UPDATE Queries**:
       - Select columns to update and provide new values.
       - Choose the column and value for the `WHERE` clause.
       - Click **Generate Update Query**.
       - The app will validate and display your SQL query.

    ### ✅ Step 4 — Validate and Save Your Queries
    - If validation passes ✅, you’ll see your SQL query with syntax highlighting.
    - Download the query as a `.sql` file for reuse in ETL or scripts.

    ### 🎯 Key Features
    - 📦 Downloadable Excel template
    - 🔎 SQL syntax validation
    - ⚙️ Support for parameterized queries with `?` placeholders
    - 💾 Save queries as .sql files
    - 🎨 User-friendly web interface
    """)

excel_template = generate_sample_excel()
st.download_button(
    label="📥 Download Excel Template",
    data=excel_template,
    file_name="sample_metadata.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

uploaded_file = st.file_uploader("Upload Excel with Table & Column Metadata", type="xlsx")

if uploaded_file:
    tables_df, columns_df = load_table_info(uploaded_file)

    selected_table = st.selectbox("Select Table", tables_df['table_name'].unique())
    table_info = tables_df[tables_df['table_name'] == selected_table].iloc[0]

    catalog = st.text_input("Catalog", value=table_info['catalog_name'])
    schema = st.text_input("Schema", value=table_info['schema_name'])

    table_columns = columns_df[columns_df['table_name'] == selected_table]['column_name'].tolist()

    # --- Parameterized toggle ---
    param_mode = st.checkbox("🔧 Generate Parameterized Query (use '?' instead of values)", value=False)

    # --- Insert Query ---
    st.subheader("Insert Query")
    insert_values = []
    for col in table_columns:
        val = st.text_input(f"Value for {col} (Insert)", key=f"insert_{col}")
        insert_values.append(val)

    if st.button("Generate Insert Query"):
        insert_query = build_insert_query(catalog, schema, selected_table, table_columns, insert_values, param_mode=param_mode)
        if is_valid_sql(insert_query):
            st.success("✅ SQL syntax looks valid!")
            st.code(insert_query, language='sql')
            st.download_button(
                label="💾 Download Query as .sql",
                data=insert_query.encode('utf-8'),
                file_name=f"{selected_table}_insert.sql",
                mime="text/sql",
            )
        else:
            st.error("❌ Generated INSERT query is invalid!")

    # --- Update Query ---
    st.subheader("Update Query")
    set_columns = st.multiselect("Columns to Update", table_columns, key="update_cols")
    set_values = []
    for col in set_columns:
        val = st.text_input(f"Value for {col} (Update)", key=f"update_{col}")
        set_values.append(val)

    where_column = st.selectbox("WHERE Column", table_columns, key="where_col")
    where_value = st.text_input(f"Value for {where_column} (WHERE)", key="where_val")

    if st.button("Generate Update Query"):
        update_query = build_update_query(catalog, schema, selected_table, set_columns, set_values, where_column, where_value, param_mode=param_mode)
        if is_valid_sql(update_query):
            st.success("✅ SQL syntax looks valid!")
            st.code(update_query, language='sql')
            st.download_button(
                label="💾 Download Query as .sql",
                data=update_query.encode('utf-8'),
                file_name=f"{selected_table}_update.sql",
                mime="text/sql",
            )
        else:
            st.error("❌ Generated UPDATE query is invalid!")
else:
    st.info("Please upload an Excel file with sheets named 'tables' and 'columns'.")
