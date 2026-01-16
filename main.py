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
VK_API_VERSION = "5.199"

print("="*60)
print("🚀 VK Анкета-бот запущен")
print("="*60)

@app.post("/callback")
async def vk_callback(request: Request):
    """Главный обработчик"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📥 Запрос от VK")
    
    try:
        data = await request.json()
        event_type = data.get("type")
        
        # 1. Подтверждение
        if event_type == "confirmation":
            return PlainTextResponse("10707297")
        
        # 2. Новое сообщение
        elif event_type == "message_new":
            message = data["object"]["message"]
            text = message.get("text", "").strip()
            user_id = message.get("from_id", 0)
            
            print(f"👤 От: {user_id}")
            print(f"📝 Длина текста: {len(text)} символов")
            
            # Проверяем анкету
            if "Анкета Вашего персонажа" in text:
                print("🎯 НАЙДЕНА АНКЕТА!")
                
                # Убираем лишнее
                clean_text = clean_anketa_text(text)
                
                # Парсим
                answers = parse_anketa_exact(clean_text)
                
                print(f"📊 Поля анкеты: {list(answers.keys())}")
                
                # Отправляем вам
                if answers:
                    message_to_you = format_full_anketa(answers, user_id)
                    send_to_user(YOUR_ID, message_to_you, "Вам")
                    
                    # Отправляем в чат
                    message_to_chat = format_chat_notification(answers, user_id)
                    send_to_chat(message_to_chat)
                else:
                    print("⚠️ Анкета пустая или не распарсилась")
                    # Отправляем сообщение об ошибке
                    send_to_user(YOUR_ID, f"⚠️ Анкета от {user_id} не распарсилась\n\n{text[:500]}...", "Вам")
            
            else:
                print("⏭️ Не анкета")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    return PlainTextResponse("ok")

def clean_anketa_text(text: str) -> str:
    """Очистка текста анкеты от лишнего"""
    # Удаляем заголовки и личные данные
    lines_to_remove = [
        "Новый ответ в опросе:",
        "Анастасия Смоль",
        "Диалог:",
        "vk.com/id",
        "vk.com/gim",
        "?sel="
    ]
    
    clean = text
    for line in lines_to_remove:
        clean = clean.replace(line, "")
    
    return clean.strip()

def parse_anketa_exact(text: str) -> dict:
    """Точный парсинг анкеты формата Q: A:"""
    answers = {}
    
    # Паттерн для Q: вопрос A: ответ
    pattern = r'Q[:.]\s*(.*?)\s*A[:.]\s*(.*?)(?=Q[:.]|$)'
    matches = re.findall(pattern, text, re.DOTALL)
    
    print(f"🔍 Найдено пар Q/A: {len(matches)}")
    
    # Точное соответствие
    field_mapping = {
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
        
        # Ищем точное соответствие
        for q_template, field in field_mapping.items():
            if question == q_template:
                answers[field] = answer
                print(f"   ✅ {field}: {answer[:50]}{'...' if len(answer) > 50 else ''}")
                break
        
        # Если не нашли точного, ищем по части
        if not any(q_template in question for q_template in field_mapping.keys()):
            print(f"   ⚠️ Неизвестный вопрос: '{question[:50]}...'")
    
    return answers

def format_full_anketa(answers: dict, user_id: int) -> str:
    """Полная анкета для модератора"""
    fields = [
        ("Имя", "👤"),
        ("Пол", "⚧️"),
        ("Возраст", "🎂"),
        ("Происхождение", "🌍"),
        ("Позиция", "🏹"),
        ("Телосложение", "💪"),
        ("Рост", "📏"),
        ("Глаза", "👁️"),
        ("Шерсть", "🐾"),
        ("Ссылка на реф", "🔗"),
        ("Внешность", "🎭"),
        ("Характер", "🧠"),
        ("Характер подробнее", "📖"),
        ("Цели", "🎯"),
        ("Навыки", "🛠️"),
        ("История", "📜")
    ]
    
    lines = [
        f"🎯 НОВАЯ АНКЕТА",
        f"👤 От: VK ID {user_id}",
        f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
        ""
    ]
    
    for field_name, emoji in fields:
        if field_name in answers:
            value = answers[field_name]
            lines.append(f"{emoji} {field_name}: {value}")
        else:
            lines.append(f"{emoji} {field_name}: —")
    
    lines.append(f"\n📝 ID анкеты: {user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    
    return "\n".join(lines)

def format_chat_notification(answers: dict, user_id: int) -> str:
    """Краткое уведомление для чата"""
    name = answers.get("Имя", "Не указано")
    gender = answers.get("Пол", "Не указано")
    age = answers.get("Возраст", "Не указано")
    
    return f"""🎯 НОВАЯ АНКЕТА!

👤 Персонаж: {name}
⚧️ Пол: {gender}
🎂 Возраст: {age}

📝 Анкета отправлена на модерацию.
🕒 {datetime.now().strftime('%H:%M')}
"""

def send_to_user(user_id: int, message: str, recipient: str = "") -> bool:
    """Отправка личного сообщения"""
    try:
        response = requests.post(
            "https://api.vk.com/method/messages.send",
            data={
                "user_id": user_id,
                "message": message,
                "random_id": random.randint(1, 10**9),
                "access_token": TOKEN,
                "v": VK_API_VERSION
            }
        )
        
        result = response.json()
        if "error" not in result:
            print(f"✅ Отправлено {recipient}")
            return True
        else:
            print(f"❌ Ошибка {recipient}: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

def send_to_chat(message: str) -> bool:
    """Отправка в чат"""
    try:
        response = requests.post(
            "https://api.vk.com/method/messages.send",
            data={
                "peer_id": CHAT_PEER_ID,
                "message": message,
                "random_id": random.randint(1, 10**9),
                "access_token": TOKEN,
                "v": VK_API_VERSION
            }
        )
        
        result = response.json()
        if "error" not in result:
            print("✅ Отправлено в чат")
            return True
        else:
            print(f"❌ Ошибка чата: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка чата: {e}")
        return False

@app.get("/")
async def root():
    return {"status": "VK Bot активен", "time": datetime.now().isoformat()}

@app.get("/test-parse")
async def test_parse():
    """Тест парсинга"""
    test_anketa = """Новый ответ в опросе: Анкета Вашего персонажа для РП сегмента проекта Эхо Севера
Анастасия Смоль vk.com/id388182166
Диалог: vk.com/gim235128907?sel=388182166

Q: Имя персонажа (полное, со знаками ударения), сокращения, клички
A: Тестовое Имя

Q: Пол персонажа
A: Самец

Q: Возраст персонажа (в формате n лет m месяцев)
A: 3 года 2 месяца

Q: Происхождение (для лайоров - горец/горянка, помор/поморка)
A: Горец

Q: Позиция в племени
A: Воин

Q: Телосложение (кратко)
A: Мускулистое

Q: Рост персонажа
A: 180 см

Q: Цвет глаз (кратко)
A: Зеленые

Q: Цвет шерсти (кратко)
A: Серый

Q: Ссылка на референс в альбоме основной группы
A: https://vk.com/photo...

Q: Внешность, отличительные черты и поведение
A: Шрамы на морде

Q: Основные черты характера через запятую
A: Храбрый, упрямый

Q: Подробнее о характере
A: Очень предан племени

Q: Цели и планы персонажа на ближайшее будущее
A: Стать лидером

Q: Здесь Вы можете написать историю персонажа:
A: История тест

Q: Навыки, таланты, недостатки
A: Отличный охотник"""
    
    clean = clean_anketa_text(test_anketa)
    answers = parse_anketa_exact(clean)
    
    return {
        "parsed": answers,
        "fields_count": len(answers),
        "all_fields_found": len(answers) == 16
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
