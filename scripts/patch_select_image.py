import sys, shutil, os

src = "src/notifications/linkedin_cmo_v4.py"
bak = src + ".bak"

if not os.path.exists(src):
    print("ERROR: source file not found:", src)
    sys.exit(1)

shutil.copyfile(src, bak)
print("Backup created:", bak)

s = open(src, "r", encoding="utf-8").read()

img_pos = s.find("image_urls = {")
if img_pos == -1:
    print("ERROR: 'image_urls = {' marker not found")
    sys.exit(1)

payload_pos = s.find("payload = {", img_pos)
if payload_pos == -1:
    print("ERROR: 'payload = {' marker not found after image_urls")
    sys.exit(1)

insertion = (
    "\n            # Choose image based on post type (fallback to english image)\n"
    "            try:\n"
    "                selected_image = image_urls.get(post_content.get(\"type\"), image_urls.get(\"open_to_work\"))\n"
    "            except Exception:\n"
    "                # fallback to first available or default image\n"
    "                selected_image = (list(image_urls.values())[0] if isinstance(image_urls, dict) and image_urls else \"https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main/image_1.png\")\n"
)

s2 = s[:payload_pos] + insertion + s[payload_pos:]
open(src, "w", encoding="utf-8").write(s2)

print("Patched file:", src)
