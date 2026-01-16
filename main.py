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
    """Callback для ВК - парсим анкету по названию"""
    sys.stdout.write("CALLBACK: Запрос получен\n")
    sys.stdout.flush()
    
    try:
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8') if body_bytes else ""
        
        if not body_str:
            return PlainTextResponse("ok")
        
        data = json.loads(body_str)
        
        # Подтверждение для ВК
        if data.get("type") == "confirmation":
            return PlainTextResponse("10707297")
        
        # Новое сообщение
        if data.get("type") == "message_new":
            message = data["object"]["message"]
            text = message.get("text", "")
            user_id = message.get("from_id", 0)
            
            sys.stdout.write(f"Сообщение от {user_id}: {text[:150]}...\n")
            sys.stdout.flush()
            
            # ПРОВЕРЯЕМ НАЗВАНИЕ АНКЕТЫ
            if "Анкета Вашего персонажа для РП сегмента проекта Эхо Севера" in text:
                sys.stdout.write("Найдена нужная анкета! Парсим...\n")
                sys.stdout.flush()
                
                # Парсим данные из формата Q/A
                answers = parse_answers_from_q_a(text)
                
                # Формируем сообщение в ТВОЁМ формате
                formatted_message = create_formatted_application(answers, user_id)
                
                # Отправляем тебе
                requests.post(
                    "https://api.vk.com/method/messages.send",
                    data={
                        "peer_id": 388182166,
                        "message": formatted_message,
                        "random_id": random.randint(1, 10**9),
                        "access_token": TOKEN,
                        "v": "5.131"
                    }
                )
                
                # Ответ пользователю
                requests.post(
                    "https://api.vk.com/method/messages.send",
                    data={
                        "user_id": user_id,
                        "message": "✅ Ваша анкета персонажа получена! Спасибо!",
                        "random_id": random.randint(1, 10**9),
                        "access_token": TOKEN,
                        "v": "5.131"
                    }
                )
    
    except Exception as e:
        sys.stdout.write(f"Ошибка: {str(e)}\n")
        sys.stdout.flush()
    
    return PlainTextResponse("ok")


def parse_answers_from_q_a(text: str) -> dict:
    """Извлекает ответы из формата Q: A:"""
    answers = {}
    
    # Маппинг вопросов из виджета к твоим полям
    question_mapping = {
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
    
    lines = text.split('\n')
    current_question = ""
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("Q:"):
            current_question = line[2:].strip()
            
        elif line.startswith("A:") and current_question:
            answer = line[2:].strip()
            
            # Если вопрос есть в маппинге - сохраняем
            if current_question in question_mapping:
                field_name = question_mapping[current_question]
                answers[field_name] = answer
    
    return answers


def create_formatted_application(answers: dict, user_id: int) -> str:
    """Создаёт анкету в ТВОЁМ формате"""
    
    # Твой точный формат
    text = f"""Новая заявка
Имя: {answers.get("Имя", "")}
Пол: {answers.get("Пол", "")}
Возраст: {answers.get("Возраст", "")}
Происхождение: {answers.get("Происхождение", "")}
Позиция: {answers.get("Позиция", "")}
Телосложение: {answers.get("Телосложение", "")}
Рост: {answers.get("Рост", "")}
Глаза: {answers.get("Глаза", "")}
Шерсть: {answers.get("Шерсть", "")}
Ссылка на реф: {answers.get("Ссылка на реф", "")}
Внешность: {answers.get("Внешность", "")}
Характер: {answers.get("Характер", "")}
Характер подробнее: {answers.get("Характер подробнее", "")}
Цели: {answers.get("Цели", "")}
Навыки: {answers.get("Навыки", "")}
"""
    return text

@app.get("/callback")
async def check():
    return {"status": "сервер работает", "code": "10707297"}

@app.get("/")
async def root():
    return {"статус": "VK Bot активен"}
