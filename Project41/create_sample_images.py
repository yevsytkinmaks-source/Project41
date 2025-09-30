#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание примеров изображений для демонстрации функциональности
"""

import os
from PIL import Image, ImageDraw, ImageFont

def create_sample_image(text, filename, size=(400, 300), bg_color=(70, 130, 180), text_color=(255, 255, 255)):
    """Создание примера изображения с текстом"""
    
    # Создаем изображение
    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img)
    
    # Пытаемся использовать системный шрифт
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font = ImageFont.load_default()
    
    # Вычисляем позицию для центрирования текста
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    # Рисуем текст
    draw.text((x, y), text, fill=text_color, font=font)
    
    # Сохраняем изображение
    img.save(filename)
    print(f"✅ Создано изображение: {filename}")

def create_all_sample_images():
    """Создание всех примеров изображений"""
    
    # Создаем директории если их нет
    directories = ["images/rules", "images/solver", "images/textbooks", "images/help"]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    # Создаем изображения
    samples = [
        {
            "text": "🔒 ПРАВИЛА\nRUУчебник\n\nСоблюдайте правила\nиспользования",
            "filename": "images/rules/rules_sample.png",
            "bg_color": (220, 53, 69),  # Красный
            "size": (500, 400)
        },
        {
            "text": "🧮 РЕШАТОР\n\nSoon...\n\nВ разработке",
            "filename": "images/solver/solver_sample.png", 
            "bg_color": (255, 193, 7),  # Желтый
            "size": (500, 400)
        },
        {
            "text": "📚 УЧЕБНИКИ\n\nПоиск и скачивание\nшкольных учебников\n\n1-11 классы",
            "filename": "images/textbooks/textbooks_sample.png",
            "bg_color": (40, 167, 69),  # Зеленый  
            "size": (500, 400)
        },
        {
            "text": "❓ ПОМОЩЬ\n\nАвтор указан:\n• На обложке\n• На титульной странице\n• В каталоге",
            "filename": "images/help/help_author_sample.png",
            "bg_color": (108, 117, 125),  # Серый
            "size": (500, 400)
        }
    ]
    
    for sample in samples:
        if not os.path.exists(sample["filename"]):
            create_sample_image(
                text=sample["text"],
                filename=sample["filename"],
                size=sample["size"],
                bg_color=sample["bg_color"]
            )
        else:
            print(f"⚠️ Изображение уже существует: {sample['filename']}")

if __name__ == "__main__":
    print("🖼️ Создание примеров изображений...")
    create_all_sample_images()
    print("✅ Все примеры изображений созданы!")