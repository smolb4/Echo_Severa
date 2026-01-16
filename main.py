from fastapi import FastAPI, Request
import requests
import random

app = FastAPI()
TOKEN = "vk1.a.sq5rMHr7_eVlqS9xPvZKC2faTUGZBGT0EeXkSYGIpw1dAe0a6Rrw_hHUSsicD21cRLAUcGd_hzA_BLd0R37aOa7fGCf9vpPkUwRT9uOJlSiMQHCZz397zimUVgVZz9jgV_OOv5vmX6I5aoRAMfCMm0NEgxMd9UgmFgISq_krk2fBhaWC5S6wjvki3apnVH19xScFwNFkOUELvD0DPJQNyA"
GROUP_ID = -235128907

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
    """Callback для ВКонтакте"""
    try:
        # Пытаемся прочитать JSON
        data = await request.json()
        
        # Если это проверка от ВК
        if data.get("type") == "confirmation":
            print("VK confirmation request received")
            return "10707297"  # ← ВОЗВРАЩАЕМ КОД СТРОКОЙ!
        
        # Логируем что пришло
        print(f"VK callback data: {data}")
        
    except Exception as e:
        # Если ошибка - все равно возвращаем код
        print(f"Error in callback: {e}")
    
    # Всегда возвращаем "ok" для ВК
    return "ok"

@app.post("/callback", response_class=PlainTextResponse)  # ← ВАЖНО!
async def vk_callback(request: Request):
    """Возвращаем код подтверждения БЕЗ кавычек"""
    try:
        data = await request.json()
        if data.get("type") == "confirmation":
            # Возвращаем просто строку, FastAPI не добавит кавычки
            return "10707297"
    except:
        pass
    
    # Для всех других запросов
    return "ok"

@app.get("/callback")
async def check_callback():
    """Для проверки в браузере - оставляем как есть"""
    return {
        "status": "callback endpoint works",
        "confirmation_code": "10707297",
        "post_url": "https://echosevera-production-5f24.up.railway.app/callback",
        "method": "POST"
    }
