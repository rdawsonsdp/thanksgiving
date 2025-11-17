# Google Sheets Sales Report Generator

This project generates sales reports from Google Sheets data, reading from "Customer Orders" and "Bakery Products Ordered" sheets.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Service Account Setup

To access Google Sheets, you need to set up a service account:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API and Google Drive API
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name (e.g., "sheets-reader")
   - Grant it the "Viewer" role for the spreadsheet
5. Create and download a JSON key:
   - Click on the service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Download the file

### 3. Configure Credentials

1. The credentials file `long-canto-360620-6858c5a01c13.json` is already configured
2. Share your Google Sheet with the service account email address:
   - Open your Google Sheet
   - Click "Share" button
   - Add the service account email: `googlesheetsaccount@long-canto-360620.iam.gserviceaccount.com`
   - Give it "Viewer" access

### 4. Run the Report

#### Generate PDF Report

```bash
python sales_report.py
```

#### Run Interactive Web Application

```bash
streamlit run app.py
```

The web application will open in your browser at `http://localhost:8501`

**Features:**
- 📅 **Date Filtering**: Filter orders by Order Date range
- 🍰 **Product Filtering**: Filter by specific products
- 📍 **Pickup Date Filtering**: Filter by Due Pickup Date range
- 📊 **Interactive Charts**: Visualize sales by category, order type, and daily trends
- 📋 **Data Table**: View and search filtered order details
- 📥 **Export**: Download filtered data as CSV

## Output

The script will:
- Read data from both sheets
- Generate a summary report in the console
- Export data to CSV files in the `reports/` directory
- Save a JSON report file with detailed metrics

## Google Sheet Information

- **Spreadsheet ID**: `1YAHO5rHhFVEReyAuxa7r2SDnoH7BnDfsmSEZ1LyjB8A`
- **Customer Orders Sheet**: `Customer Orders` (gid=199509783)
- **Bakery Products Ordered Sheet**: `Bakery Products Ordered` (gid=763641856)

## Troubleshooting

- **Authentication errors**: Make sure `credentials.json` is in the correct location and the service account has access to the sheet
- **Sheet not found**: Verify the sheet names match exactly (case-sensitive)
- **Permission denied**: Ensure the service account email has been shared with the Google Sheet

