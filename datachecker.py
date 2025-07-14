import streamlit as st
import requests
import json
import re
from datetime import datetime

# Page config
st.set_page_config(page_title="Real Estate Data Fetcher", layout="wide")

# Initialize session state
if 'total_cost' not in st.session_state:
    st.session_state.total_cost = 0.0
if 'api_calls' not in st.session_state:
    st.session_state.api_calls = 0

# Title
st.title("🏢 Real Estate Data Fetcher")
st.markdown("*Get property information using Perplexity API*")

# Sidebar
with st.sidebar:
    st.header("🔧 Settings")
    api_key = st.text_input("🔑 API Key", type="password")
    
    st.header("💰 Usage")
    st.write(f"API Calls: {st.session_state.api_calls}")
    st.write(f"Est. Cost: ${st.session_state.total_cost:.4f}")
    
    if st.button("Reset Counter"):
        st.session_state.api_calls = 0
        st.session_state.total_cost = 0.0
        st.rerun()

# Main interface
query = st.text_input("🔍 Property Search", value="Prestige Lakeside Habitat Bangalore")

col1, col2 = st.columns(2)
with col1:
    search_type = st.radio("Search Type:", ["Text Data", "Images", "Both"])
with col2:
    model = st.selectbox("Model:", ["sonar", "sonar-pro"])

def make_api_call(prompt, model_name):
    """Make API request"""
    if not api_key:
        st.error("Please enter API key")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            # Update usage stats
            st.session_state.api_calls += 1
            cost = 0.001 if model_name == "sonar" else 0.005  # Estimated
            st.session_state.total_cost += cost
            return result["choices"][0]["message"]["content"]
        else:
            st.error(f"API Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Request failed: {str(e)}")
        return None

# Search button
if st.button("🔍 Search", type="primary"):
    if not query.strip():
        st.warning("Please enter a search query")
    else:
        # Create tabs
        if search_type == "Both":
            tab1, tab2 = st.tabs(["📄 Text Data", "🖼️ Images"])
        else:
            tab1, tab2 = st.tabs(["📄 Results", "ℹ️ Info"])
        
        with tab1:
            if search_type in ["Text Data", "Both"]:
                st.subheader("📄 Property Information")
                
                prompt = f"""Find key information about this property: {query}
                
Include:
- RERA number and status
- Builder/developer name  
- Price range and configurations
- Key features and amenities
- Location details

Keep response concise and well-formatted."""

                with st.spinner("Getting property data..."):
                    result = make_api_call(prompt, model)
                
                if result:
                    st.write(result)
                else:
                    st.error("Failed to get property data")
            
            elif search_type == "Images":
                st.subheader("🖼️ Property Images")
                
                prompt = f"""Find direct image URLs for property: {query}
                
Please provide only actual image URLs (ending in .jpg, .png, etc.) from real estate websites.
List each URL on a separate line."""

                with st.spinner("Searching for images..."):
                    result = make_api_call(prompt, model)
                
                if result:
                    st.write("**Search Result:**")
                    st.write(result)
                    
                    # Try to extract URLs
                    urls = re.findall(r'https?://[^\s]+\.(?:jpg|jpeg|png|webp)', result, re.IGNORECASE)
                    
                    if urls:
                        st.write(f"**Found {len(urls)} image URLs:**")
                        for i, url in enumerate(urls[:5]):  # Limit to 5 images
                            st.write(f"{i+1}. {url}")
                            try:
                                st.image(url, width=300, caption=f"Image {i+1}")
                            except:
                                st.write("❌ Could not load image")
                    else:
                        st.info("No direct image URLs found in response")
                else:
                    st.error("Failed to get image data")
        
        with tab2:
            if search_type == "Both":
                st.subheader("🖼️ Property Images")
                
                prompt = f"""Find image URLs for property: {query}
                
List direct image URLs from real estate websites."""

                with st.spinner("Searching for images..."):
                    result = make_api_call(prompt, model)
                
                if result:
                    st.write(result)
                    
                    # Extract and display images
                    urls = re.findall(r'https?://[^\s]+\.(?:jpg|jpeg|png|webp)', result, re.IGNORECASE)
                    
                    if urls:
                        for i, url in enumerate(urls[:3]):
                            try:
                                st.image(url, width=300, caption=f"Image {i+1}")
                            except:
                                st.write(f"❌ Could not load: {url}")
                    else:
                        st.info("No image URLs found")
                else:
                    st.error("Failed to get images")
            else:
                st.subheader("ℹ️ Information")
                st.write("**How to use:**")
                st.write("1. Enter your Perplexity API key in the sidebar")
                st.write("2. Type a property name or location")
                st.write("3. Choose search type (Text/Images/Both)")
                st.write("4. Select model (sonar is faster, sonar-pro is more detailed)")
                st.write("5. Click Search")
                
                st.write("**Tips:**")
                st.write("• Use specific property names for better results")
                st.write("• Include city name for better accuracy")
                st.write("• RERA numbers provide most accurate data")

# Manual image test
st.subheader("🧪 Test Image Display")
test_url = st.text_input("Test image URL:", placeholder="https://example.com/image.jpg")
if st.button("Test Image") and test_url:
    try:
        st.image(test_url, width=300, caption="Test Image")
        st.success("✅ Image loaded successfully")
    except Exception as e:
        st.error(f"❌ Failed to load image: {str(e)}")

# Footer
st.markdown("---")
st.markdown("**Note:** Results depend on Perplexity API data availability and your API key permissions.")
