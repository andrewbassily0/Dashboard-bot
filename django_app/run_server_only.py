#!/usr/bin/env python
"""
Simple script to run Django server only
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_parts_bot.settings')
django.setup()

from django.core.management import execute_from_command_line

if __name__ == "__main__":
    execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8000'])
