import json
import random
import os
from utils.mock_database import get_data_by_intent

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(BASE_DIR, 'data', 'response_templates.json')

with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
    TEMPLATE_DATA = json.load(f)

def generate_hybrid_response(intent, static_responses, memory_slots=None):
    db_data = get_data_by_intent(intent)
    injected_info = ""

    if db_data and memory_slots and memory_slots.get('prodi'):
        user_prodi = memory_slots['prodi']
        specific_key = f"prodi_{user_prodi}"

        if specific_key in db_data:
            data_spesifik = db_data[specific_key]

            if intent == 'biaya_ukt':
                injected_info = f"💰 **Khusus Prodi {user_prodi.capitalize()}:** Biayanya adalah {data_spesifik}."
                db_data['nominal_ukt'] = data_spesifik
            
            elif intent == 'lokasi_gedung':
                injected_info = f"📍 **Info Prodi {user_prodi.capitalize()}:** Perkuliahan/Sekretariat ada di {data_spesifik}."

    if db_data:
        db_data['info_spesifik'] = injected_info

    if db_data and intent in TEMPLATE_DATA['templates']:
        templates = TEMPLATE_DATA['templates'][intent]
        selected_template = random.choice(templates)
        
        try:
            final_response = selected_template.format(**db_data)
            return final_response.replace("  ", " ").strip()
        except KeyError:
            pass 
            
    return random.choice(static_responses)