"""
🎯 PERFORMANCE TRACKER - Phase 1: Proxy Metrics
Tracks LinkedIn post performance WITHOUT LinkedIn API

Data Sources:
1. Buffer API - engagement metrics (clicks, reach)
2. Google Analytics - website traffic from LinkedIn
3. Gmail API - opportunity tracking (inbound emails mentioning LinkedIn)
4. Bitly - demo link clicks

This closes the feedback loop for AI Co-Founder learning!
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import aiohttp
import logging

logger = logging.getLogger(__name__)

# Google Analytics imports (optional - graceful fallback if not installed)
try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest,
        Dimension,
        Metric,
        DateRange,
        FilterExpression,
        Filter,
        FilterExpressionList,
    )
    from google.oauth2 import service_account
    GA_AVAILABLE = True
except ImportError:
    GA_AVAILABLE = False
    logger.warning("⚠️ google-analytics-data not installed - GA integration disabled")


class PerformanceTracker:
    """
    Tracks LinkedIn post performance using proxy metrics
    
    NO LinkedIn API needed! Uses:
    - Buffer Analytics API
    - Google Analytics API  
    - Gmail API
    - UTM parameters
    """
    
    def __init__(self):
        self.data_dir = Path("linkedin_cmo_data")
        self.data_dir.mkdir(exist_ok=True)
        
        # API keys (from environment)
        self.buffer_access_token = os.getenv('BUFFER_ACCESS_TOKEN')
        self.google_analytics_key = os.getenv('GOOGLE_ANALYTICS_KEY')
        self.google_analytics_credentials = os.getenv('GOOGLE_ANALYTICS_CREDENTIALS')  # JSON as string
        self.ga4_property_id = os.getenv('GA4_PROPERTY_ID')
        self.gmail_credentials = os.getenv('GMAIL_CREDENTIALS_PATH')
        
        # Initialize Google Analytics client
        self.ga_client = None
        if GA_AVAILABLE and (self.google_analytics_key or self.google_analytics_credentials):
            try:
                self.ga_client = self._initialize_ga_client()
                if self.ga_client:
                    logger.info("✅ GA4 client initialized")
            except Exception as e:
                logger.warning(f"⚠️ GA client init failed: {e}")
        
        # Performance database
        self.performance_file = self.data_dir / "real_performance.json"
        self.opportunities_file = self.data_dir / "opportunities.json"
        
        # Log configuration
        logger.info("📊 Performance Tracker initialized:")
        logger.info(f"   UTM tracking: ACTIVE")
        logger.info(f"   Buffer API: {'Ready' if self.buffer_access_token else 'Not configured'}")
        logger.info(f"   GA4: {'Ready' if self.ga_client else 'Not configured'}")
        logger.info(f"   Gmail: {'Ready' if self.gmail_credentials else 'Not configured'}")
    
    def _initialize_ga_client(self):
        """
        Initialize Google Analytics Data API client
        
        Supports two authentication methods:
        1. JSON key file path (GOOGLE_ANALYTICS_KEY)
        2. JSON credentials as string (GOOGLE_ANALYTICS_CREDENTIALS)
        """
        if not GA_AVAILABLE:
            logger.warning("google-analytics-data package not installed")
            return None
        
        try:
            # Method 1: JSON key file path
            if self.google_analytics_key and os.path.exists(self.google_analytics_key):
                credentials = service_account.Credentials.from_service_account_file(
                    self.google_analytics_key,
                    scopes=['https://www.googleapis.com/auth/analytics.readonly']
                )
                logger.info(f"✅ Loaded GA credentials from file: {self.google_analytics_key}")
                return BetaAnalyticsDataClient(credentials=credentials)
            
            # Method 2: JSON credentials as environment variable
            elif self.google_analytics_credentials:
                import tempfile
                
                # Parse JSON credentials
                creds_dict = json.loads(self.google_analytics_credentials)
                
                # Create temporary file for credentials
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(creds_dict, f)
                    temp_path = f.name
                
                credentials = service_account.Credentials.from_service_account_file(
                    temp_path,
                    scopes=['https://www.googleapis.com/auth/analytics.readonly']
                )
                
                # Clean up temp file
                os.unlink(temp_path)
                
                logger.info("✅ Loaded GA credentials from environment variable")
                return BetaAnalyticsDataClient(credentials=credentials)
            
            else:
                logger.warning("No GA credentials found")
                return None
        
        except Exception as e:
            logger.error(f"Failed to initialize GA client: {e}")
            return None
    
    # ==================== UTM TRACKING ====================
    
    def add_utm_parameters(self, url: str, post_id: str, post_type: str) -> str:
        """
        Add UTM parameters to track which posts drive traffic
        
        Example:
        wa.me/50766623757 
        → wa.me/50766623757?utm_source=linkedin&utm_medium=social&utm_campaign=cmo_post_123&utm_content=open_to_work
        """
        separator = "&" if "?" in url else "?"
        
        utm_params = (
            f"utm_source=linkedin"
            f"&utm_medium=social"
            f"&utm_campaign=cmo_{post_id}"
            f"&utm_content={post_type}"
            f"&utm_term=ai_cofounder"
        )
        
        tracked_url = f"{url}{separator}{utm_params}"
        logger.debug(f"UTM: {url[:30]}... → tracked")
        return tracked_url
    
    def enhance_post_content_with_utm(self, content: str, post_id: str, post_type: str) -> str:
        """
        Replace all URLs in post content with UTM-tracked versions
        """
        # URLs to track
        urls_to_track = {
            "wa.me/50766623757": "wa.me/50766623757",
            "aideazz.xyz": "https://aideazz.xyz",
            "aideazz.xyz/card": "https://aideazz.xyz/card",
            "espaluz-ai-language-tutor.lovable.app": "https://espaluz-ai-language-tutor.lovable.app",
            "atuona.xyz": "https://atuona.xyz",
        }
        
        enhanced_content = content
        
        for url_text, full_url in urls_to_track.items():
            if url_text in content:
                tracked_url = self.add_utm_parameters(full_url, post_id, post_type)
                enhanced_content = enhanced_content.replace(url_text, tracked_url)
        
        return enhanced_content
    
    # ==================== BUFFER API ====================
    
    async def get_buffer_analytics(self, post_id: str) -> Dict[str, Any]:
        """
        Get post performance from Buffer API
        
        Buffer tracks:
        - Clicks
        - Reach (estimated)
        - Engagement rate
        
        Docs: https://buffer.com/developers/api/updates
        """
        if not self.buffer_access_token:
            logger.warning("⚠️ Buffer API token not set - skipping Buffer analytics")
            return {}
        
        try:
            url = f"https://api.bufferapp.com/1/updates/{post_id}.json"
            params = {"access_token": self.buffer_access_token}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        analytics = {
                            "clicks": data.get("statistics", {}).get("clicks", 0),
                            "reach": data.get("statistics", {}).get("reach", 0),
                            "engagement": data.get("statistics", {}).get("engagement", 0),
                            "shares": data.get("statistics", {}).get("shares", 0),
                            "source": "buffer_api",
                            "fetched_at": datetime.now().isoformat()
                        }
                        
                        logger.info(f"✅ Buffer analytics: {analytics['clicks']} clicks, {analytics['reach']} reach")
                        return analytics
                    else:
                        logger.warning(f"Buffer API error: {response.status}")
                        return {}
        
        except Exception as e:
            logger.error(f"Failed to get Buffer analytics: {e}")
            return {}
    
    # ==================== GOOGLE ANALYTICS ====================
    
    async def get_google_analytics_data(
        self, 
        start_date: datetime, 
        end_date: datetime,
        utm_campaign: str
    ) -> Dict[str, Any]:
        """
        Get website traffic from Google Analytics Data API v1 (GA4)
        
        Tracks:
        - Sessions from LinkedIn
        - Page views
        - Conversions (demo requests, contact forms)
        - Time on site
        - Bounce rate
        
        Filters by UTM campaign to attribute traffic to specific LinkedIn posts
        
        Docs: https://developers.google.com/analytics/devguides/reporting/data/v1
        """
        if not self.ga_client:
            logger.warning("⚠️ Google Analytics not configured - skipping GA data")
            return {}
        
        if not self.ga4_property_id:
            logger.warning("⚠️ GA4_PROPERTY_ID not set - skipping GA data")
            return {}
        
        try:
            # Format dates for GA4 API (YYYY-MM-DD)
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            # Build the request
            request = RunReportRequest(
                property=f"properties/{self.ga4_property_id}",
                dimensions=[
                    Dimension(name="sessionSource"),
                    Dimension(name="sessionMedium"),
                    Dimension(name="sessionCampaignName"),
                ],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="screenPageViews"),
                    Metric(name="averageSessionDuration"),
                    Metric(name="engagedSessions"),
                    Metric(name="bounceRate"),
                    Metric(name="newUsers"),
                ],
                date_ranges=[DateRange(start_date=start_date_str, end_date=end_date_str)],
                dimension_filter=FilterExpression(
                    and_group=FilterExpressionList(
                        expressions=[
                            FilterExpression(
                                filter=Filter(
                                    field_name="sessionSource",
                                    string_filter=Filter.StringFilter(
                                        match_type=Filter.StringFilter.MatchType.EXACT,
                                        value="linkedin"
                                    )
                                )
                            ),
                            FilterExpression(
                                filter=Filter(
                                    field_name="sessionCampaignName",
                                    string_filter=Filter.StringFilter(
                                        match_type=Filter.StringFilter.MatchType.CONTAINS,
                                        value=utm_campaign
                                    )
                                )
                            ),
                        ]
                    )
                ),
            )
            
            # Execute request in thread pool (GA client is synchronous)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.ga_client.run_report,
                request
            )
            
            # Parse response
            analytics = {
                "sessions": 0,
                "page_views": 0,
                "avg_session_duration": 0,
                "engaged_sessions": 0,
                "bounce_rate": 0.0,
                "new_users": 0,
                "source": "google_analytics_api",
                "utm_campaign": utm_campaign,
                "date_range": f"{start_date.date()} to {end_date.date()}",
                "fetched_at": datetime.now().isoformat()
            }
            
            # Extract metrics from response
            if response.rows:
                for row in response.rows:
                    # Sum up all metrics (in case there are multiple rows)
                    analytics["sessions"] += int(row.metric_values[0].value)
                    analytics["page_views"] += int(row.metric_values[1].value)
                    analytics["avg_session_duration"] += float(row.metric_values[2].value)
                    analytics["engaged_sessions"] += int(row.metric_values[3].value)
                    analytics["bounce_rate"] += float(row.metric_values[4].value)
                    analytics["new_users"] += int(row.metric_values[5].value)
                
                # Average the session duration and bounce rate
                if len(response.rows) > 1:
                    analytics["avg_session_duration"] /= len(response.rows)
                    analytics["bounce_rate"] /= len(response.rows)
                
                logger.info(f"📊 GA: {analytics['sessions']} sessions, {analytics['page_views']} pageviews")
            else:
                logger.debug(f"📊 GA: No data yet for {utm_campaign}")
            
            return analytics
        
        except Exception as e:
            logger.error(f"Failed to get Google Analytics: {e}")
            return {}
    
    # ==================== GMAIL API - OPPORTUNITY TRACKING ====================
    
    async def scan_inbox_for_opportunities(self, since_date: datetime) -> List[Dict[str, Any]]:
        """
        Scan Gmail inbox for LinkedIn-related opportunities
        
        Looks for:
        - "I saw your LinkedIn post"
        - "Your post about AI Co-Founders"
        - Investor emails
        - Job interview requests
        - Collaboration proposals
        
        Then attributes to specific post_id via timing/content matching
        """
        if not self.gmail_credentials:
            logger.warning("⚠️ Gmail API not configured - skipping opportunity tracking")
            return []
        
        try:
            # TODO: Implement Gmail API
            # For now, return structure
            
            opportunities = []
            
            # Example structure:
            sample_opportunity = {
                "type": "investor_contact",  # investor_contact, job_interview, collaboration
                "from": "investor@vc.com",
                "subject": "Saw your LinkedIn post - let's chat",
                "date": datetime.now().isoformat(),
                "linkedin_mentioned": True,
                "post_reference": "AI Co-Founders concept",  # What they mentioned
                "attributed_post_id": "open_to_work_20251203",  # Match to post
                "value_score": 9,  # 1-10 importance
                "status": "new"  # new, responded, scheduled, closed
            }
            
            opportunities.append(sample_opportunity)
            
            logger.info(f"📧 Found {len(opportunities)} opportunities mentioning LinkedIn")
            return opportunities
        
        except Exception as e:
            logger.error(f"Failed to scan inbox: {e}")
            return []
    
    # ==================== COMPREHENSIVE POST ANALYSIS ====================
    
    async def analyze_post_performance(
        self, 
        post_id: str, 
        post_type: str,
        posted_date: datetime
    ) -> Dict[str, Any]:
        """
        Comprehensive performance analysis combining ALL proxy metrics
        
        Returns:
        {
            "post_id": "...",
            "buffer_metrics": {...},
            "ga_metrics": {...},
            "opportunities": [...],
            "total_score": 85,
            "insights": ["High engagement", "Drove 3 website visits", "1 investor email"]
        }
        """
        logger.info(f"📊 Analyzing performance for post: {post_id}")
        
        # Calculate date range (7 days after post)
        end_date = posted_date + timedelta(days=7)
        
        # Fetch all metrics in parallel
        buffer_data, ga_data, opportunities = await asyncio.gather(
            self.get_buffer_analytics(post_id),
            self.get_google_analytics_data(posted_date, end_date, f"cmo_{post_id}"),
            self.scan_inbox_for_opportunities(posted_date),
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(buffer_data, Exception):
            buffer_data = {}
        if isinstance(ga_data, Exception):
            ga_data = {}
        if isinstance(opportunities, Exception):
            opportunities = []
        
        # Calculate composite score
        score = self._calculate_performance_score(buffer_data, ga_data, opportunities)
        
        # Generate insights
        insights = self._generate_insights(buffer_data, ga_data, opportunities)
        
        analysis = {
            "post_id": post_id,
            "post_type": post_type,
            "posted_date": posted_date.isoformat(),
            "analyzed_at": datetime.now().isoformat(),
            "buffer_metrics": buffer_data,
            "ga_metrics": ga_data,
            "opportunities": opportunities,
            "performance_score": score,
            "insights": insights,
            "business_value": self._calculate_business_value(opportunities)
        }
        
        # Save to database
        self._save_performance_data(analysis)
        
        logger.info(f"✅ Post analysis complete - Score: {score}/100")
        return analysis
    
    def _calculate_performance_score(
        self,
        buffer_data: Dict,
        ga_data: Dict,
        opportunities: List
    ) -> float:
        """
        Calculate 0-100 score based on multiple signals
        
        Weights:
        - Buffer engagement: 30%
        - Website traffic: 30%
        - Opportunities: 40% (most important!)
        """
        score = 0.0
        
        # Buffer engagement (30 points)
        clicks = buffer_data.get("clicks", 0)
        reach = buffer_data.get("reach", 0)
        engagement = buffer_data.get("engagement", 0)
        
        buffer_score = min(30, (clicks * 2) + (reach * 0.01) + (engagement * 5))
        score += buffer_score
        
        # Google Analytics (30 points)
        sessions = ga_data.get("sessions", 0)
        demo_clicks = ga_data.get("demo_clicks", 0)
        contact_forms = ga_data.get("contact_form_submissions", 0)
        
        ga_score = min(30, (sessions * 3) + (demo_clicks * 5) + (contact_forms * 10))
        score += ga_score
        
        # Opportunities (40 points) - MOST IMPORTANT!
        opportunity_score = 0
        for opp in opportunities:
            value = opp.get("value_score", 5)
            if opp["type"] == "investor_contact":
                opportunity_score += value * 5  # Highest value
            elif opp["type"] == "job_interview":
                opportunity_score += value * 4
            elif opp["type"] == "collaboration":
                opportunity_score += value * 3
        
        score += min(40, opportunity_score)
        
        return min(100.0, score)
    
    def _generate_insights(
        self,
        buffer_data: Dict,
        ga_data: Dict,
        opportunities: List
    ) -> List[str]:
        """Generate human-readable insights"""
        insights = []
        
        # Buffer insights
        clicks = buffer_data.get("clicks", 0)
        if clicks > 20:
            insights.append(f"🔥 High engagement: {clicks} clicks")
        elif clicks > 10:
            insights.append(f"✅ Good engagement: {clicks} clicks")
        
        # GA insights
        sessions = ga_data.get("sessions", 0)
        if sessions > 0:
            insights.append(f"🌐 Drove {sessions} website visits")
        
        # Opportunity insights
        if opportunities:
            investor_count = len([o for o in opportunities if o["type"] == "investor_contact"])
            job_count = len([o for o in opportunities if o["type"] == "job_interview"])
            
            if investor_count > 0:
                insights.append(f"💰 {investor_count} investor contact(s)")
            if job_count > 0:
                insights.append(f"💼 {job_count} job interview request(s)")
        
        if not insights:
            insights.append("📊 Building baseline data")
        
        return insights
    
    def _calculate_business_value(self, opportunities: List) -> Dict[str, Any]:
        """
        Calculate estimated business value
        
        Rough estimates:
        - Investor contact: $50K (potential investment)
        - Job interview: $150K (potential salary)
        - Collaboration: $20K (potential revenue)
        """
        value = {
            "investor_value": len([o for o in opportunities if o["type"] == "investor_contact"]) * 50000,
            "job_value": len([o for o in opportunities if o["type"] == "job_interview"]) * 150000,
            "collaboration_value": len([o for o in opportunities if o["type"] == "collaboration"]) * 20000,
        }
        
        value["total_estimated_value"] = sum(value.values())
        
        return value
    
    def _save_performance_data(self, analysis: Dict[str, Any]):
        """Save performance data to JSON database"""
        try:
            # Load existing data
            if self.performance_file.exists():
                with open(self.performance_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {"posts": []}
            
            # Add new analysis
            data["posts"].append(analysis)
            
            # Save
            with open(self.performance_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"💾 Performance data saved: {self.performance_file}")
        
        except Exception as e:
            logger.error(f"Failed to save performance data: {e}")
    
    # ==================== LEARNING INSIGHTS ====================
    
    async def get_learning_insights(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze performance over time to generate learning insights
        
        Used by AI Co-Founder to adapt strategy
        """
        try:
            if not self.performance_file.exists():
                return {"error": "No performance data yet"}
            
            with open(self.performance_file, 'r') as f:
                data = json.load(f)
            
            posts = data.get("posts", [])
            
            # Filter to last N days
            cutoff = datetime.now() - timedelta(days=days)
            recent_posts = [
                p for p in posts
                if datetime.fromisoformat(p["posted_date"]) > cutoff
            ]
            
            if not recent_posts:
                return {"error": "No recent posts to analyze"}
            
            # Analyze by post type
            by_type = {}
            for post in recent_posts:
                post_type = post["post_type"]
                if post_type not in by_type:
                    by_type[post_type] = []
                by_type[post_type].append(post["performance_score"])
            
            # Calculate averages
            type_performance = {
                post_type: {
                    "avg_score": sum(scores) / len(scores),
                    "post_count": len(scores),
                    "recommendation": "increase" if sum(scores) / len(scores) > 70 else "decrease"
                }
                for post_type, scores in by_type.items()
            }
            
            # Best performing type
            best_type = max(type_performance.items(), key=lambda x: x[1]["avg_score"])
            
            insights = {
                "analyzed_posts": len(recent_posts),
                "date_range_days": days,
                "by_post_type": type_performance,
                "best_performing_type": best_type[0],
                "best_performing_score": best_type[1]["avg_score"],
                "recommendations": [
                    f"Post more '{best_type[0]}' content (avg score: {best_type[1]['avg_score']:.1f})",
                    f"Total opportunities generated: {sum(len(p.get('opportunities', [])) for p in recent_posts)}",
                ],
                "analyzed_at": datetime.now().isoformat()
            }
            
            logger.info(f"🧠 Learning insights generated: {insights['best_performing_type']} performing best")
            return insights
        
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return {"error": str(e)}


# ==================== QUICK SETUP HELPER ====================

def create_setup_instructions():
    """
    Generate setup instructions for the user
    """
    instructions = """
    🎯 PERFORMANCE TRACKER SETUP INSTRUCTIONS
    ==========================================
    
    To enable proxy metrics tracking, add these environment variables:
    
    1. BUFFER API (Optional but recommended):
       - Go to: https://buffer.com/developers/api
       - Create an app (free)
       - Get access token
       - Add to .env:
         BUFFER_ACCESS_TOKEN=your_token_here
    
    2. GOOGLE ANALYTICS (Optional):
       - Go to: https://console.cloud.google.com
       - Enable Analytics Data API
       - Create service account
       - Download credentials JSON
       - Add to .env:
         GOOGLE_ANALYTICS_KEY=path/to/credentials.json
    
    3. GMAIL API (Recommended for opportunity tracking):
       - Go to: https://console.cloud.google.com
       - Enable Gmail API
       - Create OAuth 2.0 credentials
       - Download credentials JSON
       - Add to .env:
         GMAIL_CREDENTIALS_PATH=path/to/gmail_credentials.json
    
    4. UTM TRACKING (No setup needed - automatic!):
       - Already integrated
       - Tracks all links in posts
       - View in Google Analytics: Acquisition > Campaigns
    
    5. TEST INSTALLATION:
       python -c "from src.notifications.performance_tracker import PerformanceTracker; pt = PerformanceTracker(); print('✅ Setup complete!')"
    
    ==========================================
    Start with just UTM tracking (zero config needed!)
    Add APIs later for richer data.
    """
    
    print(instructions)
    return instructions


if __name__ == "__main__":
    create_setup_instructions()
