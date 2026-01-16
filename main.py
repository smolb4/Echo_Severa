# main.py - УПРОЩЕННЫЙ РАБОЧИЙ КОД
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests
import random
import json
import os
import re
from datetime import datetime

app = FastAPI()

# =================== КОНФИГУРАЦИЯ ===================
TOKEN = os.environ.get("VK_TOKEN", "vk1.a.sq5rMHr7_eVlqS9xPvZKC2faTUGZBGT0EeXkSYGIpw1dAe0a6Rrw_hHUSsicD21cRLAUcGd_hzA_BLd0R37aOa7fGCf9vpPkUwRT9uOJlSiMQHCZz397zimUVgVZz9jgV_OOv5vmX6I5aoRAMfCMm0NEgxMd9UgmFgISq_krk2fBhaWC5S6wjvki3apnVH19xScFwNFkOUELvD0DPJQNyA")
GROUP_ID = int(os.environ.get("VK_GROUP_ID", "235128907"))
YOUR_ID = int(os.environ.get("YOUR_VK_ID", "388182166"))
CHAT_PEER_ID = int(os.environ.get("CHAT_PEER_ID", "2000000001"))
CONFIRMATION_CODE = os.environ.get("VK_CONFIRMATION_CODE", "744eebe2")
VK_API_VERSION = "5.199"

print(f"Бот запущен. Токен: {'есть' if TOKEN else 'НЕТ'}")

# =================== ОСНОВНОЙ ОБРАБОТЧИК ===================
@app.post("/callback")
async def vk_callback(request: Request):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Запрос от VK")
    
    try:
        data = await request.json()
        
        if data.get("type") == "confirmation":
            print(f"Отправляем код: {CONFIRMATION_CODE}")
            return PlainTextResponse(CONFIRMATION_CODE)
        
        elif data.get("type") == "message_new":
            message = data["object"]["message"]
            text = message.get("text", "")
            user_id = message.get("from_id", 0)
            
            print(f"Сообщение от {user_id}, символов: {len(text)}")
            
            # Проверяем анкету
            if "Новый ответ в опросе: Анкета" in text or "Q: Имя персонажа" in text:
                print("Найдена анкета!")
                
                # Парсим
                answers = parse_anketa(text)
                print(f"Распарсено полей: {len(answers)}")
                
                if answers:
                    # Отправляем вам
                    msg_to_you = format_for_you(answers, user_id)
                    send_message(YOUR_ID, msg_to_you, is_chat=False)
                    
                    # Отправляем в чат
                    msg_to_chat = format_for_chat(answers, user_id)
                    send_message(CHAT_PEER_ID, msg_to_chat, is_chat=True)
                    
                    print("Анкета обработана")
                else:
                    print("Не удалось распарсить")
                    send_message(YOUR_ID, f"Ошибка парсинга от {user_id}", is_chat=False)
    
    except Exception as e:
        print(f"Ошибка: {e}")
    
    return PlainTextResponse("ok")

# =================== ПАРСИНГ ===================
def parse_anketa(text: str) -> dict:
    """Парсинг анкеты из виджета"""
    answers = {}
    
    # Ищем все Q: A: пары
    pattern = r'Q:\s*(.*?)\s*A:\s*(.*?)(?=\s*Q:\s*|$)'
    matches = re.findall(pattern, text, re.DOTALL)
    
    print(f"Найдено пар Q/A: {len(matches)}")
    
    # Маппинг вопросов к полям
    question_to_field = {
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
        
        for q_template, field in question_to_field.items():
            if q_template == question:
                answers[field] = answer
                print(f"  {field}: {answer[:50]}")
                break
    
    return answers

def format_for_you(answers: dict, user_id: int) -> str:
    """Форматирование для вас"""
    fields = [
        "Имя", "Пол", "Возраст", "Происхождение", "Позиция",
        "Телосложение", "Рост", "Глаза", "Шерсть", "Ссылка на реф",
        "Внешность", "Характер", "Характер подробнее", "Цели",
        "Навыки", "История"
    ]
    
    lines = [f"Новая анкета от VK ID: {user_id}", ""]
    
    for field in fields:
        value = answers.get(field, "—")
        lines.append(f"{field}: {value}")
    
    lines.append(f"")
    lines.append(f"Время: {datetime.now().strftime('%H:%M:%S')}")
    
    return "\n".join(lines)

def format_for_chat(answers: dict, user_id: int) -> str:
    """Форматирование для чата"""
    name = answers.get("Имя", "Не указано")
    gender = answers.get("Пол", "Не указано")
    age = answers.get("Возраст", "Не указано")
    
    return f"""Новая анкета!

Персонаж: {name}
Пол: {gender}
Возраст: {age}

Отправлена на модерацию.
Время: {datetime.now().strftime('%H:%M')}"""

# =================== ОТПРАВКА ===================
def send_message(user_id: int = None, peer_id: int = None, message: str = "", is_chat: bool = False) -> bool:
    """Отправка сообщения"""
    if not TOKEN:
        print("Ошибка: токен не установлен")
        return False
    
    try:
        params = {
            "access_token": TOKEN,
            "v": VK_API_VERSION,
            "message": message,
            "random_id": random.randint(1, 10**9)
        }
        
        if is_chat and peer_id:
            params["peer_id"] = peer_id
        elif user_id:
            params["user_id"] = user_id
        else:
            return False
        
        response = requests.post(
            "https://api.vk.com/method/messages.send",
            data=params,
            timeout=10
        )
        
        result = response.json()
        
        if "error" in result:
            print(f"Ошибка отправки: {result['error']}")
            return False
        
        print("Сообщение отправлено")
        return True
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

# =================== ТЕСТЫ ===================
@app.get("/")
async def root():
    return {"status": "Бот работает"}

@app.get("/test")
async def test():
    """Тестовый endpoint"""
    if TOKEN:
        # Тест отправки вам
        send_message(YOUR_ID, f"Тест бота {datetime.now().strftime('%H:%M')}", is_chat=False)
        # Тест отправки в чат
        send_message(CHAT_PEER_ID, f"Тест бота {datetime.now().strftime('%H:%M')}", is_chat=True)
        return {"status": "тест отправлен"}
    else:
        return {"error": "токен не установлен"}

@app.get("/check")
async def check():
    """Проверка конфигурации"""
    return {
        "token": "есть" if TOKEN else "нет",
        "your_id": YOUR_ID,
        "chat_id": CHAT_PEER_ID,
        "code": CONFIRMATION_CODE
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
