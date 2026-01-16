# main.py - ДИАГНОСТИЧЕСКИЙ КОД
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests
import random
import json
import os

app = FastAPI()

# Конфигурация
TOKEN = os.environ.get("VK_TOKEN", "vk1.a.sq5rMHr7_eVlqS9xPvZKC2faTUGZBGT0EeXkSYGIpw1dAe0a6Rrw_hHUSsicD21cRLAUcGd_hzA_BLd0R37aOa7fGCf9vpPkUwRT9uOJlSiMQHCZz397zimUVgVZz9jgV_OOv5vmX6I5aoRAMfCMm0NEgxMd9UgmFgISq_krk2fBhaWC5S6wjvki3apnVH19xScFwNFkOUELvD0DPJQNyA")
CHAT_PEER_ID = 2000000001  # Ваш чат
CONFIRMATION_CODE = "744eebe2"

print(f"Сервер запущен. Токен: {'ЕСТЬ' if TOKEN else 'НЕТ'}")

@app.post("/callback")
async def vk_callback(request: Request):
    """Простой обработчик для диагностики"""
    print("\n" + "="*50)
    print("VK отправил запрос на /callback")
    
    try:
        # Получаем данные
        data = await request.json()
        print(f"Тип события: {data.get('type')}")
        
        # 1. Подтверждение
        if data.get("type") == "confirmation":
            print(f"Отправляем код: {CONFIRMATION_CODE}")
            return PlainTextResponse(CONFIRMATION_CODE)
        
        # 2. Сообщение
        elif data.get("type") == "message_new":
            message = data["object"]["message"]
            text = message.get("text", "")
            user_id = message.get("from_id", 0)
            
            print(f"Сообщение от: {user_id}")
            print(f"Текст: {text[:200]}...")
            
            # Проверяем анкету (простая проверка)
            if "Q: Имя персонажа" in text:
                print("✓ Это анкета!")
                
                # Отправляем в чат
                success = send_to_chat("Новая анкета получена!")
                
                if success:
                    print("✓ Сообщение отправлено в чат")
                else:
                    print("✗ Не удалось отправить в чат")
            else:
                print("✗ Не анкета")
    
    except Exception as e:
        print(f"Ошибка: {e}")
    
    print("="*50)
    return PlainTextResponse("ok")

def send_to_chat(message: str) -> bool:
    """Простая отправка в чат"""
    if not TOKEN:
        print("✗ Токен не установлен!")
        return False
    
    try:
        params = {
            "access_token": TOKEN,
            "peer_id": CHAT_PEER_ID,
            "message": message,
            "random_id": random.randint(1, 10**9),
            "v": "5.199"
        }
        
        print(f"Отправка в чат {CHAT_PEER_ID}")
        
        response = requests.post(
            "https://api.vk.com/method/messages.send",
            data=params,
            timeout=10
        )
        
        result = response.json()
        print(f"Ответ VK: {result}")
        
        if "error" in result:
            return False
        return True
        
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return False

@app.get("/")
async def root():
    return {"status": "сервер работает"}

@app.get("/test")
async def test():
    """Тест отправки в чат"""
    if TOKEN:
        success = send_to_chat(f"Тест бота {random.randint(1, 100)}")
        return {"status": "отправлено" if success else "ошибка"}
    else:
        return {"error": "токен не установлен"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

