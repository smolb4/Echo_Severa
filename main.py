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
TOKEN = os.environ.get("VK_TOKEN", "vk1.a.sq5rMHr7_eVlqS9xPvZKC2faTUGZBGT0EeXkSYGIpw1dAe0a6Rrw_hHUSsicD21cRLAUcGd_hzA_BLd0R37aOa7fGCf9vpPkUwRT9uOJlSiMQHCZz397zimUVgVZz9jgV_OOv5vmX6I5aoRAMfCMm0NEgxMd9UgmFgISq_krk2fBhaWC5S6wjvki3apnVH19xScFwNFkOUELvD0DPJQNyA")
GROUP_ID = int(os.environ.get("VK_GROUP_ID", "235128907"))
YOUR_ID = int(os.environ.get("YOUR_VK_ID", "388182166"))
CHAT_PEER_ID = int(os.environ.get("CHAT_PEER_ID", "2000000001"))
CONFIRMATION_CODE = os.environ.get("VK_CONFIRMATION_CODE", "744eebe2")
VK_API_VERSION = "5.199"

# Принудительный сброс будера логов
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
    print("❌ ВНИМАНИЕ: Токен не найден!")
    print("   Установите переменную VK_TOKEN в Railway Dashboard")

print("="*70 + "\n")

# =================== ОСНОВНОЙ ОБРАБОТЧИК ===================
@app.post("/callback")
async def vk_callback(request: Request):
    """Обработчик Callback API от VK - ИСПРАВЛЕННЫЙ"""
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
            
            print(f"👤 Сообщение от пользователя: {user_id}")
            print(f"📝 Длина текста: {len(text)} символов")
            
            # ОТЛАДКА: логируем начало сообщения
            print("📋 Первые 300 символов текста:")
            print("-" * 50)
            print(text[:300])
            print("-" * 50)
            
            # ПРОВЕРКА: Это анкета из виджета?
            is_anketa = check_if_anketa_from_widget(text)
            
            if is_anketa:
                print("🎯 АНКЕТА ИЗ ВИДЖЕТА ОБНАРУЖЕНА!")
                
                # Очищаем текст от лишнего
                clean_text = clean_widget_text(text)
                
                # Парсим анкету
                answers = parse_widget_anketa(clean_text)
                
                print(f"📊 Распарсено полей: {len(answers)}")
                
                if answers:
                    # Логируем что распарсили
                    for field, value in answers.items():
                        if value:
                            print(f"   ✅ {field}: {value[:80]}{'...' if len(value) > 80 else ''}")
                    
                    # 1. Отправляем полную анкету вам
                    message_to_you = format_full_anketa_for_you(answers, user_id)
                    print(f"\n📤 ОТПРАВКА ПОЛНОЙ АНКЕТЫ ВАМ (ID: {YOUR_ID})...")
                    success_to_you = send_vk_message(
                        user_id=YOUR_ID,
                        message=message_to_you,
                        is_chat=False
                    )
                    
                    if success_to_you:
                        print("✅ Полная анкета отправлена вам")
                        
                        # 2. Отправляем краткое уведомление в чат
                        message_to_chat = format_short_notification_for_chat(answers, user_id)
                        print(f"\n📤 ОТПРАВКА УВЕДОМЛЕНИЯ В ЧАТ (ID: {CHAT_PEER_ID})...")
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
                    # Отправляем сообщение об ошибке
                    error_msg = f"⚠️ Анкета от {user_id} не распарсилась\n\nНачало текста:\n{text[:500]}"
                    send_vk_message(YOUR_ID, error_msg, is_chat=False)
            else:
                print("⏭️ Не анкета, пропускаем")
        
        else:
            print(f"ℹ️ Игнорируем неизвестное событие: {event_type}")
    
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА В CALLBACK: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ ОБРАБОТКА ЗАВЕРШЕНА\n")
    return PlainTextResponse("ok")

# =================== ФУНКЦИИ ДЛЯ ВИДЖЕТА VK ===================
def check_if_anketa_from_widget(text: str) -> bool:
    """Проверяет, является ли сообщение анкетой из виджета VK"""
    # Все возможные признаки анкеты из виджета
    indicators = [
        "Новый ответ в опросе: Анкета",
        "Анкета Вашего персонажа для РП сегмента проекта Эхо Севера",
        "Q: Имя персонажа (полное, со знаками ударения), сокращения, клички",
        "Q: Пол персонажа",
        "Q: Возраст персонажа",
        "Диалог: vk.com/gim"
    ]
    
    for indicator in indicators:
        if indicator in text:
            print(f"📌 Обнаружен индикатор: '{indicator[:50]}...'")
            return True
    
    # Дополнительная проверка по количеству Q:
    q_count = text.count("Q:")
    a_count = text.count("A:")
    
    if q_count >= 5 and a_count >= 5:  # Если много вопросов-ответов
        print(f"📌 Много Q/A пар: {q_count} вопросов, {a_count} ответов")
        return True
    
    return False

def clean_widget_text(text: str) -> str:
    """Очищает текст анкеты от лишних заголовков виджета"""
    # Удаляем заголовки до первого Q:
    lines = text.split('\n')
    cleaned_lines = []
    found_first_q = False
    
    for line in lines:
        line = line.strip()
        
        # Пропускаем пустые строки в начале
        if not line and not found_first_q:
            continue
        
        # Ищем первый Q:
        if line.startswith("Q:"):
            found_first_q = True
        
        # После нахождения первого Q: добавляем все строки
        if found_first_q:
            cleaned_lines.append(line)
    
    # Если не нашли Q:, возвращаем оригинальный текст
    if not found_first_q:
        return text
    
    return '\n'.join(cleaned_lines)

def parse_widget_anketa(text: str) -> dict:
    """Парсит анкету из виджета VK (формат Q: A:)"""
    answers = {}
    
    print("🔍 Начинаем парсинг анкеты из виджета...")
    
    # Разбиваем текст на блоки Q: ... A: ...
    # Используем регулярное выражение для поиска всех пар Q/A
    pattern = r'Q:\s*(.*?)\s*A:\s*(.*?)(?=\s*Q:\s*|$)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    print(f"🔍 Найдено Q/A пар: {len(matches)}")
    
    # Точное соответствие вопросов из виджета
    question_to_field = {
        # Полные вопросы как в виджете
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
    }
    
    for question, answer in matches:
        question = question.strip()
        answer = answer.strip()
        
        # Логируем для отладки
        print(f"   📝 Вопрос: '{question[:60]}...'")
        print(f"   📝 Ответ: '{answer[:60]}...'")
        
        # Ищем точное соответствие вопроса
        field_name = None
        
        # 1. Пробуем точное совпадение
        if question in question_to_field:
            field_name = question_to_field[question]
        else:
            # 2. Пробуем частичное совпадение
            for q_template, field in question_to_field.items():
                if q_template in question:
                    field_name = field
                    break
        
        if field_name:
            answers[field_name] = answer
            print(f"   ✅ Сопоставлено: {field_name}")
        else:
            print(f"   ⚠️ Неизвестный вопрос: '{question[:50]}...'")
    
    return answers

def format_full_anketa_for_you(answers: dict, user_id: int) -> str:
    """Форматирует полную анкету для отправки вам"""
    emoji_map = {
        "Имя": "👤", "Пол": "⚧️", "Возраст": "🎂",
        "Происхождение": "🌍", "Позиция": "🏹", "Телосложение": "💪",
        "Рост": "📏", "Глаза": "👁️", "Шерсть": "🐾",
        "Ссылка на реф": "🔗", "Внешность": "🎭", "Характер": "🧠",
        "Характер подробнее": "📖", "Цели": "🎯", "Навыки": "🛠️",
        "История": "📜"
    }
    
    # Порядок полей
    field_order = [
        "Имя", "Пол", "Возраст", "Происхождение", "Позиция",
        "Телосложение", "Рост", "Глаза", "Шерсть", "Ссылка на реф",
        "Внешность", "Характер", "Характер подробнее", "Цели",
        "Навыки", "История"
    ]
    
    lines = [
        f"🎯 НОВАЯ АНКЕТА ИЗ ВИДЖЕТА VK",
        f"👤 От: VK ID {user_id}",
        f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
        f"",
    ]
    
    for field in field_order:
        emoji = emoji_map.get(field, "•")
        value = answers.get(field, "—")
        lines.append(f"{emoji} {field}: {value}")
    
    lines.append(f"")
    lines.append(f"📋 Всего заполнено полей: {len([v for v in answers.values() if v and v.strip()])}/16")
    
    return "\n".join(lines)

def format_short_notification_for_chat(answers: dict, user_id: int) -> str:
    """Форматирует краткое уведомление для чата"""
    name = answers.get("Имя", "Не указано")[:50]
    gender = answers.get("Пол", "Не указано")
    age = answers.get("Возраст", "Не указано")
    position = answers.get("Позиция", "Не указано")
    origin = answers.get("Происхождение", "Не указано")
    
    filled_count = len([v for v in answers.values() if v and v.strip()])
    
    return f"""🎯 НОВАЯ АНКЕТА!

👤 Персонаж: {name}
⚧️ Пол: {gender}
🎂 Возраст: {age}
🏹 Позиция: {position}
🌍 Происхождение: {origin}

📝 Заполнено полей: {filled_count}/16
🕒 {datetime.now().strftime('%H:%M')}
👤 Отправлено от VK ID: {user_id}"""

# =================== ОТПРАВКА СООБЩЕНИЙ ===================
def send_vk_message(user_id: int = None, peer_id: int = None, message: str = "", is_chat: bool = False) -> bool:
    """Отправляет сообщение через VK API"""
    if not TOKEN:
        print("❌ Невозможно отправить: токен не установлен!")
        return False
    
    try:
        # ОСНОВНЫЕ ПАРАМЕТРЫ
        params = {
            "access_token": TOKEN,  # КЛЮЧЕВОЙ ПАРАМЕТР!
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
        
        # Логируем параметры (без полного токена)
        safe_params = params.copy()
        if "access_token" in safe_params:
            token = safe_params["access_token"]
            if len(token) > 10:
                safe_params["access_token"] = f"{token[:5]}...{token[-5:]}"
            else:
                safe_params["access_token"] = "***"
        
        print(f"   📦 Параметры запроса: {safe_params}")
        print(f"   📝 Длина сообщения: {len(message)} символов")
        
        # Отправляем запрос
        response = requests.post(
            "https://api.vk.com/method/messages.send",
            data=params,  # Важно: data=, не json=
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
            elif error_code == 7:
                print("⚠️ Нет прав для отправки")
            elif error_code == 901:
                print("⚠️ Пользователь не разрешил сообщения")
            
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
        "service": "Обработка анкет из виджета VK",
        "endpoints": {
            "/": "Это сообщение",
            "/check": "Проверка конфигурации",
            "/test-send": "Тест отправки сообщений",
            "/test-widget": "Тест парсинга виджета"
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
            "environment": "Railway"
        }
    }

@app.get("/test-send")
async def test_send():
    """Тест отправки сообщений"""
    test_message = f"🤖 Тестовое сообщение от бота\n🕒 Время: {datetime.now().strftime('%H:%M:%S')}\n✅ Работает!"
    
    results = {
        "to_you": "not_attempted",
        "to_chat": "not_attempted"
    }
    
    if TOKEN:
        print("\n🔧 ТЕСТ ОТПРАВКИ ВАМ...")
        success = send_vk_message(
            user_id=YOUR_ID,
            message=test_message,
            is_chat=False
        )
        results["to_you"] = "success" if success else "failed"
        
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

@app.get("/test-widget")
async def test_widget_parsing():
    """Тест парсинга виджета VK"""
    test_widget_text = """Новый ответ в опросе: Анкета Вашего персонажа для РП сегмента проекта Эхо Севера
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
A: Шрамы на морде, хромает на левую лапу

Q: Основные черты характера через запятую
A: Храбрый, упрямый, верный

Q: Подробнее о характере
A: Очень предан племени, но иногда слишком импульсивен

Q: Цели и планы персонажа на ближайшее будущее
A: Стать лидером охотничьего отряда

Q: Здесь Вы можете написать историю персонажа:
A: Родился в семье воинов, с детства обучался боевым искусствам

Q: Навыки, таланты, недостатки
A: Отличный охотник, плохо плавает, быстро бегает"""
    
    print("\n🔧 ТЕСТ ПАРСИНГА ВИДЖЕТА VK...")
    
    # Проверяем определение анкеты
    is_anketa = check_if_anketa_from_widget(test_widget_text)
    print(f"📌 Определено как анкета: {is_anketa}")
    
    # Очищаем текст
    clean_text = clean_widget_text(test_widget_text)
    print(f"📌 Длина очищенного текста: {len(clean_text)} символов")
    
    # Парсим
    answers = parse_widget_anketa(clean_text)
    
    # Форматируем
    if answers:
        formatted_for_you = format_full_anketa_for_you(answers, 123456)
        formatted_for_chat = format_short_notification_for_chat(answers, 123456)
        
        return {
            "is_anketa": is_anketa,
            "parsed_fields": len(answers),
            "fields": list(answers.keys()),
            "sample_data": {k: v[:100] for k, v in list(answers.items())[:3]},
            "formatted_lengths": {
                "for_you": len(formatted_for_you),
                "for_chat": len(formatted_for_chat)
            }
        }
    else:
        return {
            "is_anketa": is_anketa,
            "parsed_fields": 0,
            "error": "Не удалось распарсить анкету"
        }

@app.get("/callback")
async def callback_get():
    """GET endpoint для /callback"""
    return {
        "message": "Это GET endpoint. VK использует POST для Callback API",
        "confirmation_code": CONFIRMATION_CODE,
        "note": "VK будет отправлять POST запросы с событиями message_new",
        "test_links": {
            "check_config": "/check",
            "test_send": "/test-send",
            "test_widget": "/test-widget"
        }
    }

# =================== ЗАПУСК СЕРВЕРА ===================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"\n🌐 Запуск сервера на порту {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

