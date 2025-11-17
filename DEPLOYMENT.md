# Deployment Guide

## Local Development

### Option 1: Streamlit App (Interactive Dashboard)

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

### Option 2: Flask API + Web Frontend

#### Start Flask API Server

```bash
python api.py
```

API runs at `http://localhost:5000`

#### Open Web Frontend

Open `public/index.html` in your browser, or use a local server:

```bash
cd public
python -m http.server 8000
```

Then open `http://localhost:8000` in your browser.

**Note:** Update the `API_BASE` in `public/index.html` to `http://localhost:5000/api` for local development.

## Vercel Deployment

### Prerequisites

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Create a Vercel account at [vercel.com](https://vercel.com)

### Deployment Steps

1. **Login to Vercel:**
```bash
vercel login
```

2. **Deploy:**
```bash
vercel
```

Follow the prompts:
- Set up and deploy? **Yes**
- Which scope? (Select your account)
- Link to existing project? **No**
- Project name? (Press Enter for default)
- Directory? (Press Enter for current directory)
- Override settings? **No**

3. **Add Environment Variables (if needed):**
```bash
vercel env add GOOGLE_SHEETS_CREDENTIALS
```

4. **Deploy to Production:**
```bash
vercel --prod
```

### Important Notes for Vercel

1. **Credentials File**: The `long-canto-360620-6858c5a01c13.json` file must be included in your deployment. Make sure it's not in `.gitignore` or `.vercelignore`.

2. **File Size Limits**: Vercel has limits on file sizes. If your credentials file is too large, consider:
   - Using environment variables instead
   - Storing credentials in Vercel's environment variables

3. **API Routes**: The Flask API will be deployed as serverless functions. Make sure all routes are under `/api/`.

4. **Static Files**: Files in the `public/` directory will be served as static files.

### Alternative: Using Environment Variables

Instead of including the JSON file, you can store credentials as environment variables:

1. Convert JSON to base64:
```bash
cat long-canto-360620-6858c5a01c13.json | base64
```

2. Add to Vercel:
```bash
vercel env add GOOGLE_CREDENTIALS_BASE64
```

3. Update `api.py` to read from environment:
```python
import os
import json
import base64

def get_credentials():
    if 'GOOGLE_CREDENTIALS_BASE64' in os.environ:
        creds_json = json.loads(base64.b64decode(os.environ['GOOGLE_CREDENTIALS_BASE64']))
        return Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    else:
        creds_path = os.path.join(os.path.dirname(__file__), "long-canto-360620-6858c5a01c13.json")
        return Credentials.from_service_account_file(creds_path, scopes=SCOPES)
```

## Troubleshooting

### CORS Issues
If you see CORS errors, make sure `flask-cors` is installed and `CORS(app)` is enabled in `api.py`.

### API Not Found
- Check that routes start with `/api/`
- Verify `vercel.json` routing configuration
- Check Vercel function logs: `vercel logs`

### Credentials Not Found
- Ensure the JSON file is in the root directory
- Check `.vercelignore` doesn't exclude it
- Consider using environment variables instead

## Project Structure

```
.
├── api.py                 # Flask API (Vercel serverless functions)
├── app.py                 # Streamlit app (local only)
├── sales_report.py        # PDF report generator
├── public/
│   └── index.html        # Web frontend
├── vercel.json           # Vercel configuration
├── requirements.txt      # Python dependencies
└── long-canto-360620-6858c5a01c13.json  # Google credentials
```

