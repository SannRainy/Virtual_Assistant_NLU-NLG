import re

class SessionManager:
    def __init__(self):
        self.PRODI_MAPPING = {
            "teknik": [
                "teknik", "informatika", "sistem informasi", "teknik industri", 
                "teknik kimia", "teknik elektro", "ti", "si", "ft"
            ],
            "ekonomi": [
                "ekonomi", "akuntansi", "manajemen", "feb", "bisnis"
            ],
            "pendidikan": [
                "pendidikan", "keguruan", "fkip", "pgsd", "bimbingan konseling", "bk", 
                "paud", "pgpaud", "pendidikan matematika", "pendidikan biologi", 
                "pendidikan fisika", "pendidikan sejarah", "ppkn", "pkn",
                "pendidikan bahasa inggris", "pendidikan bahasa indonesia", 
                "ipa", "ips", "guru"
            ],
            "hukum": [
                "hukum", "ilmu hukum", "fh"
            ],
            "kesehatan": [
                "farmasi", "ilmu keolahragaan", "fiks", "olahraga"
            ]
        }
        self.reset_session()

    def reset_session(self):
        self.history = []
        self.current_context = None
        self.memory_slots = {
            "prodi": None,
            "semester": None,
            "kategori": None
        }

    def update_history(self, role, text):
        self.history.append({"role": role, "text": text})
        if len(self.history) > 20:
            self.history.pop(0)

    def set_context(self, intent):
        self.current_context = intent

    def get_context(self):
        return self.current_context

    def extract_entities(self, user_input):
        text = user_input.lower()

        found_prodi = False
        for key, keywords in self.PRODI_MAPPING.items():
            for word in keywords:
                if re.search(r'\b' + re.escape(word) + r'\b', text):
                    self.memory_slots["prodi"] = key
                    found_prodi = True
                    break
            if found_prodi:
                break

        semester_match = re.search(r"(?:semester|smt|sem)\s*(\d+|ganjil|genap)", text)
        if semester_match:
            self.memory_slots["semester"] = semester_match.group(1)
        elif text.isdigit() and int(text) <= 14:
            self.memory_slots["semester"] = text

    def get_slot(self, key):
        return self.memory_slots.get(key)
    
    def debug_memory(self):
        return f"[MEMORY] Prodi: {self.memory_slots['prodi']} | Smt: {self.memory_slots['semester']} | Context: {self.current_context}"
