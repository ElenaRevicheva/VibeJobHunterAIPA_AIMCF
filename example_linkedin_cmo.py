"""
💼 LinkedIn CMO - Quick Example
Shows how to use the LinkedIn CMO for automated content generation
"""

import asyncio
import os
from src.notifications import LinkedInCMO


async def main():
    print("=" * 70)
    print("💼 LINKEDIN CMO - QUICK DEMO")
    print("=" * 70)
    
    # Initialize LinkedIn CMO
    # It will read MAKE_WEBHOOK_URL_LINKEDIN from .env
    cmo = LinkedInCMO(language='en')
    
    print(f"\nLinkedIn CMO Status:")
    print(f"  Enabled: {cmo.enabled}")
    print(f"  Language: {cmo.language}")
    
    if not cmo.enabled:
        print("\n⚠️  Note: Webhook not configured (posts won't be sent)")
        print("   Set MAKE_WEBHOOK_URL_LINKEDIN in .env to enable posting")
        print("   But we can still generate content for preview!\n")
    
    # Example 1: Preview an "Open to Work" post
    print("\n" + "=" * 70)
    print("📝 EXAMPLE 1: Open to Work Post (English)")
    print("=" * 70)
    
    preview_en = cmo.preview_post(
        post_type='open_to_work',
        language='en',
        role='Founding Engineer',
        experience='building AI automation tools for 3 years',
        skill_1='Build 0→1 products from scratch',
        skill_2='Lead technical architecture decisions',
        skill_3='Ship fast without compromising quality',
        strength_1='Full-stack expertise (Python, React, AI/ML)',
        strength_2='Product-minded engineering approach',
        strength_3='Proven startup experience',
        ideal_role='Founding Engineer at early-stage AI startup',
        location='Remote / San Francisco Bay Area',
        demo_link='https://wa.me/50766623757',
        role_hashtag='FoundingEngineer'
    )
    
    print("\n" + preview_en)
    
    # Example 2: Preview an Achievement post
    print("\n" + "=" * 70)
    print("📝 EXAMPLE 2: Achievement Post")
    print("=" * 70)
    
    preview_achievement = cmo.preview_post(
        post_type='achievement',
        language='en',
        achievement_description=(
            "Just launched VibeJobHunter - an AI-powered job search automation "
            "that finds, matches, and applies to jobs 24/7! 🚀"
        ),
        learning_1='Start with MVP and iterate based on real feedback',
        learning_2='Automate the repetitive, focus on the creative',
        learning_3='Ship early and ship often - speed matters',
        key_factor='Understanding the actual pain points of job seekers',
        demo_link='https://wa.me/50766623757',
        topic_1='AI',
        topic_2='Automation',
        topic_3='JobSearch'
    )
    
    print("\n" + preview_achievement)
    
    # Example 3: Preview a Demo Share post
    print("\n" + "=" * 70)
    print("📝 EXAMPLE 3: Demo Share Post")
    print("=" * 70)
    
    preview_demo = cmo.preview_post(
        post_type='demo_share',
        language='en',
        project_name='VibeJobHunter',
        description=(
            'An AI-powered autonomous job hunting engine that:\n'
            '• Monitors 50+ job boards 24/7\n'
            '• Matches opportunities with your profile\n'
            '• Generates personalized applications\n'
            '• Tracks responses and schedules interviews'
        ),
        tech_1='Python + Claude AI',
        tech_2='Telegram Bot API',
        tech_3='Multi-channel outreach (LinkedIn, Email, Twitter)',
        motivation='Help people find their dream jobs without the manual grind',
        demo_link='https://wa.me/50766623757',
        topic_1='AI',
        topic_2='JobSearch',
        topic_3='Automation'
    )
    
    print("\n" + preview_demo)
    
    # Example 4: Spanish version
    print("\n" + "=" * 70)
    print("📝 EXAMPLE 4: Open to Work Post (Spanish)")
    print("=" * 70)
    
    cmo_es = LinkedInCMO(language='es')
    preview_es = cmo_es.preview_post(
        post_type='open_to_work',
        role='Founding Engineer',
        experience='construyendo herramientas de automatización con IA',
        demo_link='https://wa.me/50766623757'
    )
    
    print("\n" + preview_es)
    
    # Show stats
    print("\n" + "=" * 70)
    print("📊 LINKEDIN CMO STATISTICS")
    print("=" * 70)
    
    stats = cmo.get_stats()
    print(f"\nPosts sent: {stats['posts_sent']}")
    print(f"Webhook configured: {stats['webhook_configured']}")
    print(f"Enabled: {stats['enabled']}")
    
    # Example of actually posting (only if webhook is configured)
    if cmo.enabled:
        print("\n" + "=" * 70)
        print("📤 SENDING POST TO LINKEDIN (via Make.com)")
        print("=" * 70)
        
        response = input("\n⚠️  This will actually post to LinkedIn. Continue? (y/n): ")
        
        if response.lower() == 'y':
            success = await cmo.post_open_to_work(
                role='Founding Engineer',
                experience='building AI automation tools',
                demo_link='https://wa.me/50766623757'
            )
            
            if success:
                print("\n✅ Post sent successfully!")
            else:
                print("\n❌ Failed to send post. Check logs.")
    else:
        print("\n💡 To enable posting:")
        print("   1. Get webhook URL from Make.com")
        print("   2. Add to .env: MAKE_WEBHOOK_URL_LINKEDIN=https://hook.us2.make.com/...")
        print("   3. Run this script again")
    
    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETE!")
    print("=" * 70)
    print("\nCheck LINKEDIN_CMO_GUIDE.md for detailed documentation.")
    print("The LinkedIn CMO is ready to use! 🚀")


if __name__ == "__main__":
    asyncio.run(main())
