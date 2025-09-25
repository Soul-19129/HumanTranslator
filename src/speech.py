#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HumanTranslator - Speech Module
===============================

Provides speech-to-text (STT) and text-to-speech (TTS) functionality.
Uses SpeechRecognition for STT and gTTS for TTS.

Author: Soul-19129
License: MIT
"""

import os
import uuid
import time
import logging
from typing import Optional, Dict

from gtts import gTTS
import speech_recognition as sr

# Configure logging
logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXT = {'.wav', '.mp3', '.m4a', '.ogg', '.flac', '.aiff', '.aif'}
AUDIO_OUTPUT_DIR = os.path.join('web', 'audio')

# Ensure output directory exists for generated audio
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

class SpeechHandler:
    """
    Handles speech-to-text and text-to-speech operations
    """

    def __init__(self, default_lang: str = 'en'):
        self.default_lang = default_lang
        self.recognizer = sr.Recognizer()
        # Tune for better performance in noisy environments
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        logger.info("SpeechHandler initialized")

    def _secure_filename(self, base: str, ext: str) -> str:
        safe_ext = ext.lower() if ext.lower() in SUPPORTED_AUDIO_EXT else '.mp3'
        return f"{base}{safe_ext}"

    def text_to_speech(self, text: str, language: str, slow: bool = False) -> Dict:
        """
        Convert text to speech and save to static file served by web server.
        Returns a dict with success flag and audio_url.
        """
        try:
            if not text or not text.strip():
                return {'success': False, 'error': 'Text cannot be empty'}
            if not language or len(language) < 2:
                return {'success': False, 'error': 'Invalid language code'}

            tts = gTTS(text=text.strip(), lang=language.lower(), slow=slow)
            file_id = uuid.uuid4().hex
            filename = self._secure_filename(file_id, '.mp3')
            filepath = os.path.join(AUDIO_OUTPUT_DIR, filename)

            # Save audio file
            tts.save(filepath)

            # Build URL path relative to web root
            audio_url = f"/audio/{filename}"
            logger.info(f"TTS generated: {audio_url}")
            return {
                'success': True,
                'audio_url': audio_url,
                'duration': None  # gTTS doesn't report duration
            }
        except Exception as e:
            logger.error(f"Text-to-speech failed: {e}")
            return {'success': False, 'error': 'Text-to-speech failed'}

    def speech_to_text(self, audio_file, language: Optional[str] = None) -> Dict:
        """
        Convert an uploaded audio file (werkzeug FileStorage) to text.
        Optionally specify language code (e.g., 'en-US', 'ar', etc.).
        Uses Google Web Speech API via SpeechRecognition (free, rate-limited).
        """
        try:
            # Save temporary file
            tmp_dir = os.path.join('logs', 'tmp_audio')
            os.makedirs(tmp_dir, exist_ok=True)
            base = uuid.uuid4().hex
            tmp_path = os.path.join(tmp_dir, base + '.wav')

            # SpeechRecognition works best with WAV; if other format, it still may work
            audio_file.save(tmp_path)

            with sr.AudioFile(tmp_path) as source:
                # Reduce noise and capture audio
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio_data = self.recognizer.record(source)

            # Recognize speech
            lang = language if language else self.default_lang
            text = self.recognizer.recognize_google(audio_data, language=lang)

            # Cleanup
            try:
                os.remove(tmp_path)
            except Exception:
                pass

            logger.info("STT success")
            return {
                'success': True,
                'text': text,
                'detected_language': lang,
                'confidence': 0.9
            }
        except sr.UnknownValueError:
            return {'success': False, 'error': 'Could not understand the audio'}
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return {'success': False, 'error': 'Speech recognition service error'}
        except Exception as e:
            logger.error(f"Speech-to-text failed: {e}")
            return {'success': False, 'error': 'Speech-to-text failed'}

if __name__ == '__main__':
    # Simple manual tests
    sh = SpeechHandler()
    # Example TTS
    res = sh.text_to_speech("Hello from HumanTranslator", "en")
    print(res)
