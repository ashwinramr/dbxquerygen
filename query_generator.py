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
        "table_name": ["my_table", "my_table", "my_table", "my_table"],
        "column_name": ["id", "name", "age", "address"],
        "data_type": ["int", "string", "int", "string"],
        "is_mandatory": ["yes", "yes", "no", "no"]
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        tables_df.to_excel(writer, sheet_name='tables', index=False)
        columns_df.to_excel(writer, sheet_name='columns', index=False)
    output.seek(0)
    return output

# --- Streamlit UI ---

st.title("Databricks Query Generator with Mandatory & Optional Fields")

with st.expander("ℹ️ How to Use the Databricks Query Generator"):
    st.markdown("""
    This tool helps you **generate valid SQL `INSERT` and `UPDATE` queries** for your Databricks tables using table metadata from an Excel file.

    ### ✅ Step 1 — Download the Template
    - Click the **“📥 Download Excel Template”** button below.
    - Open the downloaded `sample_metadata.xlsx`.
    - Fill in:
      - **Sheet `tables`:** Add your table names along with their catalog and schema.
      - **Sheet `columns`:** Add each column name, data type, and whether it is mandatory (yes/no).

    ### ✅ Step 2 — Upload Your Metadata
    - Upload your filled Excel file below.

    ### ✅ Step 3 — Generate Queries
    - Mandatory fields appear automatically.
    - Select any optional columns you want to include.
    - Click **Generate Insert Query** or **Generate Update Query**.
    - Download your generated queries as `.sql` files.

    ### 🎯 Features
    - 📦 Downloadable Excel template
    - 🛡️ SQL syntax validation
    - ⚙️ Optional parameterized queries
    - ✨ Supports mandatory/optional columns with not-null validation
    - 💾 Save generated queries
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

    # Get table columns and mandatory/optional status
    table_columns_df = columns_df[columns_df['table_name'] == selected_table]
    mandatory_columns = table_columns_df[table_columns_df['is_mandatory'].str.lower() == "yes"]['column_name'].tolist()
    optional_columns = table_columns_df[table_columns_df['is_mandatory'].str.lower() == "no"]['column_name'].tolist()

    # Parameterized toggle
    param_mode = st.checkbox("🔧 Generate Parameterized Query (use '?' instead of values)", value=False)

    st.markdown("#### Mandatory Fields")
    insert_values = []
    for col in mandatory_columns:
        val = st.text_input(f"Value for {col} (Mandatory)", key=f"insert_{col}")
        insert_values.append(val)

    st.markdown("#### Optional Fields")
    selected_optional_cols = st.multiselect("Select optional columns to include", optional_columns, key="optional_cols")

    optional_values = []
    for col in selected_optional_cols:
        val = st.text_input(f"Value for {col} (Optional)", key=f"insert_optional_{col}")
        optional_values.append(val)

    final_columns = mandatory_columns + selected_optional_cols
    final_values = insert_values + optional_values

    if st.button("Generate Insert Query"):
        # Not null check for mandatory fields
        missing_fields = [col for col, val in zip(mandatory_columns, insert_values) if not val.strip()]
        if missing_fields:
            st.error(f"🚨 Mandatory fields missing values: {', '.join(missing_fields)}")
        else:
            insert_query = build_insert_query(catalog, schema, selected_table, final_columns, final_values, param_mode=param_mode)
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

    st.subheader("Update Query")
    st.markdown("#### Select Columns to Update")
    update_columns = st.multiselect("Columns to Update", final_columns, key="update_cols")
    update_values = []
    for col in update_columns:
        val = st.text_input(f"Value for {col} (Update)", key=f"update_{col}")
        update_values.append(val)

    where_column = st.selectbox("WHERE Column", final_columns, key="where_col")
    where_value = st.text_input(f"Value for {where_column} (WHERE)", key="where_val")

    if st.button("Generate Update Query"):
        update_query = build_update_query(catalog, schema, selected_table, update_columns, update_values, where_column, where_value, param_mode=param_mode)
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
