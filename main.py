# main.py - ПРОСТАЯ ВЕБ-ФОРМА БЕЗ ЭМОДЗИ
from fastapi import FastAPI, Request, Form
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
            1. Скопируйте анкету из VK<br>
            2. Вставьте в поле ниже<br>
            3. Нажмите "Отправить в чат"<br>
            4. Сообщение придет в указанный чат
        </div>
        
        <form id="anketaForm">
            <textarea name="anketa_text" placeholder="Вставьте сюда текст анкеты из VK..."></textarea>
            <br>
            <button type="submit">Отправить в чат</button>
        </form>
        
        <div id="result" class="result"></div>
        
        <script>
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
                const formData = new FormData();
                formData.append('anketa_text', anketaText);
                
                const response = await fetch('/send-anketa', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    resultDiv.innerHTML = `<div class="success">
                        <strong>Успешно отправлено!</strong><br>
                        Распарсено полей: ${result.fields_count}<br>
                        Имя персонажа: ${result.name}<br>
                        Сообщение отправлено в чат
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

@app.post("/send-anketa")
async def send_anketa(anketa_text: str = Form(...)):
    """Обработка анкеты из формы"""
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
        
        # Простое сообщение без эмодзи
        message = f"""НОВАЯ АНКЕТА

Персонаж: {name}
Пол: {gender}
Возраст: {age}
Позиция: {position}

Отправлено через веб-форму
Время: {datetime.now().strftime('%H:%M')}"""
        
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
    """Парсинг анкеты из виджета VK"""
    answers = {}
    
    # Ищем все Q: A: пары
    pattern = r'Q:\s*(.*?)\s*A:\s*(.*?)(?=\s*Q:\s*|$)'
    matches = re.findall(pattern, text, re.DOTALL)
    
    print(f"Найдено Q/A пар: {len(matches)}")
    
    # Маппинг вопросов
    mapping = {
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
        
        # Ищем точное соответствие
        for q_template, field in mapping.items():
            if q_template == question:
                answers[field] = answer
                print(f"  {field}: {answer[:50]}")
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
