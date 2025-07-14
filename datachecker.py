import streamlit as st
import requests
import json
import re

# UI Layout
st.set_page_config(page_title="Perplexity Image & Cost Fetcher", layout="wide")
st.title("🏢 Real Estate Info Fetcher using Perplexity API")

# Add some styling
st.markdown("""
<style>
.stTextInput > div > div > input {
    background-color: #f0f2f6;
}
</style>
""", unsafe_allow_html=True)

# Input fields
api_key = st.text_input("🔑 Enter your Perplexity API Key", type="password", help="Get your API key from https://www.perplexity.ai/")
query = st.text_input("🔍 Enter your property search query", 
                     value="Aditya Moonlight Apartment, Mallapur, Hyderabad",
                     help="Enter the property name, location, or any specific details")

# Add example queries
with st.expander("💡 Example Queries"):
    st.write("• Prestige Lakeside Habitat, Varthur, Bangalore")
    st.write("• DLF New Town Heights, Sector 90, Gurgaon")
    st.write("• Godrej Properties Emerald Waters, Pune")

if st.button("🔍 Fetch Data", type="primary"):
    if not api_key or not query:
        st.warning("⚠️ Please enter both API key and query.")
    else:
        with st.spinner("Querying Perplexity API..."):
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""
Find information about this property: "{query}"

Please provide:
1. Latest pricing information with configurations (1BHK, 2BHK, 3BHK etc)
2. Area in square feet for each configuration
3. Total cost in Indian Rupees (INR)
4. At least 2 high-quality image URLs from real estate websites
5. Builder/developer name if available
6. Amenities and features

Respond ONLY in this exact JSON format:
{{
  "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
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
  ],
  "builder": "Builder Name",
  "amenities": ["Swimming Pool", "Gym", "Park"]
}}
"""
            
            body = {
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.2
            }
            
            try:
                # Make API request
                response = requests.post(
                    "https://api.perplexity.ai/chat/completions", 
                    headers=headers, 
                    json=body,
                    timeout=30
                )
                
                if response.status_code == 401:
                    st.error("❌ Invalid API key. Please check your Perplexity API key.")
                    st.info("Get your API key from: https://www.perplexity.ai/")
                    st.stop()
                elif response.status_code == 429:
                    st.error("❌ Rate limit exceeded. Please try again later.")
                    st.stop()
                
                response.raise_for_status()
                result = response.json()
                
                # Extract the response content
                reply = result["choices"][0]["message"]["content"]
                st.write("🔍 **Raw API Response:**")
                st.code(reply)
                
                # Try to extract JSON from the response
                json_match = re.search(r'\{.*\}', reply, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    try:
                        data = json.loads(json_str)
                    except json.JSONDecodeError:
                        # If direct parsing fails, try to clean the JSON
                        cleaned_json = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
                        data = json.loads(cleaned_json)
                else:
                    st.error("❌ Could not find valid JSON in the response. Please try again.")
                    st.stop()
                
                # Display results in a nice format
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # Display Images
                    st.subheader("🏙️ Property Images")
                    images = data.get("images", [])
                    if images:
                        for i, img_url in enumerate(images):
                            if img_url and img_url.startswith('http'):
                                try:
                                    st.image(img_url, caption=f"Image {i+1}", width=300, use_column_width=True)
                                except Exception as img_error:
                                    st.warning(f"⚠️ Could not load image {i+1}: {img_url}")
                            else:
                                st.warning(f"⚠️ Invalid image URL: {img_url}")
                    else:
                        st.info("📷 No images found in the response")
                
                with col2:
                    # Display Pricing
                    st.subheader("💰 Pricing Information")
                    pricing = data.get("pricing", [])
                    if pricing:
                        for item in pricing:
                            config = item.get('configuration', 'N/A')
                            area = item.get('area_sqft', 'N/A')
                            price = item.get('price_inr', 'N/A')
                            
                            st.markdown(f"""
                            <div style="background-color: #f0f2f6; padding: 10px; margin: 5px 0; border-radius: 5px;">
                                <strong>🏠 {config}</strong><br>
                                📐 Area: {area} sq ft<br>
                                💵 Price: ₹{price}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("💰 No pricing information found")
                
                # Display additional information
                if data.get("builder"):
                    st.subheader("🏗️ Builder Information")
                    st.info(f"**Builder/Developer:** {data['builder']}")
                
                if data.get("amenities"):
                    st.subheader("🎯 Amenities & Features")
                    amenities = data.get("amenities", [])
                    cols = st.columns(3)
                    for i, amenity in enumerate(amenities):
                        with cols[i % 3]:
                            st.markdown(f"✅ {amenity}")
                            
            except requests.exceptions.Timeout:
                st.error("❌ Request timed out. Please try again.")
            except requests.exceptions.ConnectionError:
                st.error("❌ Connection error. Please check your internet connection.")
            except json.JSONDecodeError as e:
                st.error(f"❌ Could not parse response as JSON: {str(e)}")
                st.write("Raw response:", reply)
            except KeyError as e:
                st.error(f"❌ Unexpected response format: {str(e)}")
                st.write("Full response:", result)
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {str(e)}")
                st.write("Please try again or contact support.")

# Add footer
st.markdown("---")
st.markdown("**Note:** This app uses the Perplexity API to fetch real estate information. Results may vary based on data availability.")
