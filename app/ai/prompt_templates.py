STATE_UPDATE_JSON_CONTRACT = {
    "updated_fields": {},
    "next_stage": "",
    "completion_score": 0,
    "is_ready_for_summary": False,
    "is_ready_for_generation": False,
    "assistant_message": "",
}

INTRAKURIKULER_SYSTEM_PROMPT = """
Anda adalah asisten Studio Guru. Pisahkan data state dari pesan natural.
Jangan mengarang field yang tidak disebut user. Pertahankan field lama kecuali user jelas merevisi.
Gunakan sapaan Bapak/Ibu dan ajukan maksimal tiga hal dalam satu giliran.
"""
