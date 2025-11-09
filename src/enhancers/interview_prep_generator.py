"""
Interview prep auto-generator
Creates custom interview materials for each job
"""
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from ..core.models import JobPosting, Profile
from ..loaders import CandidateDataLoader


class InterviewPrepGenerator:
    """Generate custom interview prep materials"""
    
    def __init__(self):
        self.loader = CandidateDataLoader()
        self.prep_data = self.loader.get_interview_prep()
        self.prep_dir = Path.cwd() / "interview_prep"
        self.prep_dir.mkdir(exist_ok=True)
    
    def generate_prep_package(self, profile: Profile, job: JobPosting) -> str:
        """
        Generate complete interview prep package
        
        Args:
            profile: Candidate profile
            job: Target job posting
            
        Returns:
            Path to prep file
        """
        prep_content = self._build_prep_content(profile, job)
        
        # Save to file
        filename = f"{job.company}_{job.id[:8]}_interview_prep.md"
        filename = filename.replace(" ", "_").replace("/", "-")
        filepath = self.prep_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(prep_content)
        
        return str(filepath)
    
    def _build_prep_content(self, profile: Profile, job: JobPosting) -> str:
        """Build interview prep content"""
        
        # Get template answers
        questions = self.prep_data.get('questions_prep', {})
        talking_points = self.prep_data.get('talking_points', {})
        
        content = f"""# INTERVIEW PREP - {job.company}
**Role:** {job.title}
**Date:** {datetime.now().strftime('%Y-%m-%d')}

---

## 🎯 COMPANY RESEARCH

**Company:** {job.company}
**What they do:** {self._extract_company_focus(job)}
**Why you're interested:** 
- [Research their recent news, product launches, funding]
- [Understand their mission and values]
- [Know their tech stack and challenges]

**Key talking points about them:**
1. [Specific feature/product you admire]
2. [Their approach to AI/technology]
3. [Company culture alignment]

---

## 💬 STANDARD INTERVIEW QUESTIONS

### "Tell me about yourself"
{questions.get('tell_me_about_yourself', 'Default answer...')}

### "Why this company?"
I'm excited about {job.company} because [research 2-3 specific things]:
- [Reason 1 based on their product/mission]
- [Reason 2 based on their technology/approach]
- [Reason 3 based on cultural fit]

Your focus on {self._extract_company_focus(job)} aligns perfectly with my experience building {self._get_relevant_experience(profile, job)}.

### "What's your biggest achievement?"
{questions.get('biggest_achievement', 'Default answer...')}

**For this role specifically:**
{self._format_relevant_achievements(profile, job)}

### "Tell me about a technical challenge you faced"
{questions.get('technical_challenge', 'Default answer...')}

**If they ask about their tech stack:**
{self._format_tech_stack_experience(profile, job)}

### "Why are you leaving your current role?"
{questions.get('why_leave_current_role', 'Default answer...')}

### "What are your salary expectations?"
{questions.get('salary_expectations', 'Default answer...')}

---

## 🎓 TECHNICAL TALKING POINTS

**Highlight these technical strengths:**
{self._format_list(talking_points.get('technical', []))}

**Strategic talking points:**
{self._format_list(talking_points.get('strategic', []))}

**Execution talking points:**
{self._format_list(talking_points.get('execution', []))}

---

## ❓ QUESTIONS TO ASK THEM

**About the Role:**
- What does success look like in the first 30/60/90 days?
- What are the biggest challenges facing the team right now?
- How much ownership will I have over features/architecture?
- What's the typical sprint cycle and development process?

**About the Team:**
- Tell me about the engineering team structure
- Who would I be working most closely with?
- What's the balance between building new features vs maintenance?
- How does the team handle technical decisions?

**About the Company:**
- What's the company's AI/product roadmap for the next year?
- How do you measure success for this role?
- What's the growth path for this position?
- What do you love most about working here?

**About Culture:**
- How do you support professional development?
- What's the work-life balance like?
- How does the team collaborate (remote/hybrid)?
- What's the biggest challenge the company faces right now?

---

## 🎯 KEY MESSAGES TO EMPHASIZE

**Your Unique Value:**
1. **Speed of Execution:** Built 6 production apps in 7 months (10x faster)
2. **Capital Efficiency:** 98% cost reduction vs traditional development
3. **Strategic + Technical:** Rare combination of C-suite experience + full-stack skills
4. **Live Demo Advantage:** Working product at wa.me/50766623757
5. **Proven Track Record:** 50K+ lines of production code, 8+ AI integrations

**For {job.company} specifically:**
{self._format_company_specific_value(job)}

---

## 💰 COMPENSATION DISCUSSION

**Your target:** $100K-180K base + equity (0.5-3%)

**Script for salary discussion:**
"I'm looking for $100-180K base plus meaningful equity, depending on the role and company stage. Given my unique combination of 7 years C-suite strategic experience plus full-stack engineering skills, I believe this is fair market value. However, I'm flexible for the right opportunity, especially if there's significant equity upside."

**If they ask current compensation:**
"I'm currently focused on finding the right role rather than just compensation. I'm looking for [$X-Y range] which aligns with my experience and the value I can bring. What's the budget for this role?"

---

## ⚠️ RED FLAGS TO WATCH FOR

During the interview, watch for:
- Unclear role expectations or scope creep
- Unrealistic timelines without adequate resources
- No mention of equity or growth path
- Toxic culture signals (long hours emphasis, no work-life balance)
- Technical team too small or no senior engineers to learn from

---

## 🎬 BEFORE THE INTERVIEW

**Preparation checklist:**
- [ ] Research company thoroughly (recent news, product, team)
- [ ] Review this prep doc completely
- [ ] Prepare 2-3 specific stories about achievements
- [ ] Have demo ready (wa.me/50766623757)
- [ ] Prepare questions to ask them
- [ ] Review their tech stack and your relevant experience
- [ ] Practice answers out loud (seriously!)
- [ ] Get good night's sleep

**Technical prep if applicable:**
- [ ] Review relevant technologies from job description
- [ ] Prepare code samples if requested
- [ ] Review system design patterns
- [ ] Brush up on algorithms if needed

---

## 📞 AFTER THE INTERVIEW

**Follow-up checklist:**
- [ ] Send thank-you email within 24 hours
- [ ] Mention 1-2 specific things discussed
- [ ] Reiterate your interest
- [ ] Provide any requested materials
- [ ] Connect on LinkedIn if appropriate

---

## 🎯 CLOSING STRONG

**If they ask "Why should we hire you?":**

"You should hire me because I can deliver immediate value. I've already built what most candidates are still talking about - you can try my AI assistant right now at wa.me/50766623757. I combine strategic thinking from 7 years in the C-suite with hands-on execution - I ship 10x faster than traditional teams with 98% cost reduction. Most importantly, I'm passionate about {self._extract_company_focus(job)} and I see huge potential to help {job.company} {self._extract_company_goal(job)}."

**Remember:**
- Be confident but humble
- Show genuine enthusiasm
- Ask thoughtful questions
- Be yourself (you're awesome!)
- Follow up promptly

---

**Good luck! You've got this! 🚀**

---

*Generated: {datetime.now().strftime('%B %d, %Y')}*
*For: {job.company} - {job.title}*
"""
        
        return content
    
    def _extract_company_focus(self, job: JobPosting) -> str:
        """Extract what company focuses on"""
        desc_lower = job.description.lower()
        if 'ai' in desc_lower or 'machine learning' in desc_lower:
            return "AI/ML innovation"
        elif 'platform' in desc_lower:
            return "platform development"
        else:
            return "technology innovation"
    
    def _extract_company_goal(self, job: JobPosting) -> str:
        """Extract company goal"""
        desc_lower = job.description.lower()
        if 'scale' in desc_lower:
            return "scale your platform to millions of users"
        elif 'build' in desc_lower:
            return "build innovative products"
        else:
            return "achieve your ambitious goals"
    
    def _get_relevant_experience(self, profile: Profile, job: JobPosting) -> str:
        """Get relevant experience summary"""
        return "AI products that solve real problems for users"
    
    def _format_relevant_achievements(self, profile: Profile, job: JobPosting) -> str:
        """Format achievements relevant to job"""
        achievements = profile.key_achievements[:3]
        formatted = ""
        for ach in achievements:
            formatted += f"- {ach}\n"
        return formatted
    
    def _format_tech_stack_experience(self, profile: Profile, job: JobPosting) -> str:
        """Format tech stack experience"""
        job_text = job.description.lower()
        relevant_skills = []
        
        for skill in profile.skills:
            if skill.lower() in job_text:
                relevant_skills.append(skill)
        
        if relevant_skills:
            return f"I have production experience with: {', '.join(relevant_skills[:5])}"
        else:
            return "I'm proficient in your tech stack and can ramp up quickly."
    
    def _format_list(self, items: List[str]) -> str:
        """Format list of items"""
        return '\n'.join([f"- {item}" for item in items])
    
    def _format_company_specific_value(self, job: JobPosting) -> str:
        """Format company-specific value proposition"""
        return f"""- Can help you move fast and ship quickly
- Bring both strategic thinking and hands-on execution
- Already validated product-building capabilities
- Can contribute from day 1 with minimal ramp-up"""
