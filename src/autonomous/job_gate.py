"""
🛡️ JOB GATE - Career-Aligned Filtering
Works with REAL ATS data (not hypothetical metadata)

STRATEGY:
- Filter based on title + description keywords (data we HAVE)
- Exclude junior/intern/sales roles
- Prioritize remote-friendly positions
- Filter by salary (when available)
- Filter by company size (when available)
- Let high-quality scoring happen in job_matcher.py
"""

from typing import Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

# ─────────────────────────────
# KEYWORDS (Based on Elena's target roles)
# ─────────────────────────────

ROLE_INCLUDE_KEYWORDS = {
    # Primary targets (CAREER_FOCUS Section 3 — green roles)
    "founding", "founder", "co-founder",
    "ai automation", "automation specialist",
    "internal tools", "ai tools",
    "ai integration", "integration engineer",
    "ai ops", "ai program", "applied ai", "ai builder",
    "product engineer", "platform engineer",
    "full stack", "fullstack", "full-stack",
    "solutions architect", "ai architect",
    # Secondary — only early-stage / founder-led
    "software engineer", "backend engineer",
    "automation", "infrastructure", "infra",
    "llm", "nlp",
    "product manager", "growth engineer",
    "fractional", "consultant",
}

ROLE_EXCLUDE_KEYWORDS = {
    # Never apply (CAREER_FOCUS Section 3 — red roles + Section 5 hard gates)
    "junior", "intern", "internship", "entry level", "entry-level",
    "senior engineer", "senior software", "senior ai engineer",
    "senior ml", "senior machine learning", "senior backend",
    "staff engineer", "staff software",
    "principal engineer", "principal software",
    "ml engineer", "machine learning engineer",
    "data scientist",
    "sales", "recruiter", "recruiting", "hr ",
    "customer success", "account manager", "account executive",
    "phd required", "doctorate required",
    "director of sales", "vp sales",
    "legal counsel", "general counsel",
    "executive assistant", "administrative",
    "microsoft 365", "power platform", "sharepoint",
}

# ─────────────────────────────
# LARGE COMPANY BLOCKLIST (Golden Roadmap: reject 20+ engineers)
# These companies have 1000+ employees - auto-reject
# ─────────────────────────────
LARGE_COMPANY_BLOCKLIST = {
    # Big Tech
    "google", "meta", "facebook", "amazon", "aws", "microsoft", "apple",
    "netflix", "nvidia", "intel", "amd", "ibm", "oracle", "sap", "salesforce",
    "adobe", "vmware", "cisco", "qualcomm", "broadcom",
    # Large Data/Cloud Companies
    "databricks", "snowflake", "palantir", "splunk", "elastic",
    "datadog", "mongodb", "confluent", "cloudera", "teradata",
    # Large SaaS/Product Companies (500+ employees)
    "figma", "notion", "airtable", "dropbox", "twilio", "okta", "zoom",
    "slack", "atlassian", "asana", "monday", "zendesk", "hubspot",
    "docusign", "servicenow", "workday", "splunk", "pagerduty",
    # Large Fintech (1000+ employees)
    "stripe", "plaid", "square", "block", "paypal", "visa", "mastercard",
    "robinhood", "coinbase", "kraken", "brex", "ramp", "mercury",
    "chime", "sofi", "affirm", "klarna", "revolut",
    # Large AI Companies (established, not startups)
    "openai", "anthropic", "deepmind", "cohere",  # These are elite but large now
    # Consulting/Enterprise/Staffing
    "accenture", "deloitte", "mckinsey", "bcg", "bain", "kpmg", "pwc", "ey",
    "capgemini", "infosys", "wipro", "tcs", "cognizant",
    # Indian IT staffing / body shops (frequent ATS noise, not product companies)
    "siro clinpharm", "nagarro", "codeforce360",
    "akaasa", "xforia", "verito", "argyll",
    "sr partners",
}

LOCATION_INCLUDE_KEYWORDS = {
    "remote", "anywhere", "global", "worldwide",
    "latam", "latin america", "americas",
    "panama", "usa", "united states", "us-",
}

# ─────────────────────────────
# SALARY FLOORS (Annual)
# ─────────────────────────────
SALARY_FLOORS = {
    "us": 42000,       # $3,500/mo hard floor (CAREER_FOCUS Section 4)
    "eu": 36000,       # ~€3K/mo equivalent
    "uk": 30000,       # ~£2.5K/mo equivalent
    "latam": 30000,    # $2,500/mo (CAREER_FOCUS: $2.5K–4.5K/mo startup range)
    "remote": 36000,   # $3K/mo — reject below hard floor
}

# ─────────────────────────────
# COMPANY SIZE LIMITS
# ─────────────────────────────
MAX_ENGINEERING_TEAM_SIZE = 20  # Reject if >20 engineers (too established)
MAX_TOTAL_EMPLOYEES = 150       # Reject if >150 total (too large)


class JobGate:
    """
    🛡️ HARD career gate for Elena's job search.
    
    Uses PRACTICAL filtering based on data ATS APIs actually provide:
    - Job title keywords
    - Job description keywords
    - Location compatibility
    - Salary minimums (when available)
    - Company size (when available)
    """

    @staticmethod
    def _extract_salary(job: Dict) -> Optional[int]:
        """
        Extract salary from job data.
        Returns annual salary in USD equivalent (or None if not available).
        """
        # Direct salary fields
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")
        compensation = job.get("compensation") or job.get("salary") or ""
        
        # If we have numeric fields, use them
        if salary_min and isinstance(salary_min, (int, float)):
            return int(salary_min)
        if salary_max and isinstance(salary_max, (int, float)):
            return int(salary_max * 0.8)  # Use 80% of max as proxy
        
        # Try to parse compensation string
        if compensation and isinstance(compensation, str):
            # Remove common symbols and normalize
            comp_clean = compensation.replace(",", "").replace("$", "").replace("€", "").replace("£", "").lower()
            
            # Look for patterns like "150k-200k", "150000", "150k"
            matches = re.findall(r'(\d+)k|\b(\d{5,})\b', comp_clean)
            
            if matches:
                numbers = []
                for m in matches:
                    if m[0]:  # "150k" pattern
                        numbers.append(int(m[0]) * 1000)
                    elif m[1]:  # "150000" pattern
                        numbers.append(int(m[1]))
                
                if numbers:
                    return min(numbers)  # Use minimum for floor check
        
        # Try description for salary info
        description = (job.get("description") or "").lower()
        salary_patterns = [
            r'\$(\d{2,3})k',  # $150k
            r'\$(\d{3},?\d{3})',  # $150,000
            r'€(\d{2,3})k',  # €90k
            r'£(\d{2,3})k',  # £80k
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, description)
            if match:
                num = match.group(1).replace(",", "")
                if "k" in pattern:
                    return int(num) * 1000
                return int(num)
        
        return None
    
    @staticmethod
    def _get_salary_floor(location: str) -> int:
        """Get the appropriate salary floor based on location."""
        location = location.lower()
        
        if any(loc in location for loc in ["united states", "usa", "us-", "new york", "san francisco", "california", "texas"]):
            return SALARY_FLOORS["us"]
        elif any(loc in location for loc in ["uk", "united kingdom", "london", "england"]):
            return SALARY_FLOORS["uk"]
        elif any(loc in location for loc in ["eu", "europe", "germany", "france", "netherlands", "spain", "berlin", "paris"]):
            return SALARY_FLOORS["eu"]
        elif any(loc in location for loc in ["latam", "latin america", "mexico", "brazil", "argentina", "panama", "colombia"]):
            return SALARY_FLOORS["latam"]
        else:
            return SALARY_FLOORS["remote"]  # Default for remote/unknown
    
    @staticmethod
    def _check_company_size(job: Dict) -> bool:
        """
        Check if company size is acceptable.
        Returns True if acceptable or unknown, False if too large.
        """
        # Check for company_size field
        company_size = job.get("company_size") or job.get("team_size") or ""
        
        if isinstance(company_size, str):
            company_size_lower = company_size.lower()
            
            # Parse ranges like "51-200", "201-500", "11-50"
            range_match = re.search(r'(\d+)-(\d+)', company_size)
            if range_match:
                lower, upper = int(range_match.group(1)), int(range_match.group(2))
                # For engineering team: reject if lower bound > 20
                # For total company: reject if lower bound > 150
                if lower > MAX_TOTAL_EMPLOYEES:
                    return False
            
            # Parse descriptive sizes
            too_large_indicators = ["500+", "1000+", "enterprise", "10000+", "5000+"]
            if any(ind in company_size_lower for ind in too_large_indicators):
                return False
                
        elif isinstance(company_size, (int, float)):
            if company_size > MAX_TOTAL_EMPLOYEES:
                return False
        
        # Check description for team size hints
        description = (job.get("description") or "").lower()
        
        # Look for "team of X engineers" patterns
        team_patterns = [
            r'team of (\d+)\+? engineers',
            r'(\d+)\+? person engineering',
            r'engineering team.*?(\d+) people',
        ]
        
        for pattern in team_patterns:
            match = re.search(pattern, description)
            if match:
                team_size = int(match.group(1))
                if team_size > MAX_ENGINEERING_TEAM_SIZE:
                    return False
        
        # Default: pass (no info means we give benefit of doubt)
        return True
    
    @staticmethod
    def _check_company_stage(job: Dict) -> bool:
        """
        Check if company stage is acceptable (Seed to Series B preferred).
        Returns True if acceptable or unknown, False if too late stage.
        """
        description = (job.get("description") or "").lower()
        company_info = (job.get("company_info") or "").lower()
        combined = f"{description} {company_info}"
        
        # Too late stage indicators
        late_stage = ["series d", "series e", "series f", "ipo", "public company", "fortune 500"]
        for indicator in late_stage:
            if indicator in combined:
                return False
        
        # Preferred stage indicators (bonus, not rejection)
        # early_stage = ["seed", "series a", "series b", "pre-seed", "yc", "y combinator"]
        # We don't reject based on early stage, but could boost score in matcher
        
        return True

    @staticmethod
    def passes(job: Dict) -> bool:
        """
        Returns True if job should proceed to scoring.
        Returns False if job should be immediately discarded.
        """
        title = (job.get("title") or "").lower()
        description = (job.get("description") or job.get("raw_text") or "").lower()
        location = (job.get("location") or "").lower()
        company = (job.get("company") or "").lower()
        
        combined_text = f"{title} {description}"
        
        # ─────────────────────────────
        # 0️⃣ BLOCKLIST large companies (instant reject)
        # Golden Roadmap: No companies with 20+ engineers
        # ─────────────────────────────
        for blocked in LARGE_COMPANY_BLOCKLIST:
            if blocked in company:
                logger.debug(f"❌ GATE REJECT (blocklisted company '{blocked}'): {company} - {title[:40]}")
                return False
        
        # ─────────────────────────────
        # 1️⃣ EXCLUDE bad roles (instant reject)
        # ─────────────────────────────
        for exclude_kw in ROLE_EXCLUDE_KEYWORDS:
            if exclude_kw in title:
                logger.debug(f"❌ GATE REJECT (excluded keyword '{exclude_kw}'): {title[:50]}")
                return False
        
        # ─────────────────────────────
        # 2️⃣ REQUIRE at least one relevant keyword
        # ─────────────────────────────
        has_relevant_keyword = any(kw in combined_text for kw in ROLE_INCLUDE_KEYWORDS)
        
        if not has_relevant_keyword:
            logger.debug(f"❌ GATE REJECT (no relevant keywords): {title[:50]}")
            return False
        
        # ─────────────────────────────
        # 3️⃣ CHECK location compatibility
        # ─────────────────────────────
        # If location is specified, check if it's compatible
        if location:
            is_remote_friendly = any(loc in location for loc in LOCATION_INCLUDE_KEYWORDS)
            
            # Reject if explicitly on-site in incompatible locations
            if not is_remote_friendly:
                incompatible_locations = ["london", "new york", "san francisco", "berlin", "paris", "tokyo"]
                for bad_loc in incompatible_locations:
                    if bad_loc in location and "remote" not in location:
                        logger.debug(f"❌ GATE REJECT (incompatible location '{location}'): {title[:50]}")
                        return False
        
        # ─────────────────────────────
        # 4️⃣ CHECK salary floor (if salary data available)
        # ─────────────────────────────
        salary = JobGate._extract_salary(job)
        if salary is not None:
            floor = JobGate._get_salary_floor(location)
            if salary < floor:
                logger.debug(f"❌ GATE REJECT (salary ${salary:,} < ${floor:,} floor): {title[:50]}")
                return False
        
        # ─────────────────────────────
        # 5️⃣ CHECK company size (if data available)
        # ─────────────────────────────
        if not JobGate._check_company_size(job):
            company = job.get("company", "Unknown")
            logger.debug(f"❌ GATE REJECT (company too large): {company} - {title[:50]}")
            return False
        
        # ─────────────────────────────
        # 6️⃣ CHECK company stage (if data available)
        # ─────────────────────────────
        if not JobGate._check_company_stage(job):
            company = job.get("company", "Unknown")
            logger.debug(f"❌ GATE REJECT (company too late stage): {company} - {title[:50]}")
            return False
        
        # ─────────────────────────────
        # ✅ PASSED - Proceed to scoring
        # ─────────────────────────────
        logger.debug(f"✅ GATE PASSED: {title[:50]}")
        return True
    
    @staticmethod
    def get_gate_stats(jobs: list) -> Dict:
        """Get statistics about gate filtering"""
        passed = sum(1 for j in jobs if JobGate.passes(j))
        return {
            "total": len(jobs),
            "passed": passed,
            "rejected": len(jobs) - passed,
            "pass_rate": f"{(passed/len(jobs)*100):.1f}%" if jobs else "0%"
        }
    
    @staticmethod
    def get_rejection_reasons(jobs: list) -> Dict:
        """Get breakdown of rejection reasons for debugging"""
        reasons = {
            "excluded_keyword": 0,
            "no_relevant_keywords": 0,
            "bad_location": 0,
            "low_salary": 0,
            "company_too_large": 0,
            "late_stage": 0,
            "passed": 0,
        }
        
        for job in jobs:
            title = (job.get("title") or "").lower()
            description = (job.get("description") or "").lower()
            location = (job.get("location") or "").lower()
            combined_text = f"{title} {description}"
            
            # Check exclusions
            excluded = False
            for exclude_kw in ROLE_EXCLUDE_KEYWORDS:
                if exclude_kw in title:
                    reasons["excluded_keyword"] += 1
                    excluded = True
                    break
            if excluded:
                continue
                
            # Check relevance
            has_relevant = any(kw in combined_text for kw in ROLE_INCLUDE_KEYWORDS)
            if not has_relevant:
                reasons["no_relevant_keywords"] += 1
                continue
            
            # Check location
            if location:
                is_remote_friendly = any(loc in location for loc in LOCATION_INCLUDE_KEYWORDS)
                if not is_remote_friendly:
                    incompatible = ["london", "new york", "san francisco", "berlin", "paris", "tokyo"]
                    for bad_loc in incompatible:
                        if bad_loc in location and "remote" not in location:
                            reasons["bad_location"] += 1
                            break
                    else:
                        continue
                    continue
            
            # Check salary
            salary = JobGate._extract_salary(job)
            if salary is not None:
                floor = JobGate._get_salary_floor(location)
                if salary < floor:
                    reasons["low_salary"] += 1
                    continue
            
            # Check company size
            if not JobGate._check_company_size(job):
                reasons["company_too_large"] += 1
                continue
            
            # Check stage
            if not JobGate._check_company_stage(job):
                reasons["late_stage"] += 1
                continue
            
            reasons["passed"] += 1
        
        return reasons
