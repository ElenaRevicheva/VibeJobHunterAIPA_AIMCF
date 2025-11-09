"""
Smart search targeting YC, AngelList, and startup-focused job boards
Focuses on founding engineer roles with equity
"""
import asyncio
import aiohttp
from typing import List
from pathlib import Path
import json

from ..core.models import JobPosting, JobSource
from ..loaders import CandidateDataLoader
from rich.console import Console

console = Console()


class StartupJobSearch:
    """Search for founding engineer roles at YC/AngelList startups"""
    
    def __init__(self):
        self.loader = CandidateDataLoader()
        self.data = self._load_candidate_data()
        self.target_roles = self.data.get('target_roles', [])
        self.target_companies = self.data.get('target_companies', {})
    
    def _load_candidate_data(self) -> dict:
        """Load candidate data"""
        try:
            data_file = Path(__file__).parent.parent / "core" / "candidate_data.json"
            with open(data_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def get_search_urls(self) -> List[str]:
        """
        Generate optimized search URLs for YC, AngelList, and startup boards
        
        Returns:
            List of search URLs to open in browser
        """
        urls = []
        
        # Y Combinator Jobs - Top priority
        yc_searches = [
            "Founding Engineer AI",
            "AI Engineer early stage",
            "Full-Stack AI Engineer",
            "LLM Engineer",
            "Technical Co-Founder"
        ]
        
        for search in yc_searches[:3]:  # Top 3 searches
            query = search.replace(" ", "%20")
            urls.append(f"https://www.ycombinator.com/companies?q={query}")
        
        # AngelList (Wellfound) - Equity-focused
        angellist_searches = [
            "founding+engineer+AI",
            "technical+cofounder",
            "ai+product+engineer"
        ]
        
        for search in angellist_searches:
            urls.append(f"https://wellfound.com/role/r/software-engineer?query={search}")
        
        # Web3 Career (for Web3+AI combo roles)
        urls.append("https://web3.career/web3-ai-jobs")
        urls.append("https://crypto.jobs/jobs?search=ai+engineer")
        
        # LinkedIn with optimized filters
        linkedin_searches = [
            "Founding%20Engineer%20AI%20startup%20equity",
            "Technical%20Co-Founder%20AI",
            "AI%20Product%20Engineer%20Series%20A"
        ]
        
        for search in linkedin_searches[:2]:
            urls.append(f"https://www.linkedin.com/jobs/search/?keywords={search}&f_TPR=r86400&f_WT=2")  # Remote, last 24h
        
        return urls
    
    def generate_search_guide(self) -> str:
        """Generate personalized search guide"""
        
        guide = f"""# 🎯 YOUR PERSONALIZED JOB SEARCH GUIDE

Based on your profile (PayPal subscriptions, 19 countries, Web3+AI), target these:

## 🔍 TOP PRIORITY SEARCHES

### 1. Y Combinator (https://www.ycombinator.com/companies)
Search terms:
- "Founding Engineer AI"
- "AI Engineer early stage"
- "Full-Stack AI Engineer"

Filter by:
- Stage: Seed, Series A
- Remote: Yes
- Industry: AI, ML, B2B SaaS

### 2. AngelList (https://wellfound.com/)
Search terms:
- "Founding Engineer AI"
- "Technical Co-Founder"
- "AI Product Engineer"

Filters:
- Equity: 0.5-3%
- Stage: Seed, Series A
- Role: Founding Engineer
- Remote: Yes

### 3. Web3 + AI (Unique Combo!)
- https://web3.career/web3-ai-jobs
- https://crypto.jobs/ (search: "AI Engineer")

Your advantage: DAO/tokenomics + AI agents!

### 4. LinkedIn (Optimized)
Search:
- "Founding Engineer AI startup equity"
- "Employee 1-10 AI company"

Filters:
- Date Posted: Past 24 hours
- Job Type: Remote
- Experience: Mid-Senior

## ✅ WHAT TO LOOK FOR

Target roles:
{', '.join(self.target_roles[:5])}

Company stage:
{', '.join(self.target_companies.get('stage', []))}

Key phrases in JD:
- "Founding engineer"
- "Employee #1-10"
- "Equity: 0.5-3%"
- "AI-first"
- "0→1 product"
- "Full-stack"

## ❌ WHAT TO AVOID

Red flags:
- No equity mentioned (at early-stage company)
- "Rockstar" or "Ninja" in title
- Below $100K with no equity
- Pure maintenance work
- Big corp with slow processes
- Non-AI companies

## 💡 YOUR PITCH

When you see a great job, remember your key differentiators:
1. PayPal Subscriptions LIVE (revenue!)
2. 19 countries reach (traction!)
3. 2 live AI agents (not demos!)
4. Web3 + AI combo (rare!)
5. Ex-Deputy CEO & CLO (strategy!)

Always include: wa.me/50766623757 (live demo!)

---

Save job URLs to jobs.txt, then run:
py -m src.main batch --file jobs.txt --v2
"""
        
        return guide
    
    async def open_all_search_pages(self):
        """Open all recommended search pages in browser"""
        import webbrowser
        
        urls = self.get_search_urls()
        
        console.print("\n[yellow]Opening all search pages in your browser...[/yellow]\n")
        
        for i, url in enumerate(urls, 1):
            console.print(f"  {i}. {url[:60]}...")
            webbrowser.open_new_tab(url)
            await asyncio.sleep(0.5)  # Small delay between opens
        
        console.print(f"\n[green]✓ Opened {len(urls)} search pages![/green]")
        console.print("\n[cyan]Now:[/cyan]")
        console.print("  1. Browse the opened tabs")
        console.print("  2. Copy URLs of interesting jobs")
        console.print("  3. Save to jobs.txt")
        console.print("  4. Run: py -m src.main batch --file jobs.txt --v2\n")
