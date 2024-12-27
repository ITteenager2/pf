from database import get_products_by_preferences
import logging
from typing import Dict, Any, List
from openai import AsyncOpenAI
from config import OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def generate_recommendation(user_data: Dict[str, Any], user_message: str = "") -> str:
    logging.info(f"Generating recommendation for user: {user_data}")
    
    if not user_data:
        return "Извините, но для получения рекомендации нужны данные пользователя. Пожалуйста, обновите ваши предпочтения."
    
    gender = user_data.get('gender', '')
    preferences = user_data.get('preferred_fragrances', [])
    
    if not gender or not preferences:
        logging.warning("Insufficient user data for recommendation")
        return "Извините, но для получения рекомендации нужно указать пол и предпочитаемые ароматы. Пожалуйста, обновите ваши предпочтения."
    
    products = get_products_by_preferences(gender, preferences)
    
    if not products:
        logging.warning("No matching products found")
        return await generate_generic_recommendation(gender, preferences)
    
    product_info = "\n".join([f"- {p['name']} ({p['category']}): {p.get('description', 'Нет описания')}" for p in products])
    
    prompt = f"""
    Пользователь:
    Пол: {gender}
    Предпочитаемые ароматы: {', '.join(preferences)}
    
    На основе этой информации и следующих продуктов, предоставьте персонализированную рекомендацию:

    {product_info}

    Опишите, почему эти ароматы подходят пользователю, учитывая его предпочтения и пол. 
    Дайте краткое описание каждого аромата и объясните, почему он может понравиться пользователю.
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Вы - эксперт по парфюмерии, который дает персонализированные рекомендации."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        recommendation = response.choices[0].message.content.strip()
        
        recommendation += "\n\nВы можете приобрести любой из парфюмов у нас на сайте: edp.by"
        
        logging.info("Recommendation generated successfully")
        return recommendation
    except Exception as e:
        logging.error(f"Error generating recommendation: {str(e)}")
        return "Извините, произошла ошибка при генерации рекомендации. Пожалуйста, попробуйте позже."

async def generate_generic_recommendation(gender: str, preferences: List[str]) -> str:
    prompt = f"""
    Пользователь:
    Пол: {gender}
    Предпочитаемые ароматы: {', '.join(preferences)}
    
    Предоставьте общую рекомендацию по выбору парфюма, основываясь на предпочтениях пользователя и его поле.
    Опишите, какие ароматы могут подойти, и почему они могут понравиться пользователю.
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Вы - эксперт по парфюмерии, который дает персонализированные рекомендации."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        recommendation = response.choices[0].message.content.strip()
        
        recommendation += "\n\nВы можете приобрести любой из парфюмов у нас на сайте: edp.by"
        
        logging.info("Generic recommendation generated successfully")
        return recommendation
    except Exception as e:
        logging.error(f"Error generating generic recommendation: {str(e)}")
        return "Извините, произошла ошибка при генерации рекомендации. Пожалуйста, попробуйте позже."

