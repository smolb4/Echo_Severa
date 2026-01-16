# main.py
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

# =================== КОНФИГУРАЦИЯ ===================
# ВАЖНО: Используем os.environ.get() для Railway
TOKEN = os.environ.get("VK_TOKEN", "")
GROUP_ID = int(os.environ.get("VK_GROUP_ID", "235128907"))
YOUR_ID = int(os.environ.get("YOUR_VK_ID", "388182166"))
CHAT_PEER_ID = int(os.environ.get("CHAT_PEER_ID", "2000000001"))
CONFIRMATION_CODE = os.environ.get("VK_CONFIRMATION_CODE", "744eebe2")
VK_API_VERSION = "5.199"

# Принудительный сброс буфера логов
import functools
print = functools.partial(print, flush=True)

# Проверка конфигурации при запуске
print("\n" + "="*70)
print("🚀 VK АНКЕТА-БОТ ЗАПУСКАЕТСЯ")
print("="*70)
print(f"📌 ID группы: {GROUP_ID}")
print(f"👤 Ваш ID: {YOUR_ID}")
print(f"💬 ID чата: {CHAT_PEER_ID}")
print(f"🔐 Код подтверждения: {CONFIRMATION_CODE}")
print(f"🌐 Версия API: {VK_API_VERSION}")

if TOKEN and TOKEN != "":
    print(f"✅ Токен загружен ({len(TOKEN)} символов)")
    print(f"   Начинается с: {TOKEN[:15]}...")
else:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: Токен не найден!")
    print("   Установите переменную VK_TOKEN в Railway Dashboard")
    print("   Токен должен начинаться с 'vk1.a.'")

print("="*70 + "\n")

# =================== ОСНОВНОЙ ОБРАБОТЧИК ===================
@app.post("/callback")
async def vk_callback(request: Request):
    """Обработчик Callback API от VK"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📥 ПОЛУЧЕН ЗАПРОС НА /callback")
    
    try:
        # Получаем тело запроса
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8', errors='ignore')
        
        if not body_str or body_str.strip() == "":
            print("⚠️ Пустое тело запроса, возвращаем 'ok'")
            return PlainTextResponse("ok")
        
        # Парсим JSON
        try:
            data = json.loads(body_str)
        except json.JSONDecodeError:
            print("⚠️ Невалидный JSON в запросе")
            return PlainTextResponse("ok")
        
        event_type = data.get("type", "unknown")
        group_id = data.get("group_id", 0)
        
        print(f"📌 Тип события: {event_type}")
        print(f"📌 ID группы из запроса: {group_id}")
        
        # 1. ПОДТВЕРЖДЕНИЕ
        if event_type == "confirmation":
            print(f"🔐 Отправляем код подтверждения: {CONFIRMATION_CODE}")
            return PlainTextResponse(CONFIRMATION_CODE)
        
        # 2. НОВОЕ СООБЩЕНИЕ
        elif event_type == "message_new":
            message = data["object"]["message"]
            text = message.get("text", "").strip()
            user_id = message.get("from_id", 0)
            peer_id = message.get("peer_id", 0)
            
            print(f"👤 Сообщение от пользователя: {user_id}")
            print(f"💬 Peer ID: {peer_id}")
            print(f"📝 Текст ({len(text)} символов):")
            print("-" * 50)
            print(text[:500])
            if len(text) > 500:
                print(f"... (еще {len(text)-500} символов)")
            print("-" * 50)
            
            # Проверяем, это анкета или нет
            if "Анкета Вашего персонажа" in text:
                print("🎯 ОБНАРУЖЕНА АНКЕТА!")
                
                # Очищаем текст от лишнего
                clean_text = clean_anketa_text(text)
                
                # Парсим анкету
                answers = parse_anketa_q_a(clean_text)
                print(f"📊 Распарсено полей: {len(answers)}")
                
                if answers:
                    # Формируем сообщение для вас
                    message_to_you = format_full_anketa(answers, user_id)
                    
                    # Отправляем вам
                    print(f"\n📤 ОТПРАВКА ВАМ (ID: {YOUR_ID})...")
                    success_to_you = send_vk_message(
                        user_id=YOUR_ID,
                        message=message_to_you,
                        is_chat=False
                    )
                    
                    if success_to_you:
                        print("✅ Анкета отправлена вам")
                        
                        # Формируем уведомление для чата
                        message_to_chat = format_chat_notification(answers, user_id)
                        
                        # Отправляем в чат
                        print(f"\n📤 ОТПРАВКА В ЧАТ (ID: {CHAT_PEER_ID})...")
                        success_to_chat = send_vk_message(
                            peer_id=CHAT_PEER_ID,
                            message=message_to_chat,
                            is_chat=True
                        )
                        
                        if success_to_chat:
                            print("✅ Уведомление отправлено в чат")
                        else:
                            print("❌ Не удалось отправить в чат")
                    else:
                        print("❌ Не удалось отправить анкету вам")
                        print("⚠️ Проверьте токен в Railway Variables")
                else:
                    print("⚠️ Анкета не распарсилась")
                    # Отправляем уведомление об ошибке
                    send_vk_message(
                        user_id=YOUR_ID,
                        message=f"⚠️ Анкета от {user_id} не распарсилась\n\nПервые 500 символов:\n{text[:500]}",
                        is_chat=False
                    )
            else:
                print("⏭️ Не анкета, игнорируем")
        
        else:
            print(f"ℹ️ Игнорируем неизвестное событие: {event_type}")
    
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА В CALLBACK: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ ОБРАБОТКА ЗАВЕРШЕНА\n")
    return PlainTextResponse("ok")

# =================== ФУНКЦИИ ОБРАБОТКИ ===================
def clean_anketa_text(text: str) -> str:
    """Очистка текста анкеты от лишней информации"""
    # Удаляем заголовки и личные данные
    patterns_to_remove = [
        r'Новый ответ в опросе:.*?\n',
        r'Анастасия Смоль.*?\n',
        r'Диалог:.*?\n',
        r'vk\.com/.*?\n',
        r'\?sel=.*?\n'
    ]
    
    cleaned = text
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()

def parse_anketa_q_a(text: str) -> dict:
    """Парсинг анкеты в формате Q: A:"""
    answers = {}
    
    # Паттерн для поиска Q: вопрос A: ответ
    pattern = r'Q[:.]\s*(.*?)\s*A[:.]\s*(.*?)(?=Q[:.]|$)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    print(f"🔍 Найдено {len(matches)} пар вопрос-ответ")
    
    # Точное соответствие вопросов полям
    question_to_field = {
        # Полные вопросы из виджета
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
        "Навыки, таланты, недостатки": "Навыки",
        
        # Сокращенные варианты (на всякий случай)
        "Имя персонажа": "Имя",
        "Возраст персонажа": "Возраст",
        "Происхождение": "Происхождение",
        "Позиция": "Позиция",
        "Телосложение": "Телосложение",
        "Рост": "Рост",
        "Цвет глаз": "Глаза",
        "Цвет шерсти": "Шерсть",
        "Ссылка на референс": "Ссылка на реф",
        "Внешность": "Внешность",
        "Характер": "Характер",
        "Цели": "Цели",
        "История": "История",
        "Навыки": "Навыки"
    }
    
    for question, answer in matches:
        question = question.strip()
        answer = answer.strip()
        
        # Ищем точное соответствие
        for q_template, field_name in question_to_field.items():
            if q_template.lower() in question.lower():
                answers[field_name] = answer
                print(f"   ✅ {field_name}: {answer[:50]}{'...' if len(answer) > 50 else ''}")
                break
        else:
            print(f"   ⚠️ Неизвестный вопрос: '{question[:50]}...'")
    
    return answers

def format_full_anketa(answers: dict, user_id: int) -> str:
    """Форматирование полной анкеты для модератора"""
    emoji_map = {
        "Имя": "👤", "Пол": "⚧️", "Возраст": "🎂",
        "Происхождение": "🌍", "Позиция": "🏹", "Телосложение": "💪",
        "Рост": "📏", "Глаза": "👁️", "Шерсть": "🐾",
        "Ссылка на реф": "🔗", "Внешность": "🎭", "Характер": "🧠",
        "Характер подробнее": "📖", "Цели": "🎯", "Навыки": "🛠️",
        "История": "📜"
    }
    
    lines = [
        f"🎯 НОВАЯ АНКЕТА",
        f"👤 От: VK ID {user_id}",
        f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
        ""
    ]
    
    # Порядок полей
    field_order = [
        "Имя", "Пол", "Возраст", "Происхождение", "Позиция",
        "Телосложение", "Рост", "Глаза", "Шерсть", "Ссылка на реф",
        "Внешность", "Характер", "Характер подробнее", "Цели",
        "Навыки", "История"
    ]
    
    for field in field_order:
        emoji = emoji_map.get(field, "•")
        value = answers.get(field, "—")
        lines.append(f"{emoji} {field}: {value}")
    
    return "\n".join(lines)

def format_chat_notification(answers: dict, user_id: int) -> str:
    """Краткое уведомление для чата"""
    name = answers.get("Имя", "Не указано")
    gender = answers.get("Пол", "Не указано")
    age = answers.get("Возраст", "Не указано")
    position = answers.get("Позиция", "Не указано")
    
    return f"""🎯 НОВАЯ АНКЕТА!

👤 Персонаж: {name}
⚧️ Пол: {gender}
🎂 Возраст: {age}
🏹 Позиция: {position}

📝 Анкета отправлена на модерацию.
🕒 {datetime.now().strftime('%H:%M')}"""

def send_vk_message(user_id: int = None, peer_id: int = None, message: str = "", is_chat: bool = False) -> bool:
    """
    Отправка сообщения через VK API
    КЛЮЧЕВОЙ МОМЕНТ: access_token должен передаваться в параметрах!
    """
    if not TOKEN:
        print("❌ Невозможно отправить: токен не установлен!")
        return False
    
    try:
        # ОСНОВНЫЕ ПАРАМЕТРЫ (access_token ОБЯЗАТЕЛЕН!)
        params = {
            "access_token": TOKEN,  # ⚠️ ЭТО КЛЮЧЕВОЙ ПАРАМЕТР!
            "v": VK_API_VERSION,
            "message": message,
            "random_id": random.randint(1, 10**9)
        }
        
        # Добавляем user_id или peer_id
        if is_chat and peer_id:
            params["peer_id"] = peer_id
            print(f"   📍 Отправка в чат (peer_id: {peer_id})")
        elif user_id:
            params["user_id"] = user_id
            print(f"   📍 Отправка пользователю (user_id: {user_id})")
        else:
            print("❌ Не указан получатель")
            return False
        
        # Логируем параметры (без токена)
        safe_params = params.copy()
        safe_params["access_token"] = f"{TOKEN[:5]}...{TOKEN[-5:]}" if len(TOKEN) > 10 else "***"
        print(f"   📦 Параметры запроса: {safe_params}")
        
        # Отправляем запрос
        response = requests.post(
            "https://api.vk.com/method/messages.send",
            data=params,  # ⚠️ Важно: data=, не json=
            timeout=15
        )
        
        result = response.json()
        print(f"   📥 Ответ VK API: {result}")
        
        if "error" in result:
            error = result["error"]
            error_code = error.get("error_code")
            error_msg = error.get("error_msg")
            
            print(f"❌ Ошибка VK API (код {error_code}): {error_msg}")
            
            if error_code == 5:
                print("⚠️ Проблема с токеном!")
                print("⚠️ Проверьте:")
                print("   1. Токен установлен в Railway Variables (VK_TOKEN)")
                print("   2. Токен действительный (не просрочен)")
                print("   3. Токен имеет права на отправку сообщений")
            
            return False
        
        print("✅ Сообщение успешно отправлено")
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Таймаут при отправке сообщения")
        return False
    except Exception as e:
        print(f"❌ Ошибка при отправке: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# =================== ТЕСТОВЫЕ ENDPOINTS ===================
@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "status": "VK Анкета-бот активен",
        "endpoints": {
            "/": "Это сообщение",
            "/callback": "POST: обработка VK Callback API",
            "/check": "Проверка конфигурации",
            "/test-send": "Тест отправки сообщений",
            "/test-parse": "Тест парсинга анкеты"
        },
        "time": datetime.now().isoformat()
    }

@app.get("/check")
async def check_config():
    """Проверка конфигурации"""
    return {
        "config": {
            "has_token": bool(TOKEN),
            "token_length": len(TOKEN) if TOKEN else 0,
            "group_id": GROUP_ID,
            "your_id": YOUR_ID,
            "chat_id": CHAT_PEER_ID,
            "confirmation_code": CONFIRMATION_CODE,
            "api_version": VK_API_VERSION
        },
        "system": {
            "timestamp": datetime.now().isoformat(),
            "environment": os.environ.get("RAILWAY_ENVIRONMENT", "unknown")
        }
    }

@app.get("/test-send")
async def test_send():
    """Тест отправки сообщений"""
    test_message = f"🤖 Тестовое сообщение от бота\n🕒 Время: {datetime.now().strftime('%H:%M:%S')}"
    
    results = {
        "to_you": "not_attempted",
        "to_chat": "not_attempted"
    }
    
    # Тест отправки вам
    if TOKEN:
        print("\n🔧 ТЕСТ ОТПРАВКИ ВАМ...")
        success = send_vk_message(
            user_id=YOUR_ID,
            message=test_message,
            is_chat=False
        )
        results["to_you"] = "success" if success else "failed"
        
        # Тест отправки в чат
        print("\n🔧 ТЕСТ ОТПРАВКИ В ЧАТ...")
        success = send_vk_message(
            peer_id=CHAT_PEER_ID,
            message=test_message,
            is_chat=True
        )
        results["to_chat"] = "success" if success else "failed"
    else:
        results["to_you"] = "no_token"
        results["to_chat"] = "no_token"
    
    return {
        "test_results": results,
        "message": test_message,
        "token_available": bool(TOKEN)
    }

@app.get("/test-parse")
async def test_parse():
    """Тест парсинга анкеты"""
    test_anketa = """Q: Имя персонажа (полное, со знаками ударения), сокращения, клички
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
    
    answers = parse_anketa_q_a(test_anketa)
    
    return {
        "parsed_fields": len(answers),
        "fields": list(answers.keys()),
        "sample": {k: v[:50] + "..." if len(v) > 50 else v for k, v in list(answers.items())[:3]},
        "full_parsed": answers
    }

@app.get("/callback")
async def callback_get():
    """GET endpoint для /callback"""
    return {
        "message": "Это GET endpoint. VK использует POST для Callback API",
        "confirmation_code": CONFIRMATION_CODE,
        "usage": "VK будет отправлять POST запросы сюда",
        "check_endpoints": "Используйте /check для проверки конфигурации"
    }

# =================== ЗАПУСК СЕРВЕРА ===================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"\n🌐 Запуск сервера на порту {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
