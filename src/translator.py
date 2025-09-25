#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HumanTranslator - Translation Module
===================================

This module handles all translation functionality using Google Translate API.
Provides a unified interface for text translation with language detection,
error handling, and caching capabilities.

Author: Soul-19129
License: MIT
"""

import googletrans
from googletrans import Translator, LANGUAGES
import logging
import time
import json
import hashlib
import os
from typing import Dict, Optional, Union, List
from functools import lru_cache
import threading
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

class TranslationCache:
    """
    Simple in-memory cache for translations with expiration
    """
    def __init__(self, max_size: int = 1000, expire_hours: int = 24):
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        self.expire_delta = timedelta(hours=expire_hours)
        self.lock = threading.RLock()
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.timestamps:
            return True
        return datetime.now() - self.timestamps[key] > self.expire_delta
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        expired_keys = [k for k in self.timestamps if self._is_expired(k)]
        for key in expired_keys:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached translation"""
        with self.lock:
            if key in self.cache and not self._is_expired(key):
                return self.cache[key]
            return None
    
    def set(self, key: str, value: Dict):
        """Set cached translation"""
        with self.lock:
            # Clean up if cache is getting too large
            if len(self.cache) >= self.max_size:
                self._cleanup_expired()
                # If still too large, remove oldest entries
                if len(self.cache) >= self.max_size:
                    oldest_keys = sorted(self.timestamps.keys(), 
                                       key=lambda k: self.timestamps[k])[:100]
                    for key in oldest_keys:
                        self.cache.pop(key, None)
                        self.timestamps.pop(key, None)
            
            self.cache[key] = value
            self.timestamps[key] = datetime.now()

class HumanTranslator:
    """
    Main translator class that handles text translation using Google Translate API
    """
    
    def __init__(self, cache_size: int = 1000, rate_limit_delay: float = 0.1):
        """
        Initialize the HumanTranslator
        
        Args:
            cache_size (int): Maximum number of translations to cache
            rate_limit_delay (float): Delay between API calls to avoid rate limiting
        """
        self.translator = Translator()
        self.cache = TranslationCache(max_size=cache_size)
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.request_lock = threading.Lock()
        
        # Initialize supported languages
        self.supported_languages = LANGUAGES
        
        logger.info(f"HumanTranslator initialized with {len(self.supported_languages)} supported languages")
    
    def _generate_cache_key(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        """
        Generate a unique cache key for the translation request
        """
        key_string = f"{text}:{source_lang or 'auto'}:{target_lang}"
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def _rate_limit(self):
        """
        Implement simple rate limiting to avoid hitting API limits
        """
        with self.request_lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - time_since_last)
            self.last_request_time = time.time()
    
    def detect_language(self, text: str) -> Dict[str, Union[str, float]]:
        """
        Detect the language of the given text
        
        Args:
            text (str): Text to analyze
            
        Returns:
            Dict containing detected language code and confidence
        """
        try:
            self._rate_limit()
            detection = self.translator.detect(text)
            
            return {
                'success': True,
                'language': detection.lang,
                'confidence': detection.confidence,
                'language_name': self.supported_languages.get(detection.lang, 'Unknown')
            }
        
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return {
                'success': False,
                'error': f'Language detection failed: {str(e)}',
                'language': 'unknown',
                'confidence': 0.0
            }
    
    def translate(self, 
                 text: str, 
                 target_language: str, 
                 source_language: Optional[str] = None) -> Dict[str, Union[str, bool, float]]:
        """
        Translate text from source language to target language
        
        Args:
            text (str): Text to translate
            target_language (str): Target language code (e.g., 'en', 'ar', 'fr')
            source_language (str, optional): Source language code. If None, auto-detect
            
        Returns:
            Dict containing translation result, detected language, and metadata
        """
        try:
            # Input validation
            if not text or not text.strip():
                return {
                    'success': False,
                    'error': 'Text cannot be empty'
                }
            
            text = text.strip()
            target_language = target_language.lower().strip()
            
            # Validate target language
            if target_language not in self.supported_languages:
                return {
                    'success': False,
                    'error': f'Unsupported target language: {target_language}'
                }
            
            # Check cache first
            cache_key = self._generate_cache_key(text, target_language, source_language)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for translation: {text[:50]}...")
                return cached_result
            
            # Detect source language if not provided
            if not source_language or source_language == 'auto':
                detection_result = self.detect_language(text)
                if not detection_result['success']:
                    return {
                        'success': False,
                        'error': 'Failed to detect source language'
                    }
                source_language = detection_result['language']
                detected_confidence = detection_result['confidence']
            else:
                source_language = source_language.lower().strip()
                if source_language not in self.supported_languages:
                    return {
                        'success': False,
                        'error': f'Unsupported source language: {source_language}'
                    }
                detected_confidence = 1.0  # Assume high confidence for manually specified language
            
            # Skip translation if source and target are the same
            if source_language == target_language:
                result = {
                    'success': True,
                    'translated_text': text,
                    'detected_language': source_language,
                    'confidence': 1.0,
                    'original_text': text,
                    'cached': False
                }
                self.cache.set(cache_key, result)
                return result
            
            # Perform translation
            self._rate_limit()
            translation = self.translator.translate(
                text, 
                src=source_language, 
                dest=target_language
            )
            
            result = {
                'success': True,
                'translated_text': translation.text,
                'detected_language': translation.src,
                'confidence': detected_confidence,
                'original_text': text,
                'source_language_name': self.supported_languages.get(translation.src, 'Unknown'),
                'target_language_name': self.supported_languages.get(target_language, 'Unknown'),
                'cached': False
            }
            
            # Cache the result
            self.cache.set(cache_key, result)
            
            logger.info(f"Translation successful: {source_language} -> {target_language}")
            return result
        
        except googletrans.exceptions.JSONDecodeError as e:
            error_msg = "Translation service temporarily unavailable"
            logger.error(f"JSONDecodeError in translation: {e}")
            return {
                'success': False,
                'error': error_msg
            }
        
        except Exception as e:
            error_msg = f"Translation failed: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def translate_batch(self, 
                       texts: List[str], 
                       target_language: str, 
                       source_language: Optional[str] = None) -> List[Dict]:
        """
        Translate multiple texts at once
        
        Args:
            texts (List[str]): List of texts to translate
            target_language (str): Target language code
            source_language (str, optional): Source language code
            
        Returns:
            List of translation results
        """
        results = []
        
        for text in texts:
            result = self.translate(
                text=text,
                target_language=target_language,
                source_language=source_language
            )
            results.append(result)
            
            # Small delay between batch translations to avoid rate limiting
            if len(texts) > 1:
                time.sleep(0.05)
        
        return results
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get dictionary of supported language codes and names
        
        Returns:
            Dict mapping language codes to language names
        """
        return self.supported_languages.copy()
    
    def is_language_supported(self, language_code: str) -> bool:
        """
        Check if a language code is supported
        
        Args:
            language_code (str): Language code to check
            
        Returns:
            bool: True if supported, False otherwise
        """
        return language_code.lower() in self.supported_languages
    
    def get_language_name(self, language_code: str) -> str:
        """
        Get the human-readable name for a language code
        
        Args:
            language_code (str): Language code
            
        Returns:
            str: Language name or 'Unknown' if not found
        """
        return self.supported_languages.get(language_code.lower(), 'Unknown')
    
    def clear_cache(self):
        """
        Clear the translation cache
        """
        with self.cache.lock:
            self.cache.cache.clear()
            self.cache.timestamps.clear()
        logger.info("Translation cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics
        
        Returns:
            Dict with cache size and hit information
        """
        with self.cache.lock:
            return {
                'cache_size': len(self.cache.cache),
                'max_size': self.cache.max_size
            }

# Create a global translator instance for easy import
translator_instance = None

def get_translator() -> HumanTranslator:
    """
    Get a singleton instance of HumanTranslator
    
    Returns:
        HumanTranslator: Singleton translator instance
    """
    global translator_instance
    if translator_instance is None:
        translator_instance = HumanTranslator()
    return translator_instance

if __name__ == "__main__":
    # Example usage and testing
    translator = HumanTranslator()
    
    # Test basic translation
    result = translator.translate("Hello, how are you?", "ar")
    if result['success']:
        print(f"Translation: {result['translated_text']}")
        print(f"Detected language: {result['detected_language']}")
    else:
        print(f"Translation failed: {result['error']}")
    
    # Test language detection
    detection = translator.detect_language("Bonjour, comment allez-vous?")
    if detection['success']:
        print(f"Detected: {detection['language']} ({detection['language_name']})")
        print(f"Confidence: {detection['confidence']}")
    
    # Test batch translation
    texts = ["Hello", "Good morning", "How are you?"]
    batch_results = translator.translate_batch(texts, "es")
    for i, result in enumerate(batch_results):
        if result['success']:
            print(f"{texts[i]} -> {result['translated_text']}")
    
    # Print cache stats
    stats = translator.get_cache_stats()
    print(f"Cache stats: {stats}")
