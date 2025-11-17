#!/usr/bin/env python3
"""
Sales Report Generator from Google Sheets
Reads Customer Orders and Bakery Products Ordered sheets and generates a sales report.
"""

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date
import json
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Google Sheets configuration
SPREADSHEET_ID = "1YAHO5rHhFVEReyAuxa7r2SDnoH7BnDfsmSEZ1LyjB8A"
CUSTOMER_ORDERS_SHEET_NAME = "Customer Orders"
BAKERY_PRODUCTS_SHEET_NAME = "Bakery Products Ordered "  # Note: trailing space

# Service account credentials (you'll need to set up a JSON key file)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]


def authenticate_google_sheets(credentials_path=None):
    """
    Authenticate with Google Sheets API using service account credentials.
    
    Args:
        credentials_path: Path to JSON credentials file. If None, looks for 'long-canto-360620-6858c5a01c13.json'
    
    Returns:
        gspread Client object
    """
    if credentials_path is None:
        credentials_path = "long-canto-360620-6858c5a01c13.json"
    
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"Credentials file not found at {credentials_path}. "
            "Please ensure the service account JSON key file is in the current directory."
        )
    
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client


def read_sheet_data(client, sheet_name):
    """
    Read data from a specific sheet in the spreadsheet.
    
    Args:
        client: gspread Client object
        sheet_name: Name of the sheet to read
    
    Returns:
        pandas DataFrame with the sheet data (date columns as text)
    """
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet(sheet_name)
        
        # Get all values
        data = sheet.get_all_records()
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Ensure date columns are read as strings/text
        date_columns = ['Order Date', 'Due Pickup Date', 'Pickup Timestamp', 'Due Date']
        for col in date_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).replace('nan', '')
        
        print(f"✓ Successfully read {len(df)} rows from '{sheet_name}'")
        return df
    
    except gspread.exceptions.WorksheetNotFound:
        print(f"✗ Sheet '{sheet_name}' not found")
        return pd.DataFrame()
    except Exception as e:
        print(f"✗ Error reading sheet '{sheet_name}': {str(e)}")
        return pd.DataFrame()


def generate_sales_report(customer_orders_df, bakery_products_df):
    """
    Generate a comprehensive sales report from the two dataframes.
    
    Args:
        customer_orders_df: DataFrame with customer orders
        bakery_products_df: DataFrame with bakery products ordered
    
    Returns:
        Dictionary containing various report metrics
    """
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {},
        "details": {}
    }
    
    # Basic summary
    report["summary"]["total_customer_orders"] = len(customer_orders_df)
    report["summary"]["total_line_items"] = len(bakery_products_df)
    
    # Try to identify common column names for order ID/key
    order_id_col = None
    for col in customer_orders_df.columns:
        if col.lower() == 'orderid':
            order_id_col = col
            break
    
    # If not found, try broader search
    if not order_id_col:
        for col in customer_orders_df.columns:
            if any(keyword in col.lower() for keyword in ['order', 'id', 'key', 'number']):
                order_id_col = col
                break
    
    # Merge data if we can find a common key
    merged_df = None
    if order_id_col and order_id_col in bakery_products_df.columns:
        try:
            # Convert OrderID to string for both dataframes to ensure matching
            customer_orders_df = customer_orders_df.copy()
            bakery_products_df = bakery_products_df.copy()
            customer_orders_df[order_id_col] = customer_orders_df[order_id_col].astype(str).str.strip().str.upper()
            bakery_products_df[order_id_col] = bakery_products_df[order_id_col].astype(str).str.strip().str.upper()
            
            merged_df = pd.merge(
                customer_orders_df,
                bakery_products_df,
                on=order_id_col,
                how='inner',
                suffixes=('_order', '_item')
            )
            report["summary"]["matched_orders"] = len(merged_df.groupby(order_id_col))
            report["summary"]["matched_line_items"] = len(merged_df)
        except Exception as e:
            merged_df = None
            report["summary"]["matched_orders"] = f"Error matching: {str(e)}"
    else:
        report["summary"]["matched_orders"] = "Unable to match (no common order ID found)"
    
    # Try to find amount/price columns
    amount_cols = []
    for col in bakery_products_df.columns:
        if any(keyword in col.lower() for keyword in ['amount', 'price', 'cost', 'total', 'value']):
            amount_cols.append(col)
    
    if amount_cols:
        for col in amount_cols:
            try:
                # Convert to numeric, handling any string values
                numeric_values = pd.to_numeric(bakery_products_df[col], errors='coerce')
                total = numeric_values.sum()
                if pd.notna(total):
                    report["summary"][f"total_{col.lower().replace(' ', '_')}"] = float(total)
            except:
                pass
    
    # Try to find quantity columns
    qty_cols = []
    for col in bakery_products_df.columns:
        if any(keyword in col.lower() for keyword in ['quantity', 'qty', 'amount', 'count']):
            qty_cols.append(col)
    
    if qty_cols:
        for col in qty_cols:
            try:
                numeric_values = pd.to_numeric(bakery_products_df[col], errors='coerce')
                total_qty = numeric_values.sum()
                if pd.notna(total_qty):
                    report["summary"][f"total_{col.lower().replace(' ', '_')}"] = float(total_qty)
            except:
                pass
    
    # Additional analysis if merged data is available
    if merged_df is not None and len(merged_df) > 0:
        # Convert numeric columns to proper types
        numeric_cols = ['Subtotal (Calculated)', 'Unit Price', 'CakeQty', 'Total', 'Tax Subtotal', 'AddOnCost']
        for col in numeric_cols:
            if col in merged_df.columns:
                merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0)
        
        # Sales by category
        if 'Category' in merged_df.columns:
            try:
                category_sales = merged_df.groupby('Category').agg({
                    'Subtotal (Calculated)': 'sum',
                    'Unit Price': 'sum',
                    'CakeQty': 'sum'
                }).round(2)
                report["details"]["sales_by_category"] = category_sales.to_dict('index')
            except Exception as e:
                print(f"  Warning: Could not calculate sales by category: {e}")
        
        # Top products by revenue
        if 'Product Description' in merged_df.columns:
            try:
                top_products = merged_df.groupby('Product Description').agg({
                    'Subtotal (Calculated)': 'sum',
                    'CakeQty': 'sum'
                }).sort_values('Subtotal (Calculated)', ascending=False).head(10).round(2)
                report["details"]["top_10_products"] = top_products.to_dict('index')
            except Exception as e:
                print(f"  Warning: Could not calculate top products: {e}")
        
        # Sales by order type
        if 'Order Type ' in merged_df.columns:
            try:
                order_type_sales = merged_df.groupby('Order Type ').agg({
                    'Total': 'sum',
                    'OrderID': 'nunique'
                }).round(2)
                report["details"]["sales_by_order_type"] = order_type_sales.to_dict('index')
            except Exception as e:
                print(f"  Warning: Could not calculate sales by order type: {e}")
    
    # Store column names for reference
    report["details"]["customer_orders_columns"] = list(customer_orders_df.columns)
    report["details"]["bakery_products_columns"] = list(bakery_products_df.columns)
    
    # Sample data preview
    report["details"]["customer_orders_sample"] = customer_orders_df.head(5).to_dict('records')
    report["details"]["bakery_products_sample"] = bakery_products_df.head(5).to_dict('records')
    
    return report


def print_report(report):
    """
    Print a formatted sales report.
    """
    print("\n" + "="*60)
    print("SALES REPORT")
    print("="*60)
    print(f"Generated at: {report['generated_at']}\n")
    
    print("SUMMARY:")
    print("-" * 60)
    for key, value in report["summary"].items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    print("\nDATA STRUCTURE:")
    print("-" * 60)
    print(f"Customer Orders columns: {', '.join(report['details']['customer_orders_columns'])}")
    print(f"Bakery Products columns: {', '.join(report['details']['bakery_products_columns'])}")
    
    # Print additional analysis if available
    if "sales_by_category" in report["details"]:
        print("\nSALES BY CATEGORY:")
        print("-" * 60)
        for category, data in report["details"]["sales_by_category"].items():
            print(f"  {category}: ${data.get('Subtotal (Calculated)', 0):,.2f} ({data.get('CakeQty', 0)} items)")
    
    if "top_10_products" in report["details"]:
        print("\nTOP 10 PRODUCTS BY REVENUE:")
        print("-" * 60)
        for product, data in list(report["details"]["top_10_products"].items())[:10]:
            print(f"  {product}: ${data.get('Subtotal (Calculated)', 0):,.2f} ({data.get('CakeQty', 0)} qty)")
    
    if "sales_by_order_type" in report["details"]:
        print("\nSALES BY ORDER TYPE:")
        print("-" * 60)
        for order_type, data in report["details"]["sales_by_order_type"].items():
            print(f"  {order_type}: ${data.get('Total', 0):,.2f} ({int(data.get('OrderID', 0))} orders)")
    
    print("\n" + "="*60)


def filter_by_date_range(df, date_column, start_date, end_date):
    """
    Filter dataframe by date range.
    
    Args:
        df: DataFrame to filter
        date_column: Name of the date column
        start_date: Start date (datetime or date object)
        end_date: End date (datetime or date object)
    
    Returns:
        Filtered DataFrame
    """
    if date_column not in df.columns:
        return df
    
    # Create a copy to avoid modifying original
    df_copy = df.copy()
    
    # Ensure date column is text/string
    df_copy[date_column] = df_copy[date_column].astype(str).replace(['nan', 'None', ''], '')
    
    # Convert date column from text to datetime - try explicit formats first, then default parsing
    # First try MM-DD-YYYY format (most common)
    df_copy[date_column] = pd.to_datetime(df_copy[date_column], errors='coerce', format='%m-%d-%Y')
    # For any that didn't parse, try M/D/YYYY format
    mask_not_parsed = df_copy[date_column].isna()
    if mask_not_parsed.any():
        df_copy.loc[mask_not_parsed, date_column] = pd.to_datetime(
            df_copy.loc[mask_not_parsed, date_column], 
            errors='coerce', 
            format='%m/%d/%Y'
        )
    # For any still not parsed, try default parsing
    mask_still_not_parsed = df_copy[date_column].isna()
    if mask_still_not_parsed.any():
        df_copy.loc[mask_still_not_parsed, date_column] = pd.to_datetime(
            df_copy.loc[mask_still_not_parsed, date_column], 
            errors='coerce', 
            dayfirst=False, 
            yearfirst=False
        )
    
    # Filter by date range
    mask = (df_copy[date_column] >= pd.Timestamp(start_date)) & (df_copy[date_column] <= pd.Timestamp(end_date))
    filtered_df = df_copy[mask].copy()
    
    return filtered_df


def generate_pdf_report(customer_orders_df, bakery_products_df, merged_df, report, output_dir="reports", 
                        start_date=None, end_date=None):
    """
    Generate a PDF report from the sales data.
    
    Args:
        customer_orders_df: DataFrame with customer orders
        bakery_products_df: DataFrame with bakery products
        merged_df: Merged DataFrame (can be None)
        report: Report dictionary
        output_dir: Output directory for PDF
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine date range for filename
    if start_date and end_date:
        date_str = f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
    else:
        date_str = datetime.now().strftime("%Y%m%d")
    
    pdf_path = os.path.join(output_dir, f"sales_report_{date_str}.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=1  # Center
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12
    )
    normal_style = styles['Normal']
    
    # Title
    title = Paragraph("Sales Report", title_style)
    story.append(title)
    
    # Date range if specified
    if start_date and end_date:
        date_range = Paragraph(
            f"<b>Date Range:</b> {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}",
            normal_style
        )
        story.append(date_range)
        story.append(Spacer(1, 0.2*inch))
    
    # Generated timestamp
    timestamp = Paragraph(
        f"<b>Generated:</b> {report['generated_at']}",
        normal_style
    )
    story.append(timestamp)
    story.append(Spacer(1, 0.3*inch))
    
    # Summary Section
    story.append(Paragraph("Summary", heading_style))
    
    summary_data = [
        ['Metric', 'Value'],
        ['Total Customer Orders', f"{report['summary'].get('total_customer_orders', 0):,}"],
        ['Total Line Items', f"{report['summary'].get('total_line_items', 0):,}"],
    ]
    
    if 'matched_orders' in report['summary']:
        if isinstance(report['summary']['matched_orders'], int):
            summary_data.append(['Matched Orders', f"{report['summary']['matched_orders']:,}"])
        else:
            summary_data.append(['Matched Orders', str(report['summary']['matched_orders'])])
    
    if 'matched_line_items' in report['summary']:
        summary_data.append(['Matched Line Items', f"{report['summary'].get('matched_line_items', 0):,}"])
    
    # Add financial totals
    if 'total_subtotal_(calculated)' in report['summary']:
        summary_data.append(['Total Revenue', f"${report['summary']['total_subtotal_(calculated)']:,.2f}"])
    if 'total_tax_subtotal' in report['summary']:
        summary_data.append(['Total Tax', f"${report['summary']['total_tax_subtotal']:,.2f}"])
    if 'total_cakeqty' in report['summary']:
        summary_data.append(['Total Quantity', f"{report['summary']['total_cakeqty']:,.0f}"])
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Sales by Category
    if "sales_by_category" in report["details"]:
        story.append(Paragraph("Sales by Category", heading_style))
        category_data = [['Category', 'Revenue', 'Quantity']]
        for category, data in report["details"]["sales_by_category"].items():
            category_data.append([
                category,
                f"${data.get('Subtotal (Calculated)', 0):,.2f}",
                f"{data.get('CakeQty', 0):,.0f}"
            ])
        
        category_table = Table(category_data, colWidths=[2*inch, 2*inch, 1.5*inch])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        story.append(category_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Top Products
    if "top_10_products" in report["details"]:
        story.append(Paragraph("Top 10 Products by Revenue", heading_style))
        product_data = [['Product', 'Revenue', 'Quantity']]
        for product, data in list(report["details"]["top_10_products"].items())[:10]:
            product_data.append([
                product[:40] + "..." if len(product) > 40 else product,
                f"${data.get('Subtotal (Calculated)', 0):,.2f}",
                f"{data.get('CakeQty', 0):,.0f}"
            ])
        
        product_table = Table(product_data, colWidths=[3*inch, 1.5*inch, 1*inch])
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        story.append(product_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Sales by Order Type
    if "sales_by_order_type" in report["details"]:
        story.append(Paragraph("Sales by Order Type", heading_style))
        order_type_data = [['Order Type', 'Revenue', 'Orders']]
        for order_type, data in report["details"]["sales_by_order_type"].items():
            order_type_data.append([
                order_type,
                f"${data.get('Total', 0):,.2f}",
                f"{int(data.get('OrderID', 0)):,}"
            ])
        
        order_type_table = Table(order_type_data, colWidths=[2.5*inch, 2*inch, 1*inch])
        order_type_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        story.append(order_type_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Sample Orders Table (if merged data available)
    if merged_df is not None and len(merged_df) > 0:
        story.append(PageBreak())
        story.append(Paragraph("Sample Orders (First 20)", heading_style))
        
        # Select key columns for display
        display_cols = ['Order Date', 'OrderID', 'Customer First Name', 'Customer Last Name', 
                       'Product Description', 'Unit Price', 'Total']
        available_cols = [col for col in display_cols if col in merged_df.columns]
        
        if available_cols:
            sample_df = merged_df[available_cols].head(20)
            sample_data = [available_cols]  # Header
            for _, row in sample_df.iterrows():
                sample_data.append([str(val)[:30] if len(str(val)) > 30 else str(val) for val in row.values])
            
            sample_table = Table(sample_data, colWidths=[5.5*inch / len(available_cols)] * len(available_cols))
            sample_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            story.append(sample_table)
    
    # Build PDF
    doc.build(story)
    print(f"✓ PDF report saved to: {pdf_path}")
    return pdf_path


def save_report_to_csv(customer_orders_df, bakery_products_df, output_dir="reports"):
    """
    Save the dataframes to CSV files for further analysis.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    customer_orders_path = os.path.join(output_dir, f"customer_orders_{timestamp}.csv")
    bakery_products_path = os.path.join(output_dir, f"bakery_products_{timestamp}.csv")
    
    customer_orders_df.to_csv(customer_orders_path, index=False)
    bakery_products_df.to_csv(bakery_products_path, index=False)
    
    print(f"\n✓ Data exported to:")
    print(f"  - {customer_orders_path}")
    print(f"  - {bakery_products_path}")


def main():
    """
    Main function to generate the sales report.
    """
    print("Google Sheets Sales Report Generator")
    print("="*60)
    
    # Date range filter: November 1-15
    start_date = date(2025, 11, 1)  # Adjust year as needed
    end_date = date(2025, 11, 15)
    print(f"\nFiltering data from {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}")
    
    # Authenticate
    try:
        print("\n1. Authenticating with Google Sheets API...")
        client = authenticate_google_sheets("long-canto-360620-6858c5a01c13.json")
        print("✓ Authentication successful")
    except Exception as e:
        print(f"✗ Authentication failed: {str(e)}")
        print("  Make sure 'long-canto-360620-6858c5a01c13.json' exists and the service account")
        print("  has been granted access to the Google Sheet.")
        return
    
    # Read Customer Orders sheet
    print("\n2. Reading Customer Orders sheet...")
    customer_orders_df = read_sheet_data(client, CUSTOMER_ORDERS_SHEET_NAME)
    
    if customer_orders_df.empty:
        print("✗ No data found in Customer Orders sheet")
        return
    
    # Read Bakery Products Ordered sheet
    print("\n3. Reading Bakery Products Ordered sheet...")
    bakery_products_df = read_sheet_data(client, BAKERY_PRODUCTS_SHEET_NAME)
    
    if bakery_products_df.empty:
        print("✗ No data found in Bakery Products Ordered sheet")
        return
    
    # Filter by date range
    print(f"\n4. Filtering orders from {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}...")
    customer_orders_filtered = filter_by_date_range(customer_orders_df, 'Order Date', start_date, end_date)
    print(f"✓ Found {len(customer_orders_filtered)} orders in date range")
    
    if customer_orders_filtered.empty:
        print("⚠ No orders found in the specified date range - generating empty report PDF")
        # Create empty dataframes for PDF generation
        bakery_products_filtered = pd.DataFrame()
        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_customer_orders": 0,
                "total_line_items": 0,
                "matched_orders": 0
            },
            "details": {}
        }
        merged_df = None
        
        # Generate PDF with empty data
        pdf_path = generate_pdf_report(
            customer_orders_filtered, 
            bakery_products_filtered, 
            merged_df,
            report,
            start_date=start_date,
            end_date=end_date
        )
        
        # Open PDF
        import subprocess
        subprocess.run(['open', pdf_path])
        print(f"\n✓ PDF report opened: {pdf_path}")
        return
    
    # Merge filtered orders with bakery products
    if 'OrderID' in customer_orders_filtered.columns and 'OrderID' in bakery_products_df.columns:
        customer_orders_filtered['OrderID'] = customer_orders_filtered['OrderID'].astype(str).str.strip().str.upper()
        bakery_products_df['OrderID'] = bakery_products_df['OrderID'].astype(str).str.strip().str.upper()
        bakery_products_filtered = bakery_products_df[
            bakery_products_df['OrderID'].isin(customer_orders_filtered['OrderID'])
        ]
        print(f"✓ Found {len(bakery_products_filtered)} line items for filtered orders")
    else:
        bakery_products_filtered = bakery_products_df
    
    # Generate report with filtered data
    print("\n5. Generating sales report...")
    report = generate_sales_report(customer_orders_filtered, bakery_products_filtered)
    
    # Print report
    print_report(report)
    
    # Generate PDF report
    print("\n6. Generating PDF report...")
    merged_df = None
    if 'OrderID' in customer_orders_filtered.columns and 'OrderID' in bakery_products_filtered.columns:
        try:
            merged_df = pd.merge(
                customer_orders_filtered,
                bakery_products_filtered,
                on='OrderID',
                how='inner',
                suffixes=('_order', '_item')
            )
        except:
            pass
    
    pdf_path = generate_pdf_report(
        customer_orders_filtered, 
        bakery_products_filtered, 
        merged_df,
        report,
        start_date=start_date,
        end_date=end_date
    )
    
    # Save to CSV
    print("\n7. Exporting filtered data to CSV...")
    save_report_to_csv(customer_orders_filtered, bakery_products_filtered)
    
    # Save report JSON
    report_path = os.path.join("reports", f"sales_report_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  - {report_path}")
    
    # Open PDF
    import subprocess
    subprocess.run(['open', pdf_path])
    print(f"\n✓ PDF report opened: {pdf_path}")
    
    print("\n✓ Report generation complete!")


if __name__ == "__main__":
    main()

