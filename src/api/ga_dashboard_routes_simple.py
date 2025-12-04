"""
Simple GA4 Dashboard Routes - Minimal version for debugging
"""
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    logger.info("✅ Test endpoint called successfully")
    return {
        "status": "working",
        "message": "Analytics routes are loaded!",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health")
async def health_check():
    """Check if GA4 connection is working"""
    logger.info("🏥 Health check endpoint called")
    
    has_credentials = bool(os.getenv('GOOGLE_ANALYTICS_CREDENTIALS'))
    has_property_id = bool(os.getenv('GA4_PROPERTY_ID'))
    
    status_info = {
        "status": "healthy" if (has_credentials and has_property_id) else "degraded",
        "ga4_credentials_set": has_credentials,
        "property_id_set": has_property_id,
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"Health check result: {status_info}")
    return status_info


@router.get("/dashboard", response_class=HTMLResponse)
async def get_simple_dashboard():
    """Simple dashboard that always works"""
    logger.info("📊 Dashboard endpoint called")
    
    has_credentials = bool(os.getenv('GOOGLE_ANALYTICS_CREDENTIALS'))
    has_property_id = bool(os.getenv('GA4_PROPERTY_ID'))
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GA4 Dashboard - Status</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #667eea;
            margin: 0 0 10px 0;
        }}
        .status {{
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .success {{
            background: #d1fae5;
            border: 2px solid #059669;
            color: #065f46;
        }}
        .warning {{
            background: #fef3c7;
            border: 2px solid #f59e0b;
            color: #92400e;
        }}
        .info {{
            background: #dbeafe;
            border: 2px solid #3b82f6;
            color: #1e40af;
        }}
        .check-item {{
            padding: 10px;
            margin: 10px 0;
            background: #f3f4f6;
            border-radius: 5px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }}
        .badge-success {{ background: #d1fae5; color: #059669; }}
        .badge-error {{ background: #fee2e2; color: #dc2626; }}
        .links {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
        }}
        .link {{
            display: inline-block;
            margin: 5px 10px 5px 0;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: 500;
        }}
        .link:hover {{ background: #5568d3; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 GA4 Dashboard Status</h1>
        <p style="color: #666; margin-bottom: 30px;">Railway Deployment Check</p>
        
        <div class="status {'success' if (has_credentials and has_property_id) else 'warning'}">
            <h2 style="margin: 0 0 15px 0;">
                {'✅ System Ready!' if (has_credentials and has_property_id) else '⚠️ Configuration Needed'}
            </h2>
            <p style="margin: 0;">
                {'All credentials are configured. Dashboard is ready!' if (has_credentials and has_property_id) else 'Some configuration is missing. Check details below.'}
            </p>
        </div>
        
        <div class="status info">
            <h3>Configuration Check:</h3>
            <div class="check-item">
                <strong>GA4 Credentials:</strong>
                <span class="badge {'badge-success' if has_credentials else 'badge-error'}">
                    {'✅ SET' if has_credentials else '❌ NOT SET'}
                </span>
            </div>
            <div class="check-item">
                <strong>GA4 Property ID:</strong>
                <span class="badge {'badge-success' if has_property_id else 'badge-error'}">
                    {'✅ SET' if has_property_id else '❌ NOT SET'}
                </span>
            </div>
        </div>
        
        <div class="status info">
            <h3>System Info:</h3>
            <div class="check-item">
                <strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>
            <div class="check-item">
                <strong>Status:</strong> Application is running ✅
            </div>
            <div class="check-item">
                <strong>Routes:</strong> Analytics endpoints loaded ✅
            </div>
        </div>
        
        <div class="links">
            <h3>Available Endpoints:</h3>
            <a href="/analytics/test" class="link">🧪 Test Endpoint</a>
            <a href="/analytics/health" class="link">❤️ Health Check (JSON)</a>
            <a href="/" class="link">🏠 Main App</a>
            <a href="/docs" class="link">📚 API Docs</a>
        </div>
        
        {'<div class="status success"><h3>✅ Ready for Full Dashboard</h3><p>Credentials are configured. The full GA4 dashboard with real data will be deployed in the next update!</p></div>' if (has_credentials and has_property_id) else '<div class="status warning"><h3>⚠️ Setup Instructions</h3><p>To enable the full dashboard:<br>1. Go to Railway Variables<br>2. Set GOOGLE_ANALYTICS_CREDENTIALS<br>3. Set GA4_PROPERTY_ID<br>4. Redeploy</p></div>'}
    </div>
</body>
</html>
"""
    
    return html


@router.get("/metrics")
async def get_simple_metrics():
    """Simple metrics endpoint"""
    logger.info("📊 Metrics endpoint called")
    
    return {
        "status": "success",
        "message": "Analytics system operational",
        "timestamp": datetime.now().isoformat(),
        "note": "Full metrics will be available once GA4 is fully integrated"
    }
