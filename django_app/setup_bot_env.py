#!/usr/bin/env python
"""
Script to help setup bot environment variables
"""
import os

def setup_environment():
    """Setup environment variables for the bot"""
    print("🤖 Telegram Bot Environment Setup")
    print("=" * 40)
    
    # Check if token is already set
    current_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if current_token:
        print(f"✅ Bot token is already set: {current_token[:10]}...")
        use_current = input("Use current token? (y/n): ").lower().strip()
        if use_current == 'y':
            return current_token
    
    # Get token from user
    print("\n📝 Please enter your Telegram Bot Token:")
    print("   (Get it from @BotFather on Telegram)")
    token = input("Token: ").strip()
    
    if not token:
        print("❌ No token provided!")
        return None
    
    # Validate token format (basic check)
    if not token.count(':') == 1 or len(token) < 40:
        print("❌ Invalid token format!")
        return None
    
    # Set environment variable for current session
    os.environ['TELEGRAM_BOT_TOKEN'] = token
    
    # Create .env file for persistence
    env_file = '.env'
    env_content = f"TELEGRAM_BOT_TOKEN={token}\nDEBUG=True\n"
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print(f"✅ Token saved to {env_file}")
    except Exception as e:
        print(f"⚠️ Could not save to .env file: {e}")
    
    print(f"✅ Bot token configured: {token[:10]}...")
    return token

def check_bot_token():
    """Check if bot token is configured"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if token:
        print(f"✅ Bot token is configured: {token[:10]}...")
        return True
    else:
        print("❌ Bot token is not configured!")
        return False

if __name__ == "__main__":
    setup_environment()
