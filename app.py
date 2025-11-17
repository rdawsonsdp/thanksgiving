#!/usr/bin/env python3
"""
Interactive Sales Dashboard Web Application
View and filter order information from Google Sheets
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Google Sheets configuration
SPREADSHEET_ID = "1YAHO5rHhFVEReyAuxa7r2SDnoH7BnDfsmSEZ1LyjB8A"
CUSTOMER_ORDERS_SHEET_NAME = "Customer Orders"
BAKERY_PRODUCTS_SHEET_NAME = "Bakery Products Ordered "  # Note: trailing space

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data():
    """
    Load data from Google Sheets and merge orders with products.
    """
    try:
        creds = Credentials.from_service_account_file(
            "long-canto-360620-6858c5a01c13.json", 
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        
        # Read Customer Orders
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        orders_sheet = spreadsheet.worksheet(CUSTOMER_ORDERS_SHEET_NAME)
        customer_orders_data = orders_sheet.get_all_records()
        customer_orders_df = pd.DataFrame(customer_orders_data)
        
        # Read Bakery Products
        products_sheet = spreadsheet.worksheet(BAKERY_PRODUCTS_SHEET_NAME)
        bakery_products_data = products_sheet.get_all_records()
        bakery_products_df = pd.DataFrame(bakery_products_data)
        
        # Ensure date columns are read as strings/text
        date_columns = ['Order Date', 'Due Pickup Date', 'Pickup Timestamp', 'Due Date']
        for col in date_columns:
            if col in customer_orders_df.columns:
                customer_orders_df[col] = customer_orders_df[col].astype(str).replace('nan', '')
            if col in bakery_products_df.columns:
                bakery_products_df[col] = bakery_products_df[col].astype(str).replace('nan', '')
        
        # Parse dates from text
        customer_orders_df = parse_dates(customer_orders_df)
        bakery_products_df = parse_dates(bakery_products_df)
        
        # Merge data
        if 'OrderID' in customer_orders_df.columns and 'OrderID' in bakery_products_df.columns:
            customer_orders_df['OrderID'] = customer_orders_df['OrderID'].astype(str).str.strip().str.upper()
            bakery_products_df['OrderID'] = bakery_products_df['OrderID'].astype(str).str.strip().str.upper()
            
            merged_df = pd.merge(
                customer_orders_df,
                bakery_products_df,
                on='OrderID',
                how='left',
                suffixes=('_order', '_item')
            )
        else:
            merged_df = customer_orders_df
        
        return customer_orders_df, bakery_products_df, merged_df
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def parse_dates(df):
    """
    Parse date columns from text, handling multiple formats.
    """
    df = df.copy()
    
    # Parse Order Date - convert from text to datetime
    if 'Order Date' in df.columns:
        # Convert to string first, handle empty values
        df['Order Date'] = df['Order Date'].astype(str).replace(['nan', 'None', ''], '')
        # First try MM-DD-YYYY format (most common)
        df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce', format='%m-%d-%Y')
        # For any that didn't parse, try M/D/YYYY format
        mask_not_parsed = df['Order Date'].isna()
        if mask_not_parsed.any():
            df.loc[mask_not_parsed, 'Order Date'] = pd.to_datetime(
                df.loc[mask_not_parsed, 'Order Date'], 
                errors='coerce', 
                format='%m/%d/%Y'
            )
        # For any still not parsed, try default parsing
        mask_still_not_parsed = df['Order Date'].isna()
        if mask_still_not_parsed.any():
            df.loc[mask_still_not_parsed, 'Order Date'] = pd.to_datetime(
                df.loc[mask_still_not_parsed, 'Order Date'], 
                errors='coerce', 
                dayfirst=False, 
                yearfirst=False
            )
    
    # Parse Due Pickup Date - convert from text to datetime
    if 'Due Pickup Date' in df.columns:
        df['Due Pickup Date'] = df['Due Pickup Date'].astype(str).replace(['nan', 'None', ''], '')
        # First try MM-DD-YYYY format
        df['Due Pickup Date'] = pd.to_datetime(df['Due Pickup Date'], errors='coerce', format='%m-%d-%Y')
        # For any that didn't parse, try M/D/YYYY format
        mask_not_parsed = df['Due Pickup Date'].isna()
        if mask_not_parsed.any():
            df.loc[mask_not_parsed, 'Due Pickup Date'] = pd.to_datetime(
                df.loc[mask_not_parsed, 'Due Pickup Date'], 
                errors='coerce', 
                format='%m/%d/%Y'
            )
        # For any still not parsed, try default parsing
        mask_still_not_parsed = df['Due Pickup Date'].isna()
        if mask_still_not_parsed.any():
            df.loc[mask_still_not_parsed, 'Due Pickup Date'] = pd.to_datetime(
                df.loc[mask_still_not_parsed, 'Due Pickup Date'], 
                errors='coerce', 
                dayfirst=False, 
                yearfirst=False
            )
    
    # Parse Pickup Timestamp - convert from text to datetime
    if 'Pickup Timestamp' in df.columns:
        df['Pickup Timestamp'] = df['Pickup Timestamp'].astype(str).replace(['nan', 'None', ''], '')
        df['Pickup Timestamp'] = pd.to_datetime(df['Pickup Timestamp'], errors='coerce', dayfirst=False, yearfirst=False)
    
    # Parse Due Date if it exists
    if 'Due Date' in df.columns:
        df['Due Date'] = df['Due Date'].astype(str).replace(['nan', 'None', ''], '')
        df['Due Date'] = pd.to_datetime(df['Due Date'], errors='coerce', format='%m-%d-%Y')
        mask_not_parsed = df['Due Date'].isna()
        if mask_not_parsed.any():
            df.loc[mask_not_parsed, 'Due Date'] = pd.to_datetime(
                df.loc[mask_not_parsed, 'Due Date'], 
                errors='coerce', 
                format='%m/%d/%Y'
            )
    
    return df


def filter_data(df, date_start=None, date_end=None, product_filter=None, pickup_date_start=None, pickup_date_end=None):
    """
    Apply filters to the dataframe.
    """
    filtered_df = df.copy()
    
    # Filter by Order Date
    if date_start and 'Order Date' in filtered_df.columns:
        start_date = pd.Timestamp(date_start).normalize()
        filtered_df = filtered_df[filtered_df['Order Date'].notna() & (filtered_df['Order Date'] >= start_date)]
    if date_end and 'Order Date' in filtered_df.columns:
        # Include full end date
        end_date = pd.Timestamp(date_end).normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        filtered_df = filtered_df[filtered_df['Order Date'].notna() & (filtered_df['Order Date'] <= end_date)]
    
    # Filter by Product Description
    if product_filter and product_filter != 'All Products':
        if 'Product Description' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Product Description'].str.contains(product_filter, case=False, na=False)]
    
    # Filter by Pickup Date
    if pickup_date_start and 'Due Pickup Date' in filtered_df.columns:
        start_date = pd.Timestamp(pickup_date_start).normalize()
        filtered_df = filtered_df[filtered_df['Due Pickup Date'].notna() & (filtered_df['Due Pickup Date'] >= start_date)]
    if pickup_date_end and 'Due Pickup Date' in filtered_df.columns:
        # Include full end date
        end_date = pd.Timestamp(pickup_date_end).normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        filtered_df = filtered_df[filtered_df['Due Pickup Date'].notna() & (filtered_df['Due Pickup Date'] <= end_date)]
    
    return filtered_df


def main():
    """
    Main application function.
    """
    # Title
    st.title("📊 Sales Dashboard")
    st.markdown("Interactive order information viewer with filtering capabilities")
    
    # Load data
    with st.spinner("Loading data from Google Sheets..."):
        customer_orders_df, bakery_products_df, merged_df = load_data()
    
    if merged_df.empty:
        st.error("No data loaded. Please check your credentials and Google Sheet access.")
        return
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Order Date filter
    st.sidebar.subheader("Order Date Range")
    if 'Order Date' in merged_df.columns and merged_df['Order Date'].notna().any():
        min_order_date = merged_df['Order Date'].min().date()
        max_order_date = merged_df['Order Date'].max().date()
        
        date_start = st.sidebar.date_input(
            "Start Date",
            value=min_order_date,
            min_value=min_order_date,
            max_value=max_order_date
        )
        date_end = st.sidebar.date_input(
            "End Date",
            value=max_order_date,
            min_value=min_order_date,
            max_value=max_order_date
        )
    else:
        date_start = None
        date_end = None
        st.sidebar.info("No Order Date data available")
    
    # Product filter
    st.sidebar.subheader("Product Filter")
    if 'Product Description' in merged_df.columns:
        products = ['All Products'] + sorted(merged_df['Product Description'].dropna().unique().tolist())
        selected_product = st.sidebar.selectbox(
            "Select Product",
            options=products,
            index=0
        )
    else:
        selected_product = 'All Products'
        st.sidebar.info("No Product Description data available")
    
    # Pickup Date filter
    st.sidebar.subheader("Pickup Date Range")
    if 'Due Pickup Date' in merged_df.columns and merged_df['Due Pickup Date'].notna().any():
        min_pickup_date = merged_df['Due Pickup Date'].min().date()
        max_pickup_date = merged_df['Due Pickup Date'].max().date()
        
        pickup_date_start = st.sidebar.date_input(
            "Pickup Start Date",
            value=min_pickup_date,
            min_value=min_pickup_date,
            max_value=max_pickup_date,
            key='pickup_start'
        )
        pickup_date_end = st.sidebar.date_input(
            "Pickup End Date",
            value=max_pickup_date,
            min_value=min_pickup_date,
            max_value=max_pickup_date,
            key='pickup_end'
        )
    else:
        pickup_date_start = None
        pickup_date_end = None
        st.sidebar.info("No Pickup Date data available")
    
    # Apply filters
    filtered_df = filter_data(
        merged_df,
        date_start=date_start,
        date_end=date_end,
        product_filter=selected_product,
        pickup_date_start=pickup_date_start,
        pickup_date_end=pickup_date_end
    )
    
    # Summary statistics
    st.header("📈 Summary Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_orders = len(filtered_df['OrderID'].unique()) if 'OrderID' in filtered_df.columns else 0
        st.metric("Total Orders", f"{total_orders:,}")
    
    with col2:
        total_items = len(filtered_df)
        st.metric("Total Line Items", f"{total_items:,}")
    
    with col3:
        if 'Subtotal (Calculated)' in filtered_df.columns:
            total_revenue = pd.to_numeric(filtered_df['Subtotal (Calculated)'], errors='coerce').sum()
            st.metric("Total Revenue", f"${total_revenue:,.2f}")
        else:
            st.metric("Total Revenue", "$0.00")
    
    with col4:
        if 'Total' in filtered_df.columns:
            order_total = pd.to_numeric(filtered_df.groupby('OrderID')['Total'].first(), errors='coerce').sum()
            st.metric("Order Total", f"${order_total:,.2f}")
        else:
            st.metric("Order Total", "$0.00")
    
    st.divider()
    
    # Charts section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Sales by Category")
        if 'Category' in filtered_df.columns:
            category_sales = filtered_df.groupby('Category').agg({
                'Subtotal (Calculated)': 'sum'
            }).reset_index()
            category_sales['Subtotal (Calculated)'] = pd.to_numeric(
                category_sales['Subtotal (Calculated)'], 
                errors='coerce'
            )
            category_sales = category_sales.sort_values('Subtotal (Calculated)', ascending=False)
            
            fig_category = px.bar(
                category_sales,
                x='Category',
                y='Subtotal (Calculated)',
                title="Revenue by Category",
                labels={'Subtotal (Calculated)': 'Revenue ($)', 'Category': 'Category'}
            )
            fig_category.update_xaxes(tickangle=45)
            st.plotly_chart(fig_category, use_container_width=True)
        else:
            st.info("No category data available")
    
    with col2:
        st.subheader("Sales by Order Type")
        if 'Order Type ' in filtered_df.columns:
            order_type_sales = filtered_df.groupby('Order Type ').agg({
                'Total': 'sum'
            }).reset_index()
            order_type_sales['Total'] = pd.to_numeric(order_type_sales['Total'], errors='coerce')
            order_type_sales = order_type_sales.sort_values('Total', ascending=False)
            
            fig_order_type = px.pie(
                order_type_sales,
                values='Total',
                names='Order Type ',
                title="Revenue by Order Type"
            )
            st.plotly_chart(fig_order_type, use_container_width=True)
        else:
            st.info("No order type data available")
    
    # Daily sales trend
    st.subheader("Daily Sales Trend")
    if 'Order Date' in filtered_df.columns and filtered_df['Order Date'].notna().any():
        daily_sales = filtered_df.groupby(filtered_df['Order Date'].dt.date).agg({
            'Subtotal (Calculated)': 'sum',
            'OrderID': 'nunique'
        }).reset_index()
        daily_sales['Subtotal (Calculated)'] = pd.to_numeric(
            daily_sales['Subtotal (Calculated)'], 
            errors='coerce'
        )
        daily_sales.columns = ['Date', 'Revenue', 'Orders']
        daily_sales = daily_sales.sort_values('Date')
        
        fig_trend = px.line(
            daily_sales,
            x='Date',
            y='Revenue',
            title="Daily Revenue Trend",
            labels={'Revenue': 'Revenue ($)', 'Date': 'Date'},
            markers=True
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("No date data available for trend analysis")
    
    st.divider()
    
    # Data table
    st.header("📋 Order Details")
    
    # Select columns to display
    display_columns = [
        'Order Date', 'OrderID', 'Customer First Name', 'Customer Last Name',
        'Product Description', 'Category', 'Unit Price', 'Subtotal (Calculated)',
        'Due Pickup Date', 'Due Pickup Time', 'Order Type ', 'Total'
    ]
    
    available_columns = [col for col in display_columns if col in filtered_df.columns]
    
    if available_columns:
        display_df = filtered_df[available_columns].copy()
        
        # Format numeric columns
        numeric_cols = ['Unit Price', 'Subtotal (Calculated)', 'Total']
        for col in numeric_cols:
            if col in display_df.columns:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce')
                display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
        
        # Format dates
        date_cols = ['Order Date', 'Due Pickup Date']
        for col in date_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].dt.strftime('%Y-%m-%d') if display_df[col].dtype == 'datetime64[ns]' else display_df[col]
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=400
        )
        
        # Download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv,
            file_name=f"orders_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("No displayable columns found in filtered data")
    
    # Footer
    st.divider()
    st.caption(f"Data loaded: {len(merged_df):,} total records | Filtered: {len(filtered_df):,} records")


if __name__ == "__main__":
    main()

