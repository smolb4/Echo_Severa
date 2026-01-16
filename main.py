from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import random
import json
import os
import re
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# === КОНФИГ ===
TOKEN = os.getenv("VK_TOKEN", "")
GROUP_ID = int(os.getenv("VK_GROUP_ID", "235128907"))
YOUR_ID = int(os.getenv("YOUR_VK_ID", "388182166"))
CHAT_PEER_ID = int(os.getenv("CHAT_PEER_ID", "2000000001"))
CONFIRMATION_CODE = os.getenv("VK_CONFIRMATION_CODE", "744eebe2")
VK_API_VERSION = "5.199"

print("="*60)
print("🚀 VK Анкета-бот запущен")
print(f"📌 Group ID: {GROUP_ID}")
print(f"🔐 Confirmation: {CONFIRMATION_CODE}")
print("="*60)

# =================== GET ENDPOINTS ===================
@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "status": "VK Bot активен",
        "endpoints": {
            "/": "Это сообщение",
            "/callback": "GET: проверка, POST: обработка VK",
            "/test": "Тест парсинга",
            "/health": "Проверка здоровья"
        },
        "config": {
            "group_id": GROUP_ID,
            "your_id": YOUR_ID,
            "chat_id": CHAT_PEER_ID
        }
    }

@app.get("/callback")
async def callback_get():
    """GET endpoint для проверки callback"""
    return {
        "status": "Callback endpoint готов",
        "confirmation_code": CONFIRMATION_CODE,
        "note": "VK отправляет POST запросы на этот endpoint",
        "method": "Используйте POST для обработки событий VK",
        "time": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Проверка здоровья сервера"""
    return {
        "status": "healthy",
        "service": "VK Callback Bot",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/test")
async def test():
    """Тест парсинга"""
    test_data = """Q: Имя персонажа (полное, со знаками ударения), сокращения, клички
A: Тест Имя

Q: Пол персонажа
A: Самец

Q: Возраст персонажа (в формате n лет m месяцев)
A: 3 года

Q: Происхождение (для лайоров - горец/горянка, помор/поморка)
A: Горец"""
    
    answers = parse_anketa(test_data)
    
    return {
        "parsed": answers,
        "fields": len(answers),
        "confirmation_code": CONFIRMATION_CODE
    }

# =================== POST ENDPOINTS ===================
@app.post("/callback")
async def vk_callback(request: Request):
    """Обработчик Callback API от VK"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📥 POST /callback")
    
    try:
        # Получаем тело запроса
        body = await request.body()
        if not body:
            print("⚠️ Пустое тело запроса")
            return PlainTextResponse("ok")
        
        # Пробуем распарсить JSON
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            print("⚠️ Невалидный JSON")
            # Возможно, это строка с кодом подтверждения
            body_str = body.decode('utf-8')
            if "confirmation" in body_str.lower():
                print(f"🔐 Отправляем код: {CONFIRMATION_CODE}")
                return PlainTextResponse(CONFIRMATION_CODE)
            return PlainTextResponse("ok")
        
        # Логируем тип события
        event_type = data.get("type", "unknown")
        print(f"📌 Тип события: {event_type}")
        
        # 1. Подтверждение
        if event_type == "confirmation":
            print(f"✅ Отправляем код подтверждения: {CONFIRMATION_CODE}")
            return PlainTextResponse(CONFIRMATION_CODE)
        
        # 2. Новое сообщение
        elif event_type == "message_new":
            message = data["object"]["message"]
            text = message.get("text", "").strip()
            user_id = message.get("from_id", 0)
            
            print(f"👤 Сообщение от {user_id}")
            print(f"💬 Текст ({len(text)} chars): {text[:200]}...")
            
            # Проверяем анкету
            if "Анкета Вашего персонажа" in text:
                print("🎯 НАЙДЕНА АНКЕТА!")
                
                # Очищаем текст
                clean_text = clean_text_for_parsing(text)
                
                # Парсим
                answers = parse_anketa(clean_text)
                
                if answers:
                    print(f"📊 Распарсено {len(answers)} полей")
                    
                    # Отправляем вам
                    msg_to_you = format_for_moderator(answers, user_id)
                    send_message(YOUR_ID, msg_to_you)
                    
                    # Отправляем в чат
                    msg_to_chat = format_for_chat(answers, user_id)
                    send_message(CHAT_PEER_ID, msg_to_chat, is_chat=True)
                else:
                    print("⚠️ Анкета не распарсилась")
                    send_message(YOUR_ID, f"⚠️ Анкета от {user_id} не распарсилась\n\n{text[:500]}...")
            
            else:
                print("⏭️ Не анкета, игнорируем")
        
        else:
            print(f"ℹ️ Игнорируем событие: {event_type}")
    
    except Exception as e:
        print(f"❌ Ошибка в callback: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Обработка завершена")
    return PlainTextResponse("ok")

# =================== ФУНКЦИИ ===================
def clean_text_for_parsing(text: str) -> str:
    """Очистка текста для парсинга"""
    # Удаляем лишние строки
    lines_to_remove = [
        "Новый ответ в опросе:",
        "Анастасия Смоль",
        "Диалог:",
        "vk.com/",
        "?sel="
    ]
    
    for line in lines_to_remove:
        text = text.replace(line, "")
    
    return text.strip()

def parse_anketa(text: str) -> dict:
    """Парсинг анкеты"""
    answers = {}
    
    # Ищем все Q: A: пары
    pattern = r'Q[:.]\s*(.*?)\s*A[:.]\s*(.*?)(?=Q[:.]|$)'
    matches = re.findall(pattern, text, re.DOTALL)
    
    print(f"🔍 Найдено {len(matches)} вопросов")
    
    # Маппинг вопросов к полям
    field_map = {
        "Имя персонажа (полное, со знаками ударения), сокращения, клички": "Имя",
        "Пол персонажа": "Пол",
        "Возраст персонажа (в формате n лет m месяцев)": "Возраст",
        "Происхождение (для лайоров - горец/горянка, помор/поморка)": "Происхождение",
        "Позиция в племени": "Позиция",
        "Телосложение (кратко)": "Телосложение",
        "Рост персонажа": "Рост",
        "Цвет глаз (кратко)": "Глаза",
        "Цвет шерсти (кратко)": "Шерсть",
        "Ссылка на референс в альбоме основной группы": "Ссылка на реф",
        "Внешность, отличительные черты и поведение": "Внешность",
        "Основные черты характера через запятую": "Характер",
        "Подробнее о характере": "Характер подробнее",
        "Цели и планы персонажа на ближайшее будущее": "Цели",
        "Здесь Вы можете написать историю персонажа:": "История",
        "Навыки, таланты, недостатки": "Навыки"
    }
    
    for question, answer in matches:
        question = question.strip()
        answer = answer.strip()
        
        # Ищем точное совпадение
        for q_template, field in field_map.items():
            if question == q_template:
                answers[field] = answer
                print(f"   ✅ {field}: {answer[:50]}{'...' if len(answer) > 50 else ''}")
                break
    
    return answers

def format_for_moderator(answers: dict, user_id: int) -> str:
    """Форматирование для модератора"""
    fields = [
        ("Имя", "👤"), ("Пол", "⚧️"), ("Возраст", "🎂"),
        ("Происхождение", "🌍"), ("Позиция", "🏹"), ("Телосложение", "💪"),
        ("Рост", "📏"), ("Глаза", "👁️"), ("Шерсть", "🐾"),
        ("Ссылка на реф", "🔗"), ("Внешность", "🎭"), ("Характер", "🧠"),
        ("Характер подробнее", "📖"), ("Цели", "🎯"), ("Навыки", "🛠️"),
        ("История", "📜")
    ]
    
    lines = [
        f"🎯 НОВАЯ АНКЕТА от VK ID: {user_id}",
        f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
        ""
    ]
    
    for field_name, emoji in fields:
        if field_name in answers:
            value = answers[field_name]
            lines.append(f"{emoji} {field_name}: {value}")
        else:
            lines.append(f"{emoji} {field_name}: —")
    
    return "\n".join(lines)

def format_for_chat(answers: dict, user_id: int) -> str:
    """Форматирование для чата"""
    name = answers.get("Имя", "Не указано")
    gender = answers.get("Пол", "Не указано")
    age = answers.get("Возраст", "Не указано")
    position = answers.get("Позиция", "Не указано")
    
    return f"""🎯 НОВАЯ АНКЕТА!

👤 Персонаж: {name}
⚧️ Пол: {gender}
🎂 Возраст: {age}
🏹 Позиция: {position}

📝 Отправлена на модерацию.
🕒 {datetime.now().strftime('%H:%M')}"""

def send_message(peer_id: int, message: str, is_chat: bool = False) -> bool:
    """Отправка сообщения"""
    try:
        params = {
            "message": message,
            "random_id": random.randint(1, 10**9),
            "access_token": TOKEN,
            "v": VK_API_VERSION
        }
        
        if is_chat:
            params["peer_id"] = peer_id
        else:
            params["user_id"] = peer_id
        
        response = requests.post(
            "https://api.vk.com/method/messages.send",
            data=params,
            timeout=10
        )
        
        result = response.json()
        
        if "error" in result:
            print(f"❌ Ошибка отправки: {result['error']}")
            return False
        
        print(f"✅ Сообщение отправлено ({'чат' if is_chat else 'ЛС'})")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
