# main.py
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests
import random
import json
import os
import re

app = FastAPI()

# Конфигурация
TOKEN = os.environ.get("VK_TOKEN", "vk1.a.sq5rMHr7_eVlqS9xPvZKC2faTUGZBGT0EeXkSYGIpw1dAe0a6Rrw_hHUSsicD21cRLAUcGd_hzA_BLd0R37aOa7fGCf9vpPkUwRT9uOJlSiMQHCZz397zimUVgVZz9jgV_OOv5vmX6I5aoRAMfCMm0NEgxMd9UgmFgISq_krk2fBhaWC5S6wjvki3apnVH19xScFwNFkOUELvD0DPJQNyA")
CHAT_PEER_ID = 2000000001  # Ваш чат
CONFIRMATION_CODE = "744eebe2"
GROUP_ID = 235128907

print(f"Сервер запущен. Токен: {'ЕСТЬ' if TOKEN else 'НЕТ'}")

@app.post("/callback")
async def vk_callback(request: Request):
    """Обработчик ВСЕХ сообщений из группы"""
    print("\n" + "="*50)
    print("Запрос от VK")
    
    try:
        data = await request.json()
        print(f"Тип: {data.get('type')}")
        
        # Подтверждение
        if data.get("type") == "confirmation":
            print(f"Код: {CONFIRMATION_CODE}")
            return PlainTextResponse(CONFIRMATION_CODE)
        
        # Новое сообщение
        elif data.get("type") == "message_new":
            message = data["object"]["message"]
            text = message.get("text", "")
            user_id = message.get("from_id", 0)
            
            print(f"От: {user_id}")
            print(f"Текст: {text[:300]}...")
            
            # ПРОВЕРЯЕМ ЛЮБЫЕ СООБЩЕНИЯ С АНКЕТОЙ
            # Ищем признаки анкеты
            if any(keyword in text for keyword in ["Q: Имя персонажа", "Анкета Вашего персонажа", "Новый ответ в опросе"]):
                print("✓ Найдена анкета!")
                
                # Парсим анкету
                parsed = parse_simple_anketa(text)
                
                if parsed:
                    print(f"Распарсено полей: {len(parsed)}")
                    
                    # Формируем сообщение для чата
                    name = parsed.get("Имя", "Не указано")
                    gender = parsed.get("Пол", "Не указано")
                    age = parsed.get("Возраст", "Не указано")
                    
                    msg = f"Новая анкета!\n\nПерсонаж: {name}\nПол: {gender}\nВозраст: {age}"
                    
                    # Отправляем в чат
                    success = send_to_chat(msg)
                    
                    if success:
                        print("✓ Отправлено в чат")
                    else:
                        print("✗ Ошибка отправки")
                else:
                    print("✗ Не удалось распарсить")
                    
                    # Всё равно отправляем уведомление
                    send_to_chat("Получена новая анкета (ошибка парсинга)")
            else:
                print("✗ Не анкета (пропускаем)")
    
    except Exception as e:
        print(f"Ошибка: {e}")
    
    print("="*50)
    return PlainTextResponse("ok")

def parse_simple_anketa(text: str) -> dict:
    """Простой парсинг анкеты"""
    answers = {}
    
    # Ищем все Q: A:
    lines = text.split('\n')
    
    current_question = ""
    current_answer = []
    in_answer = False
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("Q:"):
            # Сохраняем предыдущий
            if current_question and current_answer:
                answers[current_question] = " ".join(current_answer)
            
            # Новый вопрос
            current_question = line[2:].strip()
            current_answer = []
            in_answer = False
            
        elif line.startswith("A:"):
            current_answer.append(line[2:].strip())
            in_answer = True
            
        elif in_answer and line:
            current_answer.append(line)
    
    # Последний вопрос
    if current_question and current_answer:
        answers[current_question] = " ".join(current_answer)
    
    # Преобразуем вопросы в стандартные поля
    result = {}
    
    for question, answer in answers.items():
        q_lower = question.lower()
        
        if "имя" in q_lower:
            result["Имя"] = answer
        elif "пол" in q_lower:
            result["Пол"] = answer
        elif "возраст" in q_lower:
            result["Возраст"] = answer
        elif "происхождение" in q_lower:
            result["Происхождение"] = answer
        elif "позиция" in q_lower:
            result["Позиция"] = answer
        elif "телосложение" in q_lower:
            result["Телосложение"] = answer
        elif "рост" in q_lower:
            result["Рост"] = answer
        elif "глаз" in q_lower:
            result["Глаза"] = answer
        elif "шерсть" in q_lower:
            result["Шерсть"] = answer
    
    return result

def send_to_chat(message: str) -> bool:
    """Отправка в чат"""
    if not TOKEN:
        print("✗ Нет токена")
        return False
    
    try:
        params = {
            "access_token": TOKEN,
            "peer_id": CHAT_PEER_ID,
            "message": message,
            "random_id": random.randint(1, 10**9),
            "v": "5.199"
        }
        
        response = requests.post(
            "https://api.vk.com/method/messages.send",
            data=params,
            timeout=10
        )
        
        result = response.json()
        
        if "error" in result:
            print(f"Ошибка VK: {result['error']}")
            return False
        return True
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

@app.get("/")
async def root():
    return {"status": "сервер работает"}

@app.get("/test")
async def test():
    """Тест отправки"""
    if TOKEN:
        success = send_to_chat("Тест бота - работает!")
        return {"status": "отправлено" if success else "ошибка"}
    else:
        return {"error": "нет токена"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
