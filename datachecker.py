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
        "Model": ["sonar", "sonar-pro", "sonar-reasoning"],
        "Input/1K tokens": ["$0.0003", "$0.001", "$0.002"],
        "Output/1K tokens": ["$0.0015", "$0.005", "$0.01"],
        "Best for": ["Quick queries", "Complex search", "Multi-step reasoning"]
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
    ["sonar", "sonar-pro", "sonar-reasoning"],
    help="Sonar: Fast & cost-effective, Sonar Pro: Advanced search, Sonar Reasoning: Complex queries"
)

def calculate_cost(model, input_tokens, output_tokens):
    """Calculate API cost based on model and token usage"""
    pricing = {
        "sonar": {"input": 0.0003, "output": 0.0015},
        "sonar-pro": {"input": 0.001, "output": 0.005},
        "sonar-reasoning": {"input": 0.002, "output": 0.01}
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
        "max_tokens": 1000,  # Reduced for faster response
        "temperature": 0.2
    }
    
    # Add debug info
    st.write(f"🔍 **Debug**: Making API request to model: `{model}`")
    st.write(f"📝 **Prompt length**: {len(prompt)} characters")
    
    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=body,
            timeout=30  # Reduced timeout
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
    prompt = f"""Find key information about this property: "{query}"

Include:
- RERA details and status
- Builder/developer name
- Pricing for different configurations
- Project specifications
- Location and connectivity

Keep response concise and factual."""
    
    result = make_api_request(prompt, model, "Text Data")
    if result:
        return result["choices"][0]["message"]["content"]
    return None

def search_images(query, model):
    """Search for property images"""
    prompt = f"""Find direct image URLs for the property: "{query}"

Please provide ONLY direct image URLs (ending in .jpg, .jpeg, .png, .webp) from real estate websites.

List them as:
URL1: https://example.com/image1.jpg
URL2: https://example.com/image2.jpg
URL3: https://example.com/image3.jpg

Do not include any other text or formatting."""
    
    result = make_api_request(prompt, model, "Image Search")
    if result:
        return result["choices"][0]["message"]["content"]
    return None

# Add a test API button
if api_key:
    if st.sidebar.button("🧪 Test API Key"):
        with st.sidebar:
            with st.spinner("Testing API..."):
                test_result = make_api_request("What is 2+2?", "sonar", "Test")
                if test_result:
                    st.success("✅ API key works!")
                else:
                    st.error("❌ API key test failed")

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
                st.write("🔄 **Starting text data search...**")
                with st.spinner("🔍 Fetching text data..."):
                    text_data = search_text_data(query, model_option)
                    
                if text_data:
                    st.write("✅ **Text data received successfully!**")
                    st.subheader("📋 Property Information")
                    
                    # Display the response in a more readable format
                    st.write(text_data)
                else:
                    st.warning("⚠️ No text data found or API request failed.")
            else:
                st.info("💡 Text data search not selected for this search type.")
        
        with tab2:
            if search_type in ["🖼️ Images Only", "🔍 Combined Search"]:
                st.write("🔄 **Starting image search...**")
                with st.spinner("🖼️ Fetching images..."):
                    image_data = search_images(query, model_option)
                
                if image_data:
                    st.write("✅ **Image data received successfully!**")
                    st.subheader("🖼️ Property Images")
                    
                    # Show raw response for debugging
                    with st.expander("🔍 Debug: Raw Image Response"):
                        st.code(image_data)
                    
                    # Extract URLs using multiple methods
                    image_urls = []
                    
                    # Method 1: Look for direct URLs in the text
                    import re
                    url_pattern = r'https?://[^\s<>"]+\.(?:jpg|jpeg|png|webp|gif)'
                    found_urls = re.findall(url_pattern, image_data, re.IGNORECASE)
                    image_urls.extend(found_urls)
                    
                    # Method 2: Look for URLs after "URL:" or similar patterns
                    lines = image_data.split('\n')
                    for line in lines:
                        if 'http' in line.lower():
                            # Extract URL from line
                            url_match = re.search(r'https?://[^\s<>"]+', line)
                            if url_match:
                                url = url_match.group()
                                if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                                    image_urls.append(url)
                    
                    # Remove duplicates
                    image_urls = list(set(image_urls))
                    
                    # Fallback: If no images found, try a different approach
                    if not image_urls:
                        st.info("🔄 Trying alternative image search...")
                        
                        # Try a simpler prompt
                        simple_prompt = f"Show me photos of {query} property building exterior interior"
                        simple_result = make_api_request(simple_prompt, model_option, "Simple Image Search")
                        
                        if simple_result:
                            simple_data = simple_result["choices"][0]["message"]["content"]
                            st.write("**Alternative search result:**")
                            st.write(simple_data)
                            
                            # Try to extract URLs again
                            simple_urls = re.findall(url_pattern, simple_data, re.IGNORECASE)
                            if simple_urls:
                                st.success(f"✅ Found {len(simple_urls)} additional URLs!")
                                image_urls.extend(simple_urls)
                                image_urls = list(set(image_urls))  # Remove duplicates again
                    
                    if image_urls:
                        # Create image gallery
                        cols = st.columns(min(3, len(image_urls)))
                        
                        for i, img_url in enumerate(image_urls[:6]):  # Limit to 6 images
                            with cols[i % 3]:
                                st.write(f"**Image {i+1}:**")
                                
                                # Show clickable button
                                if st.button(f"🖼️ View Image {i+1}", key=f"img_btn_{i}"):
                                    st.session_state.selected_image = img_url
                                
                                # Try to display thumbnail
                                try:
                                    st.image(img_url, caption=f"Image {i+1}", width=200)
                                    st.success(f"✅ Image {i+1} loaded")
                                except Exception as e:
                                    st.error(f"❌ Failed to load Image {i+1}")
                                    st.code(img_url)
                                    st.write(f"Error: {str(e)}")
                        
                        # Display selected image in full size
                        if st.session_state.selected_image:
                            st.subheader("🔍 Full Size View")
                            try:
                                st.image(st.session_state.selected_image, use_column_width=True)
                                st.code(st.session_state.selected_image)
                            except Exception as e:
                                st.error(f"Error displaying full size image: {str(e)}")
                            
                            if st.button("❌ Close Full View"):
                                st.session_state.selected_image = None
                                st.rerun()
                    # Test images section
                    st.subheader("🧪 Test Image Display")
                    test_images = [
                        "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400",
                        "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=400",
                        "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=400"
                    ]
                    
                    if st.button("🧪 Test with Sample Images"):
                        st.write("Testing image display with known working URLs...")
                        for i, test_url in enumerate(test_images):
                            try:
                                st.image(test_url, caption=f"Test Image {i+1}", width=200)
                                st.success(f"✅ Test image {i+1} loaded successfully")
                            except Exception as e:
                                st.error(f"❌ Test image {i+1} failed: {str(e)}")
                    
                    if not image_urls:
                        st.warning("⚠️ No valid image URLs found in the response.")
                        st.info("💡 Try searching for a more popular property or use a different model.")
                        st.info("💡 You can also manually add image URLs using the input above.")
                else:
                    st.warning("⚠️ No image data found or API request failed.")
            else:
                st.info("💡 Image search not selected for this search type.")
            else:
                st.info("💡 Image search not selected for this search type.")
        
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
