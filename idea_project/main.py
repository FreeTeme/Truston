import requests
import json
from typing import Dict, Optional, Any

def fetch_car_price_statistics(
    available_year: int,
    brand: int,
    drive_type: int,
    engine_capacity: int,
    engine_type: int,
    generation: int,
    model: int,
    transmission_type: int,
    year: int,
    base_url: str = "https://api.av.by/offer-types/cars/price-statistics"
) -> Optional[Dict[str, Any]]:

    
    # Формируем параметры запроса
    params = {
        "available_year": available_year,
        "brand": brand,
        "drive_type": drive_type,
        "engine_capacity": engine_capacity,
        "engine_type": engine_type,
        "generation": generation,
        "model": model,
        "transmission_type": transmission_type,
        "year": year
    }
    
    try:
        headers = {
            'accept': '*/*',
            'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
            'content-type': 'application/json',
            'origin': 'https://av.by',
            'priority': 'u=1, i',
            'referer': 'https://av.by/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1',
            'x-device-type': 'web.mobile',
        }

        # Выполняем GET-запрос
        response = requests.get(base_url,headers=headers, params=params, timeout=10)
        
        # Проверяем успешность запроса
        response.raise_for_status()
        
        # Парсим JSON-ответ
        data = response.json()
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Ошибка при парсинге JSON: {e}")
        return None


# Пример использования функции
def example_usage():
    """
    Пример использования функции для получения статистики по Peugeot 308 2011 года
    с параметрами из предоставленного примера
    """
    
    # Параметры из примера URL
    statistics_data = fetch_car_price_statistics(
        available_year=2021,
        brand=8,           # Peugeot
        drive_type=4,        # передний привод
        engine_capacity=4400,
        engine_type=1,       # бензин
        generation=11815,     # T7 · Рестайлинг
        model=81,          # 308
        transmission_type=1, # механика
        year=2021
    )
    
    if statistics_data:
        # Сохраняем результат в файл для дальнейшего анализа
        with open("price_statistics_output.json", "w", encoding="utf-8") as f:
            json.dump(statistics_data, f, ensure_ascii=False, indent=2)
        
        # Выводим основную информацию
        print("Статистика цен успешно получена!")
        print(f"Сохранено в файл: price_statistics_output.json")
        
        # Пример извлечения ключевой информации
        if "mediumPrice" in statistics_data:
            medium_price = statistics_data["mediumPrice"]
            print(f"\nСредняя цена: ${medium_price.get('priceUsd', 0):.2f}")
            print(f"Количество объявлений: {medium_price.get('advertCount', 0)}")
            print(f"Диапазон цен: ${medium_price.get('minPriceUsd', 0)} - ${medium_price.get('maxPriceUsd', 0)}")
        
        return statistics_data
    else:
        print("Не удалось получить данные статистики")
        return None


# Дополнительная функция для удобного использования
def get_car_stats_by_params(car_params: Dict[str, int]) -> Optional[Dict[str, Any]]:
    """
    Упрощенная функция для получения статистики с использованием словаря параметров
    
    Параметры:
    -----------
    car_params : Dict[str, int]
        Словарь с параметрами автомобиля
    
    Возвращает:
    -----------
    Dict[str, Any] или None
        Словарь с данными статистики
    """
    
    # Обязательные параметры
    required_params = [
        "available_year", "brand", "drive_type", "engine_capacity",
        "engine_type", "generation", "model", "transmission_type", "year"
    ]
    
    # Проверяем наличие всех необходимых параметров
    for param in required_params:
        if param not in car_params:
            print(f"Отсутствует обязательный параметр: {param}")
            return None
    
    return fetch_car_price_statistics(**car_params)


if __name__ == "__main__":
    # Пример использования
    example_usage()
    
    # Альтернативный способ использования
    print("\n--- Альтернативный способ использования ---")
    
    car_params = {
        "available_year": 2011,
        "brand": 989,
        "drive_type": 1,
        "engine_capacity": 1600,
        "engine_type": 1,
        "generation": 2027,
        "model": 1927,
        "transmission_type": 2,
        "year": 2011
    }
    
    stats = get_car_stats_by_params(car_params)
    if stats:
        print("Данные успешно получены через упрощенную функцию")