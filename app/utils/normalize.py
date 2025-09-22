"""
Arabic text normalization utilities for consistent data processing.
"""
import re
import unicodedata
from typing import Union


def normalize_ar(text: str) -> str:
    """
    Normalize Arabic text for consistent comparison and storage.
    
    Rules:
    - أ/إ/آ → ا (alif variations to standard alif)
    - ى → ي (alif maqsura to ya)
    - Remove diacritics (tashkeel)
    - Remove tatweel (kashida)
    - Normalize whitespace
    - Convert to lowercase
    
    Args:
        text: Input Arabic text
        
    Returns:
        Normalized Arabic text
    """
    if not text:
        return ""
    
    # Convert to string if not already
    text = str(text)
    
    # Replace alif variations with standard alif (before NFD)
    text = re.sub(r'[أإآ]+', 'ا', text)
    
    # Replace alif maqsura with ya
    text = re.sub(r'ى', 'ي', text)
    
    # Normalize Unicode (NFD decomposition)
    text = unicodedata.normalize('NFD', text)
    
    # Remove diacritics (tashkeel) - keep only base characters
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Remove tatweel (kashida) and other formatting characters
    text = re.sub(r'[\u0640\u200B\u200C\u200D\uFEFF]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Convert to lowercase
    text = text.lower()
    
    return text


def normalize_mix(text: str) -> str:
    """
    Normalize mixed Arabic/English text for search and comparison.
    
    Handles:
    - Arabic normalization
    - English case normalization
    - Mixed token separation
    - Number normalization
    
    Args:
        text: Input mixed text
        
    Returns:
        Normalized mixed text
    """
    if not text:
        return ""
    
    text = str(text)
    
    # Split into tokens
    tokens = re.findall(r'[\u0600-\u06FF]+|[a-zA-Z0-9-]+', text)
    
    normalized_tokens = []
    for token in tokens:
        if re.match(r'[\u0600-\u06FF]+', token):
            # Arabic token
            normalized_tokens.append(normalize_ar(token))
        elif re.match(r'[a-zA-Z0-9-]+', token):
            # English/numeric token
            normalized_tokens.append(token.lower())
    
    return ' '.join(normalized_tokens)


def extract_car_info(text: str) -> dict:
    """
    Extract car make and model from mixed text.
    
    Args:
        text: Input text containing car information
        
    Returns:
        Dict with 'make' and 'model' keys
    """
    if not text:
        return {'make': '', 'model': ''}
    
    normalized = normalize_mix(text)
    
    # Common car makes in Arabic and English
    makes = {
        'تويوتا': 'toyota',
        'toyota': 'toyota',
        'هونداي': 'hyundai',
        'hyundai': 'hyundai',
        'هوندا': 'honda',
        'honda': 'honda',
        'نيسان': 'nissan',
        'nissan': 'nissan',
        'كيا': 'kia',
        'kia': 'kia',
        'مرسيدس': 'mercedes',
        'mercedes': 'mercedes',
        'بي ام دبليو': 'bmw',
        'bmw': 'bmw',
        'أودي': 'audi',
        'اودي': 'audi',
        'audi': 'audi',
        'فولكس فاجن': 'volkswagen',
        'volkswagen': 'volkswagen',
        'vw': 'volkswagen',
        'فورد': 'ford',
        'ford': 'ford',
        'شيفروليه': 'chevrolet',
        'chevrolet': 'chevrolet',
        'شيفي': 'chevrolet',
        'جي ام سي': 'gmc',
        'gmc': 'gmc',
        'لاند روفر': 'landrover',
        'landrover': 'landrover',
        'جيب': 'jeep',
        'jeep': 'jeep',
    }
    
    # Find make
    found_make = ''
    for arabic_make, english_make in makes.items():
        if arabic_make in normalized or english_make in normalized:
            found_make = english_make
            break
    
    # Extract model (everything after the make)
    model = ''
    if found_make:
        # Remove the make from the text
        for arabic_make, english_make in makes.items():
            if arabic_make in normalized:
                normalized = normalized.replace(arabic_make, '')
            if english_make in normalized:
                normalized = normalized.replace(english_make, '')
        
        # Clean up and get the model
        model = normalized.strip()
    else:
        # If no make found, return the original normalized text as model
        model = normalized.strip()
    
    return {
        'make': found_make,
        'model': model
    }


def is_arabic(text: str) -> bool:
    """
    Check if text contains Arabic characters.
    
    Args:
        text: Input text
        
    Returns:
        True if text contains Arabic characters
    """
    if not text:
        return False
    
    return bool(re.search(r'[\u0600-\u06FF]', text))


def is_english(text: str) -> bool:
    """
    Check if text contains only English characters.
    
    Args:
        text: Input text
        
    Returns:
        True if text contains only English characters
    """
    if not text or not text.strip():
        return False
    
    return bool(re.match(r'^[a-zA-Z0-9\s]+$', text))


def clean_phone_number(phone: str) -> str:
    """
    Clean and normalize phone number.
    
    Args:
        phone: Input phone number
        
    Returns:
        Cleaned phone number
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Handle Saudi phone numbers
    if cleaned.startswith('+966'):
        return cleaned
    elif cleaned.startswith('966'):
        return '+' + cleaned
    elif cleaned.startswith('0'):
        return '+966' + cleaned[1:]
    elif len(cleaned) == 9 and cleaned.startswith('5'):
        return '+966' + cleaned
    
    return cleaned


def normalize_city_name(city_name: str) -> str:
    """
    Normalize city names for consistent matching.
    
    Args:
        city_name: Input city name
        
    Returns:
        Normalized city name
    """
    if not city_name or not city_name.strip():
        return ""
    
    # Common city name variations
    city_mappings = {
        'الرياض': 'riyadh',
        'riyadh': 'riyadh',
        'جدة': 'jeddah',
        'jeddah': 'jeddah',
        'مكة': 'makkah',
        'makkah': 'makkah',
        'مكة المكرمة': 'makkah',
        'الدمام': 'dammam',
        'dammam': 'dammam',
        'الخبر': 'khobar',
        'khobar': 'khobar',
        'الظهران': 'dhahran',
        'dhahran': 'dhahran',
        'الطائف': 'taif',
        'taif': 'taif',
        'بريدة': 'buraidah',
        'buraidah': 'buraidah',
        'تبوك': 'tabuk',
        'tabuk': 'tabuk',
        'حائل': 'hail',
        'hail': 'hail',
        'نجران': 'najran',
        'najran': 'najran',
        'الباحة': 'albaha',
        'albaha': 'albaha',
        'الجوف': 'jouf',
        'jouf': 'jouf',
        'عرعر': 'arar',
        'arar': 'arar',
        'سكاكا': 'sakaka',
        'sakaka': 'sakaka',
    }
    
    normalized = normalize_mix(city_name)
    
    for arabic_name, english_name in city_mappings.items():
        if arabic_name in normalized or english_name in normalized:
            return english_name
    
    # If no mapping found, return the normalized version or original if empty
    return normalized if normalized else city_name.lower()
