#!/usr/bin/env python3
"""
Quick setup script for VibeJobHunter
"""
import os
import sys
from pathlib import Path


def main():
    print("🚀 VibeJobHunter Setup")
    print("=" * 50)
    print()
    
    base_dir = Path(__file__).parent
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        print(f"   Current version: {sys.version}")
        return 1
    
    print("✓ Python version OK")
    
    # Check if requirements are installed
    try:
        import anthropic
        import pydantic
        import click
        print("✓ Dependencies installed")
    except ImportError as e:
        print(f"⚠️  Missing dependency: {e.name}")
        print("   Run: pip install -r requirements.txt")
        return 1
    
    # Check .env file
    env_file = base_dir / ".env"
    if not env_file.exists():
        print("⚠️  No .env file found")
        print("   Creating from template...")
        
        env_example = base_dir / ".env.example"
        with open(env_example, 'r') as src:
            with open(env_file, 'w') as dst:
                dst.write(src.read())
        
        print("✓ Created .env file")
        print()
        print("📝 IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY")
        print("   Get it from: https://console.anthropic.com/")
        print()
        
        # Prompt for API key
        api_key = input("Enter your Anthropic API key (or press Enter to skip): ").strip()
        if api_key:
            with open(env_file, 'r') as f:
                content = f.read()
            content = content.replace(
                'ANTHROPIC_API_KEY=your_anthropic_api_key_here',
                f'ANTHROPIC_API_KEY={api_key}'
            )
            with open(env_file, 'w') as f:
                f.write(content)
            print("✓ API key saved")
    else:
        print("✓ .env file exists")
    
    # Check for resume
    print()
    resume_files = list(base_dir.glob("*.pdf"))
    if resume_files:
        print(f"✓ Found resume: {resume_files[0].name}")
        
        create_profile = input("\nCreate profile now? (y/n): ").strip().lower()
        if create_profile == 'y':
            print()
            print("Creating profile...")
            os.system(f'python -m src.main setup --resume "{resume_files[0]}"')
    else:
        print("⚠️  No PDF resume found")
        print("   Add your resume.pdf to this directory")
    
    # Create directories
    print()
    print("Creating data directories...")
    dirs = [
        "data/profiles",
        "data/jobs",
        "data/applications",
        "data/stats",
        "tailored_resumes",
        "cover_letters",
        "templates",
        "logs"
    ]
    for dir_path in dirs:
        (base_dir / dir_path).mkdir(parents=True, exist_ok=True)
    print("✓ Directories created")
    
    # Final instructions
    print()
    print("=" * 50)
    print("✨ Setup complete!")
    print()
    print("Next steps:")
    print("1. Ensure ANTHROPIC_API_KEY is set in .env")
    print("2. Run: python -m src.main setup --resume YOUR_RESUME.pdf")
    print("3. Run: python -m src.main search")
    print("4. Run: python -m src.main apply --top 5")
    print()
    print("Or use the interactive menu:")
    print("   ./run.sh")
    print()
    print("Read QUICKSTART.md for detailed instructions.")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
