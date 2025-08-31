import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from gst_matcher import GSTMatcher
import io
import base64

st.set_page_config(
    page_title="GST Invoice Matcher",
    page_icon="📊",
    layout="wide"
)

def download_excel(df_matched, df_unmatched, filename="gst_results.xlsx"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_matched.to_excel(writer, sheet_name='Matched', index=False)
        df_unmatched.to_excel(writer, sheet_name='Unmatched', index=False)
    
    b64 = base64.b64encode(output.getvalue()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">Download Results</a>'
    return href

def main():
    st.title("🧾 GST Invoice Matcher")
    st.markdown("Match company invoices with portal data")
    
    st.sidebar.header("Configuration")
    buffer_size = st.sidebar.number_input("Buffer Size (₹)", min_value=0.0, value=0.0, step=1.0)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Company Data")
        company_file = st.file_uploader("Upload Company Excel", type=['xlsx', 'xls'], key="company")
        
    with col2:
        st.subheader("Portal Data")
        portal_file = st.file_uploader("Upload Portal Excel", type=['xlsx', 'xls'], key="portal")
    
    if company_file and portal_file:
        try:
            matcher = GSTMatcher()
            
            with st.spinner("Loading data..."):
                company_df, portal_df = matcher.load_data(company_file, portal_file)
            
            st.success(f"✅ Loaded {len(company_df)} company records and {len(portal_df)} portal records")
            
            if st.button("🔍 Start Matching", type="primary"):
                with st.spinner("Matching invoices..."):
                    matched_records, unmatched_records = matcher.match_invoices(
                        company_df, portal_df, buffer_size
                    )
                
                matched_df = pd.DataFrame(matched_records)
                unmatched_df = pd.DataFrame(unmatched_records)
                
                total_records = len(company_df)
                matched_count = len(matched_records)
                unmatched_count = len(unmatched_records)
                
                st.header("📈 Results Summary")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Records", total_records)
                col2.metric("Matched", matched_count, f"{(matched_count/total_records*100):.1f}%")
                col3.metric("Unmatched", unmatched_count, f"{(unmatched_count/total_records*100):.1f}%")
                col4.metric("Match Rate", f"{(matched_count/total_records*100):.1f}%")
                
                fig = go.Figure(data=[
                    go.Bar(name='Matched', x=['Results'], y=[matched_count], marker_color='green'),
                    go.Bar(name='Unmatched', x=['Results'], y=[unmatched_count], marker_color='red')
                ])
                fig.update_layout(title="Matching Results", barmode='stack', height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                if not matched_df.empty:
                    st.subheader("✅ Matched Records")
                    
                    match_type_counts = matched_df['Match Status'].value_counts()
                    fig_pie = px.pie(values=match_type_counts.values, names=match_type_counts.index, 
                                   title="Match Types Distribution")
                    st.plotly_chart(fig_pie, use_container_width=True)
                    
                    if st.checkbox("Show Matched Details"):
                        st.dataframe(matched_df, use_container_width=True)
                
                if not unmatched_df.empty:
                    st.subheader("❌ Unmatched Records")
                    if st.checkbox("Show Unmatched Details"):
                        st.dataframe(unmatched_df, use_container_width=True)
                
                st.subheader("📥 Download Results")
                download_link = download_excel(matched_df, unmatched_df)
                st.markdown(download_link, unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Please check your file format and column names")
    
    with st.sidebar:
        st.subheader("📋 Required Columns")
        st.write("**Company Data:**")
        st.text("• GSTIN of supplier\n• Party Name\n• Accounting Document No\n• Invoice No\n• Invoice Date\n• CGST Amount\n• SGST Amount\n• IGST Amount")
        
        st.write("**Portal Data:**")
        st.text("• GSTIN of supplier\n• Invoice number\n• Invoice Date\n• Central Tax(₹)\n• State/UT Tax(₹)\n• Integrated Tax(₹)")

if __name__ == "__main__":
    main()