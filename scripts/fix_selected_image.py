import os,sys,shutil

src = "src/notifications/linkedin_cmo_v4.py"
bak = src + ".bak"

if not os.path.exists(src):
    print("ERROR: source file not found:", src); sys.exit(1)

shutil.copyfile(src, bak)
print("Backup created:", bak)

s = open(src, "r", encoding="utf-8").read()

start_marker = "image_urls = {"
payload_marker = "payload = {"

a = s.find(start_marker)
b = s.find(payload_marker, a if a!=-1 else 0)
if a == -1 or b == -1:
    print("ERROR: could not find expected markers in file"); sys.exit(1)

new_block = """
            image_urls = {
                "open_to_work": "https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main/image_1.png",
                "technical_showcase": "https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main/image_1.png",
                "transformation_story": "https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main/image_1.png",
                "seeking_funding": "https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main/image_1.png",
                "busco_trabajo": "https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main/image_1.1.jpeg",
                "historia_transformacion": "https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main/image_1.1.jpeg"
            }

            # Choose image based on post type (fallback to first available)
            selected_image = image_urls.get(post_content.get(\"type\")) or next(iter(image_urls.values()))
            # Persist last chosen image for anti-repeat behavior
            try:
                self.strategy_data[\"last_image\"] = selected_image
                self._save_json(self.strategy_file, self.strategy_data)
            except Exception:
                # Non-fatal: if saving fails, continue using selected_image
                pass

            logger.info(f\"Selected image for post: {selected_image}\")
"""

s2 = s[:a] + new_block + s[b:]
open(src, "w", encoding="utf-8").write(s2)
print("Patched:", src)
