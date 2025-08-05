import os
import re

# Простая транслитерация кириллицы в латиницу
TRANSLIT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
    'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '',
    'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
}

def transliterate(name):
    """Транслитерация кириллических символов в латиницу."""
    result = ''
    for char in name:
        result += TRANSLIT_MAP.get(char, char)
    return result

def is_image_file(filename):
    """Проверяет, является ли файл изображением (jpg/jpeg)."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ['.jpg', '.jpeg']

def rename_photos_in_folders(root_dir):
    """Переименовывает все jpg-файлы в подпапках по шаблону: ИмяПапки_1.jpg и т.д."""
    for folder_name in os.listdir(root_dir):
        folder_path = os.path.join(root_dir, folder_name)
        
        if not os.path.isdir(folder_path):
            continue

        # Транслитерируем название папки
        safe_folder_name = transliterate(folder_name)
        # Убираем недопустимые символы из имён файлов
        safe_folder_name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', safe_folder_name)

        # Получаем список jpg-файлов
        files = [f for f in os.listdir(folder_path) if is_image_file(f)]
        files.sort()  # Чтобы порядок был одинаковым

        for idx, filename in enumerate(files, start=1):
            old_path = os.path.join(folder_path, filename)
            new_filename = f"{safe_folder_name}_{idx}.jpg"
            new_path = os.path.join(folder_path, new_filename)

            # Проверяем, не совпадает ли новое имя с текущим
            if old_path == new_path:
                print(f"Пропущено (уже правильно): {new_filename}")
                continue

            # Проверяем, существует ли уже файл с таким именем
            if os.path.exists(new_path):
                print(f"Внимание: файл уже существует, пропущено: {new_path}")
                continue

            os.rename(old_path, new_path)
            print(f"Переименовано: {filename} → {new_filename}")

# === ЗАПУСК СКРИПТА ===
if __name__ == "__main__":
    # Укажите путь к папке, содержащей подпапки с фото
    ROOT_DIRECTORY = input("Введите путь к основной папке: ").strip()
    
    if not os.path.isdir(ROOT_DIRECTORY):
        print("Ошибка: Указанный путь не является папкой.")
    else:
        rename_photos_in_folders(ROOT_DIRECTORY)
        print("Готово!")