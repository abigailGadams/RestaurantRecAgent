import streamlit as st
import openai
import requests
import urllib.parse
import os
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Get API keys from .env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
YELP_API_KEY = os.getenv("YELP_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Validate keys
if not all([OPENAI_API_KEY, YELP_API_KEY, GOOGLE_API_KEY]):
    raise EnvironmentError("❌ One or more API keys are missing from your .env file.")

# Set OpenAI key
openai.api_key = OPENAI_API_KEY





#openai.api_key = OPENAI_API_KEY

def search_yelp(location, preferences, limit=5):
    headers = {
        "Authorization": f"Bearer {YELP_API_KEY}"
    }
    params = {
        "location": location,
        "term": "fine dining",
        "categories": "restaurants",
        "sort_by": "rating",
        "limit": limit
    }
    response = requests.get("https://api.yelp.com/v3/businesses/search", headers=headers, params=params)
    response.raise_for_status()
    return response.json()["businesses"]

def search_google_place(business_name, address):
    query = f"{business_name}, {address}"
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        return {}
    
    place = results[0]
    return {
        "google_name": place.get("name"),
        "google_rating": place.get("rating"),
        "user_ratings_total": place.get("user_ratings_total"),
        "photo_ref": place["photos"][0]["photo_reference"] if "photos" in place else None,
        "maps_url": f"https://www.google.com/maps/place/?q=place_id:{place['place_id']}"
    }

def get_google_photo_url(photo_ref, maxwidth=400):
    return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth={maxwidth}&photoreference={photo_ref}&key={GOOGLE_API_KEY}"


def format_yelp_results_with_google(businesses):
    formatted = []
    for biz in businesses:
        yelp_name = biz["name"]
        address = ", ".join(biz["location"]["display_address"])

        google_data = search_google_place(yelp_name, address)
        item = {
            "name": yelp_name,
            "address": address,
            "yelp_rating": biz["rating"],
            "google_rating": google_data.get("google_rating", "N/A"),
            "total_reviews": google_data.get("user_ratings_total", "N/A"),
            "price": biz.get("price", "N/A"),
            "phone": biz["display_phone"],
            "yelp_url": biz["url"],
            "maps_url": google_data.get("maps_url", ""),
            "categories": ", ".join([cat["title"] for cat in biz["categories"]])
        }
        formatted.append(item)
    return formatted


def refine_with_gpt(location, preferences, raw_data):
    prompt = f"""
You are a luxury travel concierge. Based on the location "{location}" and the client preferences "{preferences}", review the following restaurant options and return a refined list of 3–5 upscale restaurant recommendations. For each, include:

- Name  
- One-sentence description  
- Cuisine type  
- Price level  
- Booking link (if available)  

Raw Yelp Data:
{raw_data}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a luxury restaurant recommender for high-end travel clients."},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content']

def main():
    print("🍽️ Luxury Restaurant Recommender 🍷")
    location = input("Enter the client's destination (e.g., St. Tropez, Tokyo): ")
    preferences = input("Enter client preferences (e.g., romantic, ocean view, seafood, vegan): ")

    print("\n🔍 Searching Yelp for top restaurants...")
    yelp_results = search_yelp(location, preferences)
    

    print("\n🧠 Refining results with GPT...\n")
    refined_output = refine_with_gpt(location, preferences, formatted_data)
    print(refined_output)

if __name__ == "__main__":
    main()


# Streamlit App
st.title("🍽️ Luxury Restaurant Recommender")
st.markdown("Get high-end restaurant picks based on your travel destination and preferences.")

location = st.text_input("Enter destination", placeholder="e.g., St. Tropez")
preferences = st.text_input("Client preferences", placeholder="e.g., romantic, seafood, ocean view")

if st.button("Get Recommendations"):
    if not location:
        st.warning("Please enter a destination.")
    else:
        with st.spinner("Searching and refining..."):
            yelp_results = search_yelp(location, preferences)
            formatted_data = format_yelp_results_with_google(yelp_results)
            gpt_output = refine_with_gpt(location, preferences, formatted_data)
        st.success("Refined recommendations:")
        st.markdown(gpt_output)