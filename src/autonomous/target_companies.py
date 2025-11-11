"""
🎯 TARGET COMPANIES
Curated list of AI/ML companies and startups hiring for Elena's target roles.
These companies use Greenhouse, Workable, or have careers pages we can monitor.
"""

# 🔥 HOT AI COMPANIES (Greenhouse)
GREENHOUSE_COMPANIES = [
    # Major AI companies
    'openai',
    'anthropic',
    'huggingface',
    'cohere',
    'stability',
    'replicate',
    
    # AI Infrastructure
    'modal',
    'together',
    'anyscale',
    'weights-biases',
    'scale',
    
    # AI Products
    'jasper',
    'copy-ai',
    'writesonic',
    'synthesia',
    'runway',
    
    # Search & Data
    'perplexity',
    'glean',
    'hebbia',
    
    # LLM Ops & Dev Tools
    'langchain',
    'pinecone',
    'weaviate',
    'chroma',
    
    # AI Agents & Automation
    'adept',
    'dust',
    'fixie',
]

# 🚀 STARTUPS (Workable)
WORKABLE_COMPANIES = [
    'midjourney',
    'character',
    'inflection',
]

# 🦄 YC BATCH COMPANIES TO MONITOR
YC_AI_COMPANIES = [
    # W25 Batch
    'w25-ai-startup-1',
    'w25-ai-startup-2',
    
    # S25 Batch (will be updated)
    's25-ai-startup-1',
]

# 🌐 WEB3 + AI HYBRID COMPANIES
WEB3_AI_COMPANIES = [
    'ritual',
    'gensyn',
    'fetch-ai',
    'ocean-protocol',
    'akash',
]

# 📚 CURATED STARTUP LIST (From your network/research)
# Add companies you discover from:
# - YC directories
# - Twitter/X announcements
# - Hacker News launches
# - Personal network
CURATED_STARTUPS = [
    # Add manually discovered companies here
    # Format: 'company-slug-for-careers-page'
]


def get_all_target_companies():
    """Get complete list of target companies"""
    return {
        'greenhouse': GREENHOUSE_COMPANIES,
        'workable': WORKABLE_COMPANIES,
        'yc': YC_AI_COMPANIES,
        'web3': WEB3_AI_COMPANIES,
        'curated': CURATED_STARTUPS,
    }


def get_greenhouse_url(company_slug: str) -> str:
    """Get Greenhouse careers URL for company"""
    return f"https://boards.greenhouse.io/{company_slug}"


def get_workable_url(company_slug: str) -> str:
    """Get Workable careers URL for company"""
    return f"https://apply.workable.com/{company_slug}/"


def get_lever_url(company_slug: str) -> str:
    """Get Lever careers URL for company"""
    return f"https://jobs.lever.co/{company_slug}"


# 💡 HOW TO EXPAND THIS LIST:
"""
1. Browse YC companies: ycombinator.com/companies
2. Check who's hiring on Twitter: Search "YC [W25] hiring"
3. Monitor Hacker News: news.ycombinator.com
4. Check Web3 job boards: web3.career
5. Browse AI company lists: aimojo.ai, ai-startups.org
6. Add any company you discover to CURATED_STARTUPS
"""
