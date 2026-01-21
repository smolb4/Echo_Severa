# main.py - ПРОСТАЯ ВЕБ-ФОРМА БЕЗ ЭМОДЗИ
from fastapi import FastAPI, Request, Body  # Заменили Form на Body
from fastapi.responses import HTMLResponse, PlainTextResponse
import requests
import random
import json
import os
import re
from datetime import datetime

app = FastAPI()

# Конфигурация
TOKEN = os.environ.get("VK_TOKEN", "vk1.a.sq5rMHr7_eVlqS9xPvZKC2faTUGZBGT0EeXkSYGIpw1dAe0a6Rrw_hHUSsicD21cRLAUcGd_hzA_BLd0R37aOa7fGCf9vpPkUwRT9uOJlSiMQHCZz397zimUVgVZz9jgV_OOv5vmX6I5aoRAMfCMm0NEgxMd9UgmFgISq_krk2fBhaWC5S6wjvki3apnVH19xScFwNFkOUELvD0DPJQNyA")
CHAT_ID = 2000000001  # ID вашего чата

print(f"Сервер запущен")

# =================== ВЕБ-ФОРМА ===================
@app.get("/", response_class=HTMLResponse)
async def home():
    """Главная страница с формой"""
    # ... (HTML-код формы остаётся БЕЗ ИЗМЕНЕНИЙ, как у вас в примере) ...
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Отправка анкеты в чат</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #333; }
            textarea { 
                width: 100%; 
                height: 400px; 
                padding: 10px; 
                font-size: 14px; 
                border: 2px solid #ddd;
                border-radius: 5px;
                font-family: monospace;
            }
            button { 
                background: #007bff; 
                color: white; 
                border: none; 
                padding: 12px 24px; 
                font-size: 16px; 
                cursor: pointer; 
                margin-top: 10px;
                border-radius: 5px;
            }
            button:hover { background: #0056b3; }
            .result { 
                margin-top: 20px; 
                padding: 15px; 
                border-radius: 5px;
                display: none;
            }
            .success { 
                background: #d4edda; 
                color: #155724; 
                border: 1px solid #c3e6cb;
            }
            .error { 
                background: #f8d7da; 
                color: #721c24; 
                border: 1px solid #f5c6cb;
            }
            .info { 
                background: #d1ecf1; 
                color: #0c5460; 
                border: 1px solid #bee5eb;
                margin-bottom: 20px;
                padding: 15px;
            }
        </style>
    </head>
    <body>
        <h1>Отправка анкеты в чат VK</h1>
        
        <div class="info">
            <strong>Как использовать:</strong><br>
            1. Скопируй анкету из VK (где есть "...Q: Имя персонажа (полное, со знаками ударения), сокращения, клички A: Кличка...")<br>
            2. Вставь в поле ниже<br>
            3. Нажми "Отправить в чат"<br>
            4. Анкета в приятном для нас виде придет в чат "Анкеты | РП | Эхо Севера"
        </div>
        
        <form id="anketaForm">
            <textarea name="anketa_text" placeholder="Вставьте сюда текст анкеты из VK..."></textarea>
            <br>
            <button type="submit">Отправить в чат</button>
        </form>
        
        <div id="result" class="result"></div>
        
        <script>
        // ВАЖНОЕ ИЗМЕНЕНИЕ В ФРОНТЕНДЕ: отправляем JSON, а не FormData
        document.getElementById('anketaForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const form = e.target;
            const textarea = form.querySelector('textarea');
            const button = form.querySelector('button');
            const resultDiv = document.getElementById('result');
            
            const originalText = button.textContent;
            const anketaText = textarea.value.trim();
            
            if (!anketaText) {
                resultDiv.innerHTML = '<div class="error">Введите текст анкеты</div>';
                resultDiv.style.display = 'block';
                return;
            }
            
            button.textContent = 'Отправка...';
            button.disabled = true;
            
            try {
                // Отправляем данные в формате JSON
                const response = await fetch('/send-anketa', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ anketa_text: anketaText })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    resultDiv.innerHTML = `<div class="success">
                        <strong>Успешно отправлено!</strong><br>
                        Имя персонажа: ${result.name}<br>
                    </div>`;
                    
                    // Очищаем поле
                    textarea.value = '';
                } else {
                    resultDiv.innerHTML = `<div class="error">
                        <strong>Ошибка:</strong><br>
                        ${result.error}
                    </div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="error">
                    Ошибка соединения с сервером
                </div>`;
            }
            
            resultDiv.style.display = 'block';
            button.textContent = originalText;
            button.disabled = false;
            
            // Прокручиваем к результату
            resultDiv.scrollIntoView({ behavior: 'smooth' });
        });
        </script>
    </body>
    </html>
    """

# ВАЖНОЕ ИЗМЕНЕНИЕ В БЭКЕНДЕ: получаем данные из JSON-тела
@app.post("/send-anketa")
async def send_anketa(request: Request):  # Убрали Form, заменили на Request
    """Обработка анкеты из формы"""
    try:
        # Получаем тело запроса как JSON
        data = await request.json()
        anketa_text = data.get("anketa_text", "")
    except:
        return {"success": False, "error": "Неверный формат данных"}
    
    print(f"\nПолучена анкета, {len(anketa_text)} символов")
    
    try:
        # Парсим анкету
        parsed = parse_anketa(anketa_text)
        
        if not parsed:
            return {"success": False, "error": "Не удалось распарсить анкету"}
        
        print(f"Распарсено полей: {len(parsed)}")
        
        # Формируем сообщение для чата
        name = parsed.get("Имя", "Не указано")
        gender = parsed.get("Пол", "Не указано")
        age = parsed.get("Возраст", "Не указано")
        position = parsed.get("Позиция", "Не указано")
        
        message = f"""Имя: {parsed.get("Имя", "")}
Пол: {parsed.get("Пол", "")}
Возраст: {parsed.get("Возраст", "")}
Происхождение: {parsed.get("Происхождение", "")}
Позиция: {parsed.get("Позиция", "")}
Телосложение: {parsed.get("Телосложение", "")}
Рост: {parsed.get("Рост", "")}
Глаза: {parsed.get("Глаза", "")}
Шерсть: {parsed.get("Шерсть", "")}
Ссылка на реф: {parsed.get("Ссылка на реф", "")}
Внешность: {parsed.get("Внешность", "")}
Характер: {parsed.get("Характер", "")}
Характер подробнее: {parsed.get("Характер подробнее", "")}
Цели: {parsed.get("Цели", "")}
Навыки: {parsed.get("Навыки", "")}"""
        
        # Отправляем в чат
        if TOKEN:
            result = send_to_chat(message)
            
            if result and "error" not in result:
                return {
                    "success": True,
                    "fields_count": len(parsed),
                    "name": name[:50]
                }
            else:
                return {"success": False, "error": "Ошибка отправки в VK"}
        else:
            return {"success": False, "error": "Токен VK не установлен"}
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return {"success": False, "error": "Внутренняя ошибка сервера"}

# =================== ПАРСИНГ ===================
def parse_anketa(text: str) -> dict:
    """Парсинг анкеты из реального сообщения VK"""
    answers = {}

    # 1. Очищаем текст: оставляем только часть после "Диалог: ..."
    # Это убирает "Новый ответ в опросе", имена и ссылки
    lines = text.split('\n')
    start_parsing = False
    cleaned_lines = []

    for line in lines:
        if line.strip().startswith('Q:'):
            start_parsing = True
        if start_parsing:
            cleaned_lines.append(line)

    cleaned_text = '\n'.join(cleaned_lines)

    # 2. Ищем все Q: A: пары (как и раньше)
    pattern = r'Q:\s*(.*?)\s*A:\s*(.*?)(?=\s*Q:\s*|$)'
    matches = re.findall(pattern, cleaned_text, re.DOTALL)

    # 3. Маппинг вопросов к полям (добавлены сокращённые варианты)
    mapping = {
        "Имя персонажа (полное, со знаками ударения), сокращения, клички": "Имя",
        "Имя персонажа": "Имя",
        "Пол персонажа": "Пол",
        "Возраст персонажа (в формате n лет m месяцев)": "Возраст",
        "Возраст персонажа": "Возраст",
        "Происхождение (для лайоров - горец/горянка, помор/поморка)": "Происхождение",
        "Происхождение": "Происхождение",
        "Позиция в племени": "Позиция",
        "Позиция": "Позиция",
        "Телосложение (кратко)": "Телосложение",
        "Телосложение": "Телосложение",
        "Рост персонажа": "Рост",
        "Рост": "Рост",
        "Цвет глаз (кратко)": "Глаза",
        "Цвет глаз": "Глаза",
        "Цвет шерсти (кратко)": "Шерсть",
        "Цвет шерсти": "Шерсть",
        "Ссылка на референс в альбоме основной группы": "Ссылка на реф",
        "Ссылка на референс": "Ссылка на реф",
        "Референс": "Ссылка на реф",
        "Внешность, отличительные черты и поведение": "Внешность",
        "Внешность": "Внешность",
        "Основные черты характера через запятую": "Характер",
        "Черты характера": "Характер",
        "Характер": "Характер",
        "Подробнее о характере": "Характер подробнее",
        "Цели и планы персонажа на ближайшее будущее": "Цели",
        "Цели": "Цели",
        "Здесь Вы можете написать историю персонажа:": "История",
        "История персонажа": "История",
        "История": "История",
        "Навыки, таланты, недостатки": "Навыки",
        "Навыки": "Навыки"
    }

    for question, answer in matches:
        question = question.strip()
        answer = answer.strip()

        # Ищем точное или частичное совпадение
        for q_template, field in mapping.items():
            if q_template == question:
                answers[field] = answer
                break
            # Если точное не совпало, проверяем, содержится ли шаблон в вопросе
            # (на случай небольших расхождений в формулировке)
            elif q_template in question:
                answers[field] = answer
                break

    return answers

# =================== ОТПРАВКА ===================
def send_to_chat(message: str):
    """Отправка сообщения в чат"""
    if not TOKEN:
        print("Ошибка: токен не установлен")
        return {"error": "Токен не установлен"}
    
    try:
        params = {
            "access_token": TOKEN,
            "peer_id": CHAT_ID,
            "message": message,
            "random_id": random.randint(1, 10**9),
            "v": "5.199"
        }
        
        print(f"Отправка в чат {CHAT_ID}")
        
        response = requests.post(
            "https://api.vk.com/method/messages.send",
            data=params,
            timeout=10
        )
        
        result = response.json()
        print(f"Ответ VK: {result}")
        
        return result
        
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return {"error": str(e)}

# =================== ТЕСТЫ ===================
@app.get("/test")
async def test():
    """Тест отправки"""
    if TOKEN:
        result = send_to_chat(f"Тест бота {datetime.now().strftime('%H:%M:%S')}")
        return {"result": result}
    else:
        return {"error": "токен не установлен"}

@app.get("/check")
async def check():
    """Проверка сервера"""
    return {
        "status": "работает",
        "time": datetime.now().isoformat(),
        "has_token": bool(TOKEN),
        "chat_id": CHAT_ID
    }

# =================== CALLBACK ===================
@app.post("/callback")
async def callback_handler(request: Request):
    """Обработчик для VK"""
    try:
        data = await request.json()
        
        if data.get("type") == "confirmation":
            return PlainTextResponse("744eebe2")
            
    except:
        pass
    
    return PlainTextResponse("ok")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)






