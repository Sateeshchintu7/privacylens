"""Quick translation test script — run on server to verify Gemini translation works."""
import os
import sys
sys.path.insert(0, '/home/ubuntu/privacylens')
os.environ['GEMINI_API_KEY'] = open('/home/ubuntu/privacylens/.env').read().split('GEMINI_API_KEY=')[1].split()[0]

from api.routes.audio import _translate_text

# Test Telugu
result_te = _translate_text('This policy collects your name and email address.', 'te')
print(f'Telugu result: {result_te}')
has_te = any(0x0C00 <= ord(c) <= 0x0C7F for c in result_te)
print(f'Has Telugu chars: {has_te}')

# Test Hindi
result_hi = _translate_text('This policy collects your name and email address.', 'hi')
print(f'Hindi result: {result_hi}')
has_hi = any(0x0900 <= ord(c) <= 0x097F for c in result_hi)
print(f'Has Hindi chars: {has_hi}')

# Test French
result_fr = _translate_text('This policy collects your name and email address.', 'fr')
print(f'French result: {result_fr}')

# Test audio generation with Telugu text
from audio.tts_engine import generate_audio
audio_result = generate_audio('నమస్కారం ఇది ఒక పరీక్ష', 'te', 'adult', 'gtts')
print(f'Audio generated: {len(open(audio_result.audio_path, "rb").read()) > 100}')
print(f'Audio language: {audio_result.language}')
print(f'Audio engine: {audio_result.voice_engine}')
print('\nAll tests passed!' if (has_te and has_hi) else '\nSOME TESTS FAILED!')
