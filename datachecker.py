import streamlit as st
import requests
import json
import re
import pandas as pd
from datetime import datetime

# UI Layout
st.set_page_config(page_title="Real Estate Data Fetcher", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
st.markdown("""
<style>
.stTextInput > div > div > input {
    background-color: #f0f2f6;
}
.cost-box {
    background-color: #e1f5fe;
    padding: 10px;
    border-radius: 5px;
    border-left: 4px solid #0288d1;
    margin: 10px 0;
}
.success-box {
    background-color: #e8f5e8;
    padding: 10px;
    border-radius: 5px;
    border-left: 4px solid #4caf50;
}
.image-gallery {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}
.image-item {
    border: 2px solid #ddd;
    border-radius: 8px;
    padding: 5px;
    cursor: pointer;
    transition: transform 0.2s;
}
.image-item:hover {
    transform: scale(1.05);
    border-color: #0288d1;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state for cost tracking
if 'total_cost' not in st.session_state:
    st.session_state.total_cost = 0.0
if 'api_calls' not in st.session_state:
    st.session_state.api_calls = []
if 'selected_image' not in st.session_state:
    st.session_state.selected_image = None

# Sidebar for configuration
with st.sidebar:
    st.header("🔧 Configuration")
    api_key = st.text_input("🔑 Perplexity API Key", type="password", help="Get your API key from https://www.perplexity.ai/")
    
    st.header("💰 Cost Tracking")
    st.markdown(f"""
    <div class="cost-box">
        <strong>Total API Calls:</strong> {len(st.session_state.api_calls)}<br>
        <strong>Estimated Cost:</strong> ${st.session_state.total_cost:.4f}
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🗑️ Reset Cost Tracker"):
        st.session_state.total_cost = 0.0
        st.session_state.api_calls = []
        st.rerun()
    
    # API Pricing Info
    st.subheader("📊 API Pricing")
    pricing_data = {
        "Model": ["sonar-small-online", "sonar-medium-online", "sonar-large-online"],
        "Cost per 1K tokens": ["$0.0002", "$0.0006", "$0.0010"],
        "Best for": ["Quick queries", "Detailed analysis", "Complex research"]
    }
    st.table(pd.DataFrame(pricing_data))

# Main content
st.title("🏢 Real Estate Data Fetcher")
st.markdown("*Comprehensive property information with cost tracking*")

# Query input
query = st.text_input(
    "🔍 Enter your property search query", 
    value="Prestige Lakeside Habitat Bangalore",
    help="Enter property name, location, or RERA number"
)

# Search type selection
search_type = st.radio(
    "📋 Select Search Type:",
    ["📄 Text Data (RERA, Floor Plans, Pricing)", "🖼️ Images Only", "🔍 Combined Search"],
    horizontal=True
)

# Model selection
model_option = st.selectbox(
    "🤖 Select Model:",
    ["llama-3.1-sonar-small-128k-online", "llama-3.1-sonar-large-128k-online"],
    help="Small: Faster & cheaper, Large: More detailed & expensive"
)

def calculate_cost(model, input_tokens, output_tokens):
    """Calculate API cost based on model and token usage"""
    pricing = {
        "llama-3.1-sonar-small-128k-online": {"input": 0.0002, "output": 0.0002},
        "llama-3.1-sonar-large-128k-online": {"input": 0.001, "output": 0.001}
    }
    
    if model in pricing:
        cost = (input_tokens * pricing[model]["input"] / 1000) + (output_tokens * pricing[model]["output"] / 1000)
        return cost
    return 0.001  # Default estimate

def make_api_request(prompt, model, search_type_name):
    """Make API request with error handling and cost tracking"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
        "temperature": 0.2,
        "return_citations": True
    }
    
    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=body,
            timeout=60
        )
        
        if response.status_code == 400:
            error_detail = response.json().get('error', {})
            st.error(f"❌ Bad Request (400): {error_detail.get('message', 'Invalid request format')}")
            st.info("💡 Try simplifying your query or check your API key permissions")
            return None
        elif response.status_code == 401:
            st.error("❌ Invalid API key. Please check your Perplexity API key.")
            return None
        elif response.status_code == 429:
            st.error("❌ Rate limit exceeded. Please try again later.")
            return None
        
        response.raise_for_status()
        result = response.json()
        
        # Calculate cost
        usage = result.get('usage', {})
        input_tokens = usage.get('prompt_tokens', 100)  # Estimate if not provided
        output_tokens = usage.get('completion_tokens', 100)
        cost = calculate_cost(model, input_tokens, output_tokens)
        
        # Track cost
        st.session_state.total_cost += cost
        st.session_state.api_calls.append({
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'type': search_type_name,
            'cost': cost,
            'tokens': input_tokens + output_tokens
        })
        
        return result
        
    except requests.exceptions.Timeout:
        st.error("❌ Request timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"❌ API Error: {str(e)}")
        return None

def search_text_data(query, model):
    """Search for text-based real estate data"""
    prompt = f"""
Search for comprehensive information about this property: "{query}"

Find and provide the following in a structured format:
1. RERA Registration details (number, status, approval date)
2. Builder/Developer information
3. Project specifications (total units, floors, towers)
4. Pricing details for different configurations
5. Possession timeline and construction status
6. Floor plan details and unit sizes
7. Amenities and facilities
8. Location advantages and connectivity
9. Legal clearances and approvals
10. Recent market rates and price trends

Format the response as structured data that can be displayed in tables.
"""
    
    result = make_api_request(prompt, model, "Text Data")
    if result:
        return result["choices"][0]["message"]["content"]
    return None

def search_images(query, model):
    """Search for property images"""
    prompt = f"""
Find high-quality images for this property: "{query}"

Search for and provide direct URLs to:
1. Exterior building views
2. Interior sample flats/units
3. Amenities (gym, pool, clubhouse)
4. Floor plans and layouts
5. Location and surroundings
6. Construction progress (if under development)

Provide only direct image URLs from reliable real estate websites like:
- 99acres.com
- magicbricks.com
- housing.com
- squareyards.com
- builder's official website

Format as a JSON list of image URLs with descriptions:
{{"images": [{{"url": "https://...", "description": "Exterior view"}}, ...]}}
"""
    
    result = make_api_request(prompt, model, "Image Search")
    if result:
        return result["choices"][0]["message"]["content"]
    return None

# Main search functionality
if st.button("🔍 Fetch Data", type="primary", disabled=not api_key or not query):
    if not api_key:
        st.warning("⚠️ Please enter your Perplexity API key in the sidebar.")
    elif not query:
        st.warning("⚠️ Please enter a search query.")
    else:
        # Create tabs for different types of results
        tab1, tab2, tab3 = st.tabs(["📄 Text Data", "🖼️ Images", "💰 Cost Details"])
        
        with tab1:
            if search_type in ["📄 Text Data (RERA, Floor Plans, Pricing)", "🔍 Combined Search"]:
                with st.spinner("🔍 Fetching text data..."):
                    text_data = search_text_data(query, model_option)
                    
                if text_data:
                    st.subheader("📋 Property Information")
                    
                    # Try to parse structured data
                    try:
                        # Split content into sections
                        sections = text_data.split('\n\n')
                        
                        for section in sections:
                            if section.strip():
                                lines = section.strip().split('\n')
                                if len(lines) > 1:
                                    # Create expandable sections
                                    with st.expander(f"📊 {lines[0]}"):
                                        for line in lines[1:]:
                                            if line.strip():
                                                st.write(f"• {line.strip()}")
                                else:
                                    st.write(section)
                    except:
                        # Fallback to raw display
                        st.write(text_data)
                else:
                    st.info("No text data found or API request failed.")
        
        with tab2:
            if search_type in ["🖼️ Images Only", "🔍 Combined Search"]:
                with st.spinner("🖼️ Fetching images..."):
                    image_data = search_images(query, model_option)
                
                if image_data:
                    st.subheader("🖼️ Property Images")
                    
                    # Try to extract JSON
                    try:
                        json_match = re.search(r'\{.*\}', image_data, re.DOTALL)
                        if json_match:
                            image_json = json.loads(json_match.group())
                            images = image_json.get('images', [])
                            
                            if images:
                                st.success(f"✅ Found {len(images)} images")
                                
                                # Create image gallery
                                cols = st.columns(3)
                                for i, img_data in enumerate(images):
                                    with cols[i % 3]:
                                        if isinstance(img_data, dict):
                                            img_url = img_data.get('url', '')
                                            description = img_data.get('description', f'Image {i+1}')
                                        else:
                                            img_url = img_data
                                            description = f'Image {i+1}'
                                        
                                        if img_url and img_url.startswith('http'):
                                            try:
                                                # Create clickable image thumbnail
                                                if st.button(f"🖼️ View {description}", key=f"img_{i}"):
                                                    st.session_state.selected_image = img_url
                                                
                                                # Show thumbnail
                                                st.image(img_url, caption=description, width=200)
                                            except:
                                                st.warning(f"⚠️ Could not load: {description}")
                                
                                # Display selected image in full size
                                if st.session_state.selected_image:
                                    st.subheader("🔍 Full Size View")
                                    st.image(st.session_state.selected_image, use_column_width=True)
                                    if st.button("❌ Close"):
                                        st.session_state.selected_image = None
                                        st.rerun()
                            else:
                                st.info("No image URLs found in the response.")
                        else:
                            st.warning("Could not parse image data as JSON.")
                            st.write("Raw response:", image_data)
                    except Exception as e:
                        st.error(f"Error parsing image data: {str(e)}")
                        st.write("Raw response:", image_data)
                else:
                    st.info("No image data found or API request failed.")
        
        with tab3:
            st.subheader("💰 Cost Breakdown")
            
            if st.session_state.api_calls:
                # Create DataFrame for cost tracking
                df = pd.DataFrame(st.session_state.api_calls)
                
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Calls", len(st.session_state.api_calls))
                with col2:
                    st.metric("Total Cost", f"${st.session_state.total_cost:.4f}")
                with col3:
                    avg_cost = st.session_state.total_cost / len(st.session_state.api_calls)
                    st.metric("Avg Cost/Call", f"${avg_cost:.4f}")
                
                # Detailed breakdown
                st.subheader("📊 Call History")
                st.dataframe(df, use_container_width=True)
                
                # Cost by type chart
                if len(df) > 0:
                    cost_by_type = df.groupby('type')['cost'].sum()
                    st.bar_chart(cost_by_type)
            else:
                st.info("No API calls made yet.")

# Add example queries
with st.expander("💡 Example Queries"):
    examples = [
        "Prestige Lakeside Habitat Bangalore RERA",
        "DLF New Town Heights Sector 90 Gurgaon floor plans",
        "Godrej Emerald Waters Pune pricing 2024",
        "Brigade Golden Triangle Bangalore amenities",
        "Sobha City Gurgaon construction status"
    ]
    
    for example in examples:
        if st.button(f"📋 {example}", key=f"ex_{example}"):
            st.session_state.query = example
            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
**💡 Tips:**
- Use specific property names for better results
- Include location and builder name when possible
- RERA numbers provide the most accurate information
- Image search works best with popular projects
""")
