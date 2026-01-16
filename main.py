from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import random
import json
import sys
import re
from datetime import datetime
import os

app = FastAPI()

# Добавляем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройки из переменных окружения
TOKEN = os.getenv("VK_TOKEN", "vk1.a.sq5rMHr7_eVlqS9xPvZKC2faTUGZBGT0EeXkSYGIpw1dAe0a6Rrw_hHUSsicD21cRLAUcGd_hzA_BLd0R37aOa7fGCf9vpPkUwRT9uOJlSiMQHCZz397zimUVgVZz9jgV_OOv5vmX6I5aoRAMfCMm0NEgxMd9UgmFgISq_krk2fBhaWC5S6wjvki3apnVH19xScFwNFkOUELvD0DPJQNyA")
GROUP_ID = int(os.getenv("VK_GROUP_ID", "235128907"))
YOUR_ID = int(os.getenv("YOUR_VK_ID", "2000000001"))

# Принудительный сброс буфера логов
import functools
print = functools.partial(print, flush=True)

@app.post("/form")
async def form(request: Request):
    """Старый endpoint для формы"""
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
                "peer_id": YOUR_ID,
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
    print("\n" + "="*60)
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - НОВЫЙ ЗАПРОС")
    print("="*60)
    
    try:
        # Получаем тело запроса
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8', errors='ignore')
        
        print(f"Длина тела: {len(body_str)} символов")
        
        if not body_str or body_str.strip() == "":
            print("Пустое тело, возвращаем ok")
            return PlainTextResponse("ok")
        
        # Пробуем распарсить JSON
        try:
            data = json.loads(body_str)
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            print(f"Тело запроса: {body_str[:500]}")
            return PlainTextResponse("ok")
        
        print(f"Тип события: {data.get('type', 'неизвестно')}")
        
        # Подтверждение для ВК
        if data.get("type") == "confirmation":
            print(f"Запрос подтверждения для группы {data.get('group_id')}")
            print("Отправляем код: 10707297")
            return PlainTextResponse("10707297")
        
        # Новое сообщение
        if data.get("type") == "message_new":
            message = data["object"]["message"]
            text = message.get("text", "").strip()
            user_id = message.get("from_id", 0)
            
            print(f"Сообщение от пользователя: {user_id}")
            print(f"Текст ({len(text)} символов):")
            print("-"*40)
            print(text[:1000])
            if len(text) > 1000:
                print(f"... (еще {len(text)-1000} символов)")
            print("-"*40)
            
            # Сохраняем оригинал для отладки
            debug_filename = f"debug_{user_id}_{datetime.now().strftime('%H%M%S')}.txt"
            with open(debug_filename, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Оригинал сохранен в {debug_filename}")
            
            # ПРОВЕРЯЕМ НАЗВАНИЕ АНКЕТЫ
            if "Анкета" in text or "анкета" in text:
                print("Найдена анкета! Парсим...")
                
                # Парсим данные
                answers = parse_answers_from_text(text)
                
                print(f"Распарсено {len(answers)} полей:")
                for key, value in answers.items():
                    if value:
                        print(f"  {key}: {value[:80]}{'...' if len(value) > 80 else ''}")
                
                # Формируем сообщение
                formatted_message = create_formatted_application(answers, user_id)
                
                print("\nСформированное сообщение:")
                print(formatted_message)
                
                # Отправляем вам
                try:
                    send_result = send_vk_message(
                        peer_id=YOUR_ID,
                        message=formatted_message
                    )
                    if send_result:
                        print("✅ Сообщение отправлено вам")
                    else:
                        print("❌ Ошибка отправки вам")
                except Exception as e:
                    print(f"❌ Ошибка при отправке вам: {str(e)}")
                
                # Ответ пользователю
                try:
                    send_result = send_vk_message(
                        peer_id=user_id,
                        message="✅ Ваша анкета персонажа получена и отправлена на проверку! Спасибо!"
                    )
                    if send_result:
                        print("✅ Пользователю отправлено подтверждение")
                    else:
                        print("❌ Ошибка отправки пользователю")
                except Exception as e:
                    print(f"❌ Ошибка при отправке пользователю: {str(e)}")
            else:
                print("Не анкета, игнорируем")
    
    except Exception as e:
        print(f"❌ Критическая ошибка в callback: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("="*60 + "\n")
    return PlainTextResponse("ok")

def parse_answers_from_text(text: str) -> dict:
    """Парсит анкету из текста сообщения"""
    answers = {}
    
    # Удаляем лишние пробелы и разбиваем на строки
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Маппинг вопросов к полям
    field_mapping = {
        # Вопросы -> Поле
        "имя": "Имя",
        "имя персонажа": "Имя",
        "пол": "Пол",
        "пол персонажа": "Пол",
        "возраст": "Возраст",
        "возраст персонажа": "Возраст",
        "происхождение": "Происхождение",
        "позиция": "Позиция",
        "позиция в племени": "Позиция",
        "телосложение": "Телосложение",
        "рост": "Рост",
        "рост персонажа": "Рост",
        "глаза": "Глаза",
        "цвет глаз": "Глаза",
        "шерсть": "Шерсть",
        "цвет шерсти": "Шерсть",
        "референс": "Ссылка на реф",
        "ссылка": "Ссылка на реф",
        "ссылка на референс": "Ссылка на реф",
        "внешность": "Внешность",
        "характер": "Характер",
        "черты характера": "Характер",
        "характер подробнее": "Характер подробнее",
        "подробнее о характере": "Характер подробнее",
        "цели": "Цели",
        "планы": "Цели",
        "навыки": "Навыки",
        "таланты": "Навыки",
        "история": "История"
    }
    
    # Паттерны для поиска Q/A
    patterns = [
        r'(?:Q[:.]?|Вопрос[:.]?)\s*(.*?)\s*(?:A[:.]?|Ответ[:.]?)\s*(.*?)(?=(?:Q[:.]?|Вопрос[:.]?)|$)',
        r'(.*?)[:]\s*\n?(.*?)(?=\n\s*(?:\w+[:]|Q|Вопрос|$))',
        r'^(.*?)[-]\s*(.*?)$'
    ]
    
    # Сначала пробуем найти Q/A форматы
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if matches:
            print(f"Найдено {len(matches)} пар вопрос-ответ")
            for question, answer in matches:
                question_clean = question.strip().lower()
                answer_clean = answer.strip()
                
                # Ищем подходящее поле
                for question_key, field_name in field_mapping.items():
                    if question_key in question_clean:
                        answers[field_name] = answer_clean
                        break
    
    # Если Q/A не нашли, пробуем парсить по ключевым словам
    if not answers:
        current_field = None
        current_answer = []
        
        for line in lines:
            line_lower = line.lower()
            
            # Проверяем, начинается ли строка с вопроса
            found_field = None
            for question_key, field_name in field_mapping.items():
                if line_lower.startswith(question_key) or f": {question_key}" in line_lower:
                    found_field = field_name
                    break
            
            if found_field:
                # Сохраняем предыдущий ответ
                if current_field and current_answer:
                    answers[current_field] = ' '.join(current_answer).strip()
                
                # Начинаем новый ответ
                current_field = found_field
                current_answer = []
                
                # Пытаемся извлечь ответ из той же строки
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_answer.append(parts[1].strip())
            elif current_field:
                # Продолжаем собирать ответ
                current_answer.append(line)
        
        # Не забываем последний ответ
        if current_field and current_answer:
            answers[current_field] = ' '.join(current_answer).strip()
    
    return answers

def create_formatted_application(answers: dict, user_id: int) -> str:
    """Создаёт анкету в нужном формате"""
    return f"""Новая заявка (от VK ID: {user_id})
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

def send_vk_message(peer_id: int, message: str) -> bool:
    """Отправляет сообщение через VK API"""
    try:
        response = requests.post(
            "https://api.vk.com/method/messages.send",
            data={
                "peer_id": peer_id,
                "message": message,
                "random_id": random.randint(1, 10**9),
                "access_token": TOKEN,
                "v": "5.131"
            },
            timeout=10
        )
        
        result = response.json()
        if "error" in result:
            print(f"VK API ошибка: {result['error']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Ошибка отправки сообщения: {str(e)}")
        return False

@app.get("/callback")
async def check():
    """GET endpoint для проверки"""
    return {"status": "сервер работает", "code": "10707297", "group_id": GROUP_ID}

@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "статус": "VK Bot активен",
        "group_id": GROUP_ID,
        "endpoints": ["/", "/callback", "/form"],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/test")
async def test_endpoint():
    """Тестовый endpoint для проверки"""
    test_text = """Анкета Вашего персонажа для РП сегмента проекта Эхо Севера

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

Q: Навыки, таланты, недостатки
A: Отличный охотник, плохо плавает"""
    
    answers = parse_answers_from_text(test_text)
    formatted = create_formatted_application(answers, 123456)
    
    return {
        "parsed": answers,
        "formatted": formatted,
        "fields_count": len(answers)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


