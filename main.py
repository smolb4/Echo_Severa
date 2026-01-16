from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests
import random
import json
import sys

app = FastAPI()
TOKEN = "vk1.a.sq5rMHr7_eVlqS9xPvZKC2faTUGZBGT0EeXkSYGIpw1dAe0a6Rrw_hHUSsicD21cRLAUcGd_hzA_BLd0R37aOa7fGCf9vpPkUwRT9uOJlSiMQHCZz397zimUVgVZz9jgV_OOv5vmX6I5aoRAMfCMm0NEgxMd9UgmFgISq_krk2fBhaWC5S6wjvki3apnVH19xScFwNFkOUELvD0DPJQNyA"
GROUP_ID = -235128907

# Принудительный сброс буфера логов
import functools
print = functools.partial(print, flush=True)

@app.post("/form")
async def form(request: Request):
    try:
        data = await request.json()
    except:
        return {"error": "Некорректный JSON"}

    name = data.get("Имя", "")
    gender = data.get("Пол", "")
    age = data.get("Возраст", "")
    country = data.get("Происхождение", "")
    role = data.get("Позиция", "")
    body = data.get("Телосложение", "")
    height = data.get("Рост", "")
    eye = data.get("Глаза", "")
    wool = data.get("Шерсть", "")
    ref = data.get("Ссылка на реф", "")
    look = data.get("Внешность", "")
    character = data.get("Характер", "")
    character2 = data.get("Характер подробнее", "")
    goals = data.get("Цели", "")
    skills = data.get("Навыки", "")

    text = f"""Новая заявка
Имя: {name}
Пол: {gender}
Возраст: {age}
Происхождение: {country}
Позиция: {role}
Телосложение: {body}
Рост: {height}
Глаза: {eye}
Шерсть: {wool}
Ссылка на реф: {ref}
Внешность: {look}
Характер: {character}
Характер подробнее: {character2}
Цели: {goals}
Навыки: {skills}
"""
    try:
        requests.post(
            "https://api.vk.com/method/messages.send",
            data={
                "peer_id": 388182166,
                "message": text,
                "random_id": random.randint(1, 10**9),
                "access_token": TOKEN,
                "v": "5.131"
            }
        )
    except Exception as e:
        return {"error": str(e)}

    return {"ok": True}

@app.post("/callback")
async def vk_callback(request: Request):
    """Callback для ВК с логированием"""
    # Логируем факт запроса
    sys.stdout.write("CALLBACK: Запрос получен от ВК\n")
    sys.stdout.flush()
    
    try:
        # Читаем сырые данные
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8') if body_bytes else ""
        
        # Логируем что пришло
        sys.stdout.write(f"Сырые данные: {body_str[:500]}\n")
        sys.stdout.flush()
        
        if not body_str:
            return PlainTextResponse("ok")
        
        data = json.loads(body_str)
        
        # Подтверждение для ВК
        if data.get("type") == "confirmation":
            sys.stdout.write("Отправляем код: 10707297\n")
            sys.stdout.flush()
            return PlainTextResponse("10707297")
        
        # Новое сообщение
        if data.get("type") == "message_new":
            message = data["object"]["message"]
            text = message.get("text", "")
            user_id = message.get("from_id", 0)
            
            sys.stdout.write(f"Сообщение от {user_id}: {text[:100]}\n")
            sys.stdout.flush()
            
            # Проверяем ключевые слова
            keywords = ["анкет", "опрос", "заполнил", "прошел", "заявка"]
            text_lower = text.lower()
            
            if any(keyword in text_lower for keyword in keywords):
                sys.stdout.write(f"Это анкета! Отправляем уведомление\n")
                sys.stdout.flush()
                
                # Отправляем тебе сообщение
                requests.post(
                    "https://api.vk.com/method/messages.send",
                    data={
                        "peer_id": 388182166,
                        "message": f"Кто-то заполнил анкету! ID: {user_id}",
                        "random_id": random.randint(1, 10**9),
                        "access_token": TOKEN,
                        "v": "5.131"
                    }
                )
    
    except Exception as e:
        sys.stdout.write(f"Ошибка: {str(e)}\n")
        sys.stdout.flush()
    
    return PlainTextResponse("ok")

@app.get("/callback")
async def check():
    return {"status": "сервер работает", "code": "10707297"}

@app.get("/")
async def root():
    return {"статус": "VK Bot активен"}

# Тестовый endpoint для проверки логов
@app.get("/debug")
async def debug():
    sys.stdout.write("DEBUG: Тестовое сообщение в логах\n")
    sys.stdout.flush()
    return {"debug": "ok", "message": "проверь логи railway"}
