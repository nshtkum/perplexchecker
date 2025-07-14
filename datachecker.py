import streamlit as st
import requests
import json

# UI Layout
st.set_page_config(page_title="Perplexity Image & Cost Fetcher", layout="wide")
st.title("🏢 Real Estate Info Fetcher using Perplexity API")

# Input fields
api_key = st.text_input("🔑 Enter your Perplexity API Key", type="password")
query = st.text_input("🔍 Enter your property search query", value="Aditya Moonlight Apartment, Mallapur, Hyderabad")

if st.button("Fetch Data"):
    if not api_key or not query:
        st.warning("Please enter both API key and query.")
    else:
        with st.spinner("Querying Perplexity..."):
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            prompt = f"""
Given the property query: "{query}"
1. Find the latest pricing information, configuration (2 BHK, 3 BHK etc), area in sq ft, and total cost in INR.
2. Extract at least 2 image URLs (interior/exterior) from known listing sources like SquareYards, 99acres, Housing, or MagicBricks.
3. Respond in JSON format like:
{{
  "images": ["image_url_1", "image_url_2"],
  "pricing": [
    {{
      "configuration": "2 BHK",
      "area_sqft": "1286",
      "price_inr": "55.3 Lakh"
    }},
    {{
      "configuration": "3 BHK",
      "area_sqft": "1448",
      "price_inr": "62.3 Lakh"
    }}
  ]
}}
"""

            body = {
                "model": "mistral-7b-instruct",
                "messages": [{"role": "user", "content": prompt}]
            }

            try:
                res = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, data=json.dumps(body))
                res.raise_for_status()
                result = res.json()
                reply = result["choices"][0]["message"]["content"]
                data = json.loads(reply)

                # Display Images
                st.subheader("🏙️ Property Images")
                for img_url in data.get("images", []):
                    st.image(img_url, width=300)

                # Display Pricing
                st.subheader("💰 Pricing Information")
                for item in data.get("pricing", []):
                    st.markdown(f"- **{item['configuration']}**: {item['area_sqft']} sq ft → ₹{item['price_inr']}")

            except Exception as e:
                st.error(f"Error fetching or parsing data: {str(e)}")
