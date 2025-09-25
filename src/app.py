#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HumanTranslator - Main Application
==================================

Main Flask application that connects all translation modules.
Provides REST API endpoints for translation, speech-to-text, and text-to-speech.

Author: Soul-19129
License: MIT
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import logging
import os
from datetime import datetime

# Import our custom modules
try:
    from translator import HumanTranslator
    from speech import SpeechHandler
    from utils import validate_language_code, log_translation, get_supported_languages
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all required files are in the same directory")
    exit(1)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for web interface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize components
translator = HumanTranslator()
speech_handler = SpeechHandler()

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

@app.route('/')
def home():
    """
    Serve the main web interface
    """
    try:
        # If web interface exists, serve it
        if os.path.exists('web/index.html'):
            return render_template('index.html')
        else:
            # Return API information if web interface not found
            return jsonify({
                'message': 'HumanTranslator API Server',
                'version': '1.0.0',
                'endpoints': {
                    '/api/translate': 'POST - Translate text',
                    '/api/languages': 'GET - Get supported languages',
                    '/api/speech-to-text': 'POST - Convert speech to text',
                    '/api/text-to-speech': 'POST - Convert text to speech',
                    '/api/health': 'GET - Health check'
                },
                'documentation': '/api/docs'
            })
    except Exception as e:
        logger.error(f"Error in home route: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health')
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/languages')
def get_languages():
    """
    Get list of supported languages
    """
    try:
        languages = get_supported_languages()
        return jsonify({
            'languages': languages,
            'total': len(languages)
        })
    except Exception as e:
        logger.error(f"Error getting languages: {e}")
        return jsonify({'error': 'Failed to get languages'}), 500

@app.route('/api/translate', methods=['POST'])
def translate_text():
    """
    Translate text from source language to target language
    
    Expected JSON payload:
    {
        "text": "Hello world",
        "source": "en",  # optional, auto-detect if not provided
        "target": "ar"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'text' not in data or 'target' not in data:
            return jsonify({
                'error': 'Missing required fields: text and target'
            }), 400
        
        text = data['text'].strip()
        target_lang = data['target'].strip().lower()
        source_lang = data.get('source', 'auto').strip().lower()
        
        # Validate input
        if not text:
            return jsonify({'error': 'Text cannot be empty'}), 400
        
        if not validate_language_code(target_lang):
            return jsonify({'error': 'Invalid target language code'}), 400
        
        if source_lang != 'auto' and not validate_language_code(source_lang):
            return jsonify({'error': 'Invalid source language code'}), 400
        
        # Perform translation
        result = translator.translate(
            text=text,
            target_language=target_lang,
            source_language=source_lang if source_lang != 'auto' else None
        )
        
        if result['success']:
            # Log successful translation
            log_translation(
                original_text=text,
                translated_text=result['translated_text'],
                source_lang=result['detected_language'],
                target_lang=target_lang
            )
            
            return jsonify({
                'success': True,
                'original_text': text,
                'translated_text': result['translated_text'],
                'source_language': result['detected_language'],
                'target_language': target_lang,
                'confidence': result.get('confidence', 0.95)
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
    
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return jsonify({
            'success': False,
            'error': 'Translation failed'
        }), 500

@app.route('/api/speech-to-text', methods=['POST'])
def speech_to_text():
    """
    Convert uploaded audio file to text
    
    Expected form data:
    - audio: audio file (wav, mp3, etc.)
    - language: language code (optional, auto-detect if not provided)
    """
    try:
        # Check if audio file is present
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get language parameter
        language = request.form.get('language', 'auto')
        
        # Process speech to text
        result = speech_handler.speech_to_text(
            audio_file=audio_file,
            language=language if language != 'auto' else None
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'text': result['text'],
                'language': result['detected_language'],
                'confidence': result.get('confidence', 0.9)
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
    
    except Exception as e:
        logger.error(f"Speech to text error: {e}")
        return jsonify({
            'success': False,
            'error': 'Speech recognition failed'
        }), 500

@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    """
    Convert text to speech audio
    
    Expected JSON payload:
    {
        "text": "Hello world",
        "language": "en",
        "slow": false  # optional, for slow speech
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'text' not in data or 'language' not in data:
            return jsonify({
                'error': 'Missing required fields: text and language'
            }), 400
        
        text = data['text'].strip()
        language = data['language'].strip().lower()
        slow = data.get('slow', False)
        
        # Validate input
        if not text:
            return jsonify({'error': 'Text cannot be empty'}), 400
        
        if not validate_language_code(language):
            return jsonify({'error': 'Invalid language code'}), 400
        
        # Convert text to speech
        result = speech_handler.text_to_speech(
            text=text,
            language=language,
            slow=slow
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'audio_url': result['audio_url'],
                'duration': result.get('duration'),
                'language': language
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
    
    except Exception as e:
        logger.error(f"Text to speech error: {e}")
        return jsonify({
            'success': False,
            'error': 'Text to speech conversion failed'
        }), 500

@app.route('/api/batch-translate', methods=['POST'])
def batch_translate():
    """
    Translate multiple texts at once
    
    Expected JSON payload:
    {
        "texts": ["Hello", "World", "How are you?"],
        "target": "ar",
        "source": "en"  # optional
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'texts' not in data or 'target' not in data:
            return jsonify({
                'error': 'Missing required fields: texts and target'
            }), 400
        
        texts = data['texts']
        target_lang = data['target'].strip().lower()
        source_lang = data.get('source', 'auto').strip().lower()
        
        # Validate input
        if not isinstance(texts, list) or not texts:
            return jsonify({'error': 'texts must be a non-empty list'}), 400
        
        if len(texts) > 100:  # Limit batch size
            return jsonify({'error': 'Maximum 100 texts per batch'}), 400
        
        if not validate_language_code(target_lang):
            return jsonify({'error': 'Invalid target language code'}), 400
        
        # Process batch translation
        results = []
        for text in texts:
            if not text.strip():
                results.append({
                    'success': False,
                    'error': 'Empty text',
                    'original_text': text
                })
                continue
            
            result = translator.translate(
                text=text.strip(),
                target_language=target_lang,
                source_language=source_lang if source_lang != 'auto' else None
            )
            
            results.append({
                'success': result['success'],
                'original_text': text,
                'translated_text': result.get('translated_text'),
                'detected_language': result.get('detected_language'),
                'error': result.get('error')
            })
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results),
            'successful': sum(1 for r in results if r['success'])
        })
    
    except Exception as e:
        logger.error(f"Batch translation error: {e}")
        return jsonify({
            'success': False,
            'error': 'Batch translation failed'
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist'
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        'error': 'Method not allowed',
        'message': 'The request method is not allowed for this endpoint'
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

if __name__ == '__main__':
    # Get configuration from environment variables
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting HumanTranslator server on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    
    # Start the Flask application
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )
