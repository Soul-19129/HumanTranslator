#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HumanTranslator - Utility Functions
==================================

Shared helpers for validation, logging, and convenience utilities.

Author: Soul-19129
License: MIT
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

# googletrans language map is used in translator module; to avoid a hard dependency here,
# we allow passing a fallback language list if needed.
try:
    from googletrans import LANGUAGES as GOOGLE_LANGUAGES
except Exception:
    GOOGLE_LANGUAGES = {}

logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

LANG_CACHE_FILE = os.path.join('logs', 'languages_cache.json')
TRANSLATION_LOG_FILE = os.path.join('logs', 'translations.log')


def validate_language_code(code: str) -> bool:
    """
    Validate language code presence in googletrans LANGUAGES mapping
    """
    if not code or len(code) < 2:
        return False
    code = code.lower().strip()
    if GOOGLE_LANGUAGES:
        return code in GOOGLE_LANGUAGES
    # Fallback: accept ISO-like two-letter codes when map not available
    return len(code) in (2, 3)


def get_supported_languages() -> Dict[str, str]:
    """
    Return supported languages mapping, caching to file for quick reuse
    """
    try:
        if GOOGLE_LANGUAGES:
            langs = GOOGLE_LANGUAGES
        else:
            langs = {
                'en': 'English', 'ar': 'Arabic', 'fr': 'French', 'es': 'Spanish',
                'de': 'German', 'it': 'Italian', 'tr': 'Turkish', 'ru': 'Russian',
                'zh-cn': 'Chinese (Simplified)', 'ja': 'Japanese', 'ko': 'Korean'
            }
        # Cache to file
        with open(LANG_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(langs, f, ensure_ascii=False, indent=2)
        return langs
    except Exception as e:
        logger.error(f"Failed to get supported languages: {e}")
        # Try read from cache
        if os.path.exists(LANG_CACHE_FILE):
            try:
                with open(LANG_CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}


def log_translation(original_text: str, translated_text: str, source_lang: str, target_lang: str):
    """
    Append a translation event to logs/translations.log as JSON line
    """
    try:
        event = {
            'timestamp': datetime.now().isoformat(),
            'source_lang': source_lang,
            'target_lang': target_lang,
            'original_len': len(original_text or ''),
            'translated_len': len(translated_text or '')
        }
        with open(TRANSLATION_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Failed to log translation: {e}")


def sanitize_text(text: str, max_len: int = 5000) -> str:
    """
    Basic sanitization: trim length and strip whitespace
    """
    if text is None:
        return ''
    text = text.strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text


def chunk_text(text: str, chunk_size: int = 4000) -> List[str]:
    """
    Split long text into chunks suitable for translation services limits
    """
    text = sanitize_text(text)
    if not text:
        return []
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
