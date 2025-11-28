import asyncio
from src.notifications.linkedin_cmo_v4 import LinkedInCMO

async def test_image_rotation():
    print("\n TESTING IMAGE ROTATION \n")
    
    cmo = LinkedInCMO()
    
    # Simulate 5 posts to see image variety
    for i in range(5):
        print(f"\n--- Test Post {i+1} ---")
        
        # Generate post (this selects random image)
        post_content = await cmo.generate_linkedin_post("random", "en")
        
        print(f"Post type: {post_content['type']}")
        print(f"Language: {post_content['language']}")
        print(f"AI generated: {post_content.get('ai_generated', False)}")
        
        # Don't actually send, just show what would be selected
        # The image selection happens in send_to_make_com
        print(" Would select random image from 11 available")

if __name__ == "__main__":
    asyncio.run(test_image_rotation())
