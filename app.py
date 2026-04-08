import streamlit as st

# MUST BE THE FIRST COMMAND
st.set_page_config(page_title="AI-First Career Bridge", page_icon="🚀", layout="wide")

import streamlit.components.v1 as components
from fpdf import FPDF
import subprocess
import tempfile
import os
import random 
import requests 
from bs4 import BeautifulSoup 
import base64 

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- YOUR HARDCODED API KEYS ---
DEFAULT_GITHUB_TOKEN = "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"
DEFAULT_SCRAPETABLE_KEY = "scr_594eb8ab02b5a7f529078d53d323"

# --- 1. THE STABLE CLI BRIDGE (GEMINI V3 FLASH) ---
def ask_gemini_cli(prompt):
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write(prompt)
            temp_file_path = f.name
        
        # Uses the Gemini 3 Flash model for maximum speed
        command = f'gemini --model gemini-3-flash-preview < "{temp_file_path}"'
        
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True,
            encoding='utf-8',
            shell=True,
            timeout=240 
        )
        
        os.remove(temp_file_path)
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error from CLI: {result.stderr}"
    except subprocess.TimeoutExpired:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return "TIMEOUT_ERROR" 
    except Exception as e:
        return f"Python couldn't run the command: {e}"

def extract_pdf_text(uploaded_file):
    if not PDF_AVAILABLE:
        return "Error: PyPDF2 not installed."
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

# --- GITHUB LIVE DATA FETCHER ---
def fetch_github_data(username, token=""):
    if not username or username.lower() == "none":
        return "", ""
    
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    
    try:
        user_url = f"https://api.github.com/users/{username}"
        user_response = requests.get(user_url, headers=headers)
        
        if user_response.status_code in [403, 429]:
            return "ERROR: RATE_LIMIT", ""
        elif user_response.status_code == 404:
            return "ERROR: NOT_FOUND", ""
            
        user_data = user_response.json()
        avatar_url = user_data.get("avatar_url", "")
        bio = user_data.get("bio", "Software Developer")
        name = user_data.get("name", username)
        
        repos_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=5"
        repos_response = requests.get(repos_url, headers=headers)
        
        repo_text = f"GitHub Name: {name}\nGitHub Bio: {bio}\n\nTop Projects from GitHub:\n"
        
        if repos_response.status_code == 200:
            repos_data = repos_response.json()
            if isinstance(repos_data, list) and len(repos_data) > 0:
                for repo in repos_data:
                    repo_name = repo.get("name", "")
                    repo_desc = repo.get("description", "No description provided.")
                    repo_lang = repo.get("language", "Multiple")
                    repo_text += f"- Project Name: {repo_name} | Language: {repo_lang} | Description: {repo_desc}\n"
            else:
                repo_text += "- No public repositories found.\n"
                
        return repo_text, avatar_url
    except Exception as e:
        return f"ERROR: {e}", ""

# --- SCRAPETABLE LINKEDIN FETCHER ---
def fetch_linkedin_scrapetable(linkedin_url, token=""):
    if not linkedin_url or linkedin_url.lower() == "none":
        return ""
    if not token:
        return "NO_TOKEN"

    api_endpoint = 'https://api.scrapetable.com/scrape'
    params = {
        'api_key': token,
        'url': linkedin_url
    }

    try:
        response = requests.get(api_endpoint, params=params, timeout=30)
        
        if response.status_code == 200:
            try:
                data = response.json()
                return str(data)[:3000] 
            except:
                soup = BeautifulSoup(response.text, 'html.parser')
                clean_text = ' '.join(soup.stripped_strings)
                return f"LinkedIn Raw Profile Data: {clean_text[:3500]}"
                
        elif response.status_code in [401, 403]:
            return "ERROR: INVALID_TOKEN"
        elif response.status_code == 429:
            return "ERROR: RATE_LIMIT"
        else:
            return f"ERROR: Status {response.status_code}"
    except Exception as e:
        return f"ERROR: {e}"


# --- 2. ATS PDF GENERATOR ---
class PDF(FPDF):
    def __init__(self, theme="Standard Tech (Helvetica, Light Grey Line)"):
        super().__init__()
        self.theme = theme

    def add_section(self, title, body):
        self.ln(3)
        
        clean_body = body.replace("•", "-").replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-").replace("…", "...")
        clean_body = clean_body.encode('latin-1', 'replace').decode('latin-1')

        font_family = "Helvetica"
        if "Times" in self.theme or "Finance" in self.theme or "Academic" in self.theme: font_family = "Times"
        elif "Courier" in self.theme or "Cybersecurity" in self.theme: font_family = "Courier"

        if self.theme == "Standard Tech (Helvetica, Light Grey Line)":
            self.set_line_width(0.3)
            self.set_draw_color(180, 180, 180) 
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(4)
            y_start = self.get_y()
            self.set_font("Helvetica", 'B', 10)
            self.set_text_color(40, 40, 40) 
            self.cell(45, 5, txt=title.upper(), ln=False)
            self.set_xy(55, y_start)
            self.set_font("Helvetica", '', 10)
            self.set_text_color(0, 0, 0) 
            self.multi_cell(0, 5, txt=clean_body)

        else:
            title_color = (0, 0, 0)
            line_color = None
            line_width = 0.3
            align = 'L'
            fill = False

            if self.theme == "Harvard Classic (Times, Black Line)":
                line_color = (0, 0, 0)
            elif self.theme == "Modern Executive (Helvetica, Navy Blue)":
                title_color = (30, 80, 140)
            elif self.theme == "Creative Professional (Helvetica, Teal Line)":
                title_color = (0, 128, 128)
                line_color = (0, 128, 128)
            elif self.theme == "Minimalist Startup (Helvetica, No Lines)":
                pass 
            elif self.theme == "Finance Strict (Times, Thick Black Line)":
                line_color = (0, 0, 0)
                line_width = 0.7 
            elif self.theme == "Engineering Pro (Helvetica, Grey Highlight)":
                self.set_fill_color(230, 230, 230)
                fill = True
            elif self.theme == "Product Manager (Helvetica, Centered)":
                align = 'C'
            elif self.theme == "Cybersecurity (Courier, Dark Green)":
                title_color = (0, 100, 0)
                line_color = (0, 100, 0)
            elif self.theme == "Elegant Academic (Times, Maroon Line)":
                title_color = (128, 0, 0)
                line_color = (128, 0, 0)

            self.set_font(font_family, 'B', 12)
            self.set_text_color(*title_color)
            self.cell(0, 6, txt=title.upper(), ln=True, align=align, fill=fill)

            if line_color:
                self.set_line_width(line_width)
                self.set_draw_color(*line_color)
                self.line(10, self.get_y(), 200, self.get_y())
                self.ln(2)
            elif not fill:
                self.ln(1)
            else:
                self.ln(2)

            self.set_font(font_family, '', 10)
            self.set_text_color(0, 0, 0)
            self.multi_cell(0, 5, txt=clean_body)
            
        self.ln(2)

def generate_ats_resume(name, contact, profile, education, experience, skills, template="Standard Tech (Helvetica, Light Grey Line)"):
    pdf = PDF(theme=template)
    pdf.add_page()
    
    font_family = "Helvetica"
    name_color = (0, 0, 0)

    if "Times" in template or "Finance" in template or "Academic" in template: font_family = "Times"
    elif "Courier" in template or "Cybersecurity" in template: font_family = "Courier"

    if "Modern Executive" in template: name_color = (30, 80, 140)
    elif "Creative" in template: name_color = (0, 128, 128)
    elif "Cybersecurity" in template: name_color = (0, 100, 0)
    elif "Academic" in template: name_color = (128, 0, 0)

    pdf.set_font(font_family, 'B', 24)
    pdf.set_text_color(*name_color)
    clean_name = name.encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, txt=clean_name, ln=True, align='C')
    
    pdf.set_font(font_family, '', 11)
    pdf.set_text_color(100, 100, 100) 
    clean_contact = contact.encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 5, txt=clean_contact, ln=True, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)
    
    if profile: pdf.add_section("Profile", profile)
    if education: pdf.add_section("Education", education)
    if experience: pdf.add_section("Experience", experience)
    if skills: pdf.add_section("Skills", skills)
    
    pdf_filename = "ATS_Resume_Pro.pdf"
    pdf.output(pdf_filename)
    return pdf_filename

# --- 3. UI MEMORY SETUP ---
if "generated_roles" not in st.session_state: st.session_state.generated_roles = []
if "roadmap" not in st.session_state: st.session_state.roadmap = ""
if "project_ideas" not in st.session_state: st.session_state.project_ideas = []
if "project_guide" not in st.session_state: st.session_state.project_guide = ""

if "res_name" not in st.session_state: st.session_state.res_name = ""
if "res_contact" not in st.session_state: st.session_state.res_contact = ""
if "res_profile" not in st.session_state: st.session_state.res_profile = ""
if "res_edu" not in st.session_state: st.session_state.res_edu = ""
if "res_exp" not in st.session_state: st.session_state.res_exp = ""
if "res_skills" not in st.session_state: st.session_state.res_skills = ""

if "ai_success" not in st.session_state: st.session_state.ai_success = False
if "portfolio_html" not in st.session_state: st.session_state.portfolio_html = "" 
if "pdf_filename" not in st.session_state: st.session_state.pdf_filename = None
if "pdf_display" not in st.session_state: st.session_state.pdf_display = None
if "selected_template" not in st.session_state: st.session_state.selected_template = "Standard Tech (Helvetica, Light Grey Line)"

# --- 4. GLOBAL CSS STYLING ---
st.markdown("""
    <style>
    div.stButton > button { border-radius: 8px; font-weight: bold; transition: 0.3s; }
    div.stButton > button:hover { transform: scale(1.02); }
    .big-title { text-align: center; font-size: 3rem !important; font-weight: 800; background: -webkit-linear-gradient(45deg, #FF4B2B, #FF416C); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0px; }
    .sub-title { text-align: center; font-size: 1.2rem; color: #666; margin-bottom: 40px; }
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a { display: none !important; }
    a.header-anchor { display: none !important; }
    h1 svg, h2 svg, h3 svg, h4 svg, h5 svg, h6 svg { display: none !important; }
    
    .tpl-page-large {
        width: 100%;
        height: 250px; 
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 16px; 
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        gap: 12px; 
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    .m-line-lg { height: 6px; background: #CBD5E1; border-radius: 3px; width: 100%; } 
    .m-head-lg { height: 10px; background: #475569; border-radius: 3px; width: 50%; } 
    </style>
""", unsafe_allow_html=True)


# ==========================================
# PAGE FUNCTIONS
# ==========================================

def render_home():
    st.markdown("<h1 class='big-title'>AI-First Career Bridge</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-title'>Your personal AI architect for professional identity and career planning.</p>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("### 📝 AI Resume Builder\n\nCraft a mathematically precise, 100% ATS-compliant PDF resume in seconds using live data.")
        if st.button("Launch Resume Builder ➔", use_container_width=True, type="primary"):
            st.switch_page(page_resume)
    with col2:
        st.success("### 🌐 Pro Website Builder\n\nUpload your profile details and let the AI code a stunning, editable portfolio website.")
        if st.button("Launch Website Builder ➔", use_container_width=True, type="primary"):
            st.switch_page(page_website)
            
    st.write("")
    col3, col4 = st.columns(2)
    with col3:
        st.warning("### 🧠 Smart Career Mapper\n\nExplore roles and generate learning guides for any technical field.")
        if st.button("Launch Career Mapper ➔", use_container_width=True, type="primary"):
            st.switch_page(page_mapper)
    with col4:
        st.error("### 💡 Project Ideator\n\nGet standout project ideas and generate complete architectural execution guides.")
        if st.button("Launch Project Ideator ➔", use_container_width=True, type="primary"):
            st.switch_page(page_projects)


def render_resume():
    st.title("📝 AI ATS Resume Builder")
    st.write("Generate a strict, ATS-friendly PDF. Preview and edit until it is perfect!")
    
    with st.container(border=True):
        st.subheader("✨ 1. AI Auto-Fill & Data Sources")
        col_url1, col_url2 = st.columns(2)
        with col_url1:
            linkedin_url = st.text_input("LinkedIn URL", placeholder="https://linkedin.com/in/your-profile", autocomplete="off")
        with col_url2:
            github_url = st.text_input("GitHub URL", placeholder="https://github.com/your-username", autocomplete="off")
            
        custom_instructions = st.text_area("Custom AI Content Formatting (Optional)", placeholder="e.g., Use STAR method for bullet points, emphasize leadership skills...")
            
        gen_mode = st.radio("How should the AI build your content?", 
                            ["Build entirely from links (Overwrite below)", 
                             "Enhance & Combine links with my manual data below"])
            
        if st.button("🤖 Auto-Generate Content", type="primary"):
            st.session_state.ai_success = False 
            with st.spinner("Fetching live data and generating your profile..."):
                gh_user = github_url.split('/')[-1] if github_url else "None"
                
                gh_text_data, _ = fetch_github_data(gh_user, DEFAULT_GITHUB_TOKEN)
                li_text_data = fetch_linkedin_scrapetable(linkedin_url, DEFAULT_SCRAPETABLE_KEY)
                
                if gen_mode == "Enhance & Combine links with my manual data below":
                    manual_data = f"Name: {st.session_state.res_name}\nEducation: {st.session_state.res_edu}\nProfile: {st.session_state.res_profile}\nSkills: {st.session_state.res_skills}\nExperience: {st.session_state.res_exp}"
                    auto_prompt = f"CRITICAL INSTRUCTION: Based on this live LinkedIn text: '{li_text_data}', live GitHub data: '{gh_text_data}', AND the user's manual data: '{manual_data}'. FOLLOW THESE CUSTOM INSTRUCTIONS: '{custom_instructions}'. Combine and enhance everything into a highly professional profile. Output EXACTLY 4 sections separated by '|||'. Format: [Summary] ||| [Education] ||| [Experience] ||| [Skills]"
                else:
                    auto_prompt = f"CRITICAL INSTRUCTION: Based on this live LinkedIn text: '{li_text_data}' and this live GitHub data: '{gh_text_data}'. FOLLOW THESE CUSTOM INSTRUCTIONS: '{custom_instructions}'. Generate a professional profile from scratch. Output EXACTLY 4 sections separated by '|||'. Format: [Summary] ||| [Education] ||| [Experience] ||| [Skills]"
                
                ai_response = ask_gemini_cli(auto_prompt)
                
                if "TIMEOUT_ERROR" in ai_response:
                    st.error("AI Timeout. Please try again.")
                else:
                    try:
                        parts = ai_response.split("|||")
                        if len(parts) >= 4:
                            st.session_state.res_profile = parts[0].strip()
                            st.session_state.res_edu = parts[1].strip()
                            st.session_state.res_exp = parts[2].strip()
                            st.session_state.res_skills = parts[3].strip()
                            st.session_state.ai_success = True 
                            st.rerun() 
                    except:
                        st.warning("Format error. Try again.")

        if st.session_state.ai_success:
            st.success("✅ AI generation complete!")

    st.divider()
    
    with st.container(border=True):
        st.subheader("✏️ 2. Edit Your Core Details")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", key="res_name", autocomplete="off")
            contact = st.text_input("Contact Info", key="res_contact", autocomplete="off", placeholder="Email | Phone | Location")
            user_edu = st.text_area("Education", key="res_edu", height=150)
        with col2:
            user_profile = st.text_area("Profile Summary", key="res_profile", height=100)
            user_skills = st.text_area("Core Skills", key="res_skills", height=125)
        user_experience = st.text_area("Projects & Experience", key="res_exp", height=200)
    
    st.subheader("📄 3. Choose Template & Preview")
    st.write("**Select a Layout by clicking the button below the design:**")
    
    templates_data = [
        {"name": "Standard Tech (Helvetica, Light Grey Line)", "title": "Standard Tech", "html": '<div class="tpl-page-large"><div class="m-head-lg" style="margin: 0 auto 6px auto; width: 60%;"></div><div style="display:flex; gap:6px;"><div class="m-head-lg" style="width:30%;"></div><div style="width:70%; border-top: 2px solid #CBD5E1; padding-top:4px;"><div class="m-line-lg" style="margin-bottom:4px;"></div><div class="m-line-lg" style="width:80%;"></div></div></div></div>'},
        {"name": "Harvard Classic (Times, Black Line)", "title": "Harvard Classic", "html": '<div class="tpl-page-large"><div class="m-head-lg" style="margin: 0 auto 6px auto; width: 50%;"></div><div style="border-top: 3px solid #000; margin-bottom: 6px;"></div><div class="m-head-lg" style="width:40%;"></div><div class="m-line-lg" style="margin-bottom:4px;"></div><div class="m-line-lg" style="width:80%;"></div></div>'},
        {"name": "Modern Executive (Helvetica, Navy Blue)", "title": "Modern Executive", "html": '<div class="tpl-page-large"><div class="m-head-lg" style="margin: 0 auto 6px auto; width: 60%; background: #1E508C; height: 8px;"></div><div class="m-head-lg" style="width:40%; background: #1E508C;"></div><div class="m-line-lg" style="margin-bottom:4px;"></div><div class="m-line-lg" style="width:80%;"></div></div>'},
        {"name": "Creative Professional (Helvetica, Teal Line)", "title": "Creative Pro", "html": '<div class="tpl-page-large"><div class="m-head-lg" style="margin: 0 auto 6px auto; width: 60%; background: #008080;"></div><div class="m-head-lg" style="width:40%; background: #008080;"></div><div style="border-top: 2px solid #008080; margin-bottom: 6px;"></div><div class="m-line-lg" style="margin-bottom:4px;"></div><div class="m-line-lg" style="width:80%;"></div></div>'},
        {"name": "Minimalist Startup (Helvetica, No Lines)", "title": "Minimalist Startup", "html": '<div class="tpl-page-large"><div class="m-head-lg" style="margin: 0 auto 10px auto; width: 60%;"></div><div class="m-head-lg" style="width:40%; margin-bottom: 6px;"></div><div class="m-line-lg" style="margin-bottom:4px;"></div><div class="m-line-lg" style="width:80%;"></div></div>'},
        {"name": "Finance Strict (Times, Thick Black Line)", "title": "Finance Strict", "html": '<div class="tpl-page-large"><div class="m-head-lg" style="margin: 0 auto 6px auto; width: 50%;"></div><div style="border-top: 4px solid #000; margin-bottom: 6px;"></div><div class="m-head-lg" style="width:40%;"></div><div class="m-line-lg" style="margin-bottom:4px;"></div><div class="m-line-lg" style="width:80%;"></div></div>'},
        {"name": "Engineering Pro (Helvetica, Grey Highlight)", "title": "Engineering Pro", "html": '<div class="tpl-page-large"><div class="m-head-lg" style="margin: 0 auto 6px auto; width: 60%;"></div><div class="m-head-lg" style="width:100%; background: #E2E8F0; padding: 4px 0; height: 12px;"><div style="width:40%; height:4px; background:#475569; margin-left: 4px;"></div></div><div class="m-line-lg" style="margin-bottom:4px; margin-top:4px;"></div><div class="m-line-lg" style="width:80%;"></div></div>'},
        {"name": "Product Manager (Helvetica, Centered)", "title": "Product Manager", "html": '<div class="tpl-page-large"><div class="m-head-lg" style="margin: 0 auto 6px auto; width: 60%;"></div><div class="m-head-lg" style="width:40%; margin: 0 auto 6px auto;"></div><div class="m-line-lg" style="margin: 0 auto 4px auto;"></div><div class="m-line-lg" style="width:80%; margin: 0 auto;"></div></div>'},
        {"name": "Cybersecurity (Courier, Dark Green)", "title": "Cybersecurity", "html": '<div class="tpl-page-large"><div class="m-head-lg" style="margin: 0 auto 6px auto; width: 60%; background: #006400;"></div><div class="m-head-lg" style="width:40%; background: #006400;"></div><div style="border-top: 2px solid #006400; margin-bottom: 6px;"></div><div class="m-line-lg" style="margin-bottom:4px;"></div><div class="m-line-lg" style="width:80%;"></div></div>'},
        {"name": "Elegant Academic (Times, Maroon Line)", "title": "Elegant Academic", "html": '<div class="tpl-page-large"><div class="m-head-lg" style="margin: 0 auto 6px auto; width: 60%; background: #800000;"></div><div class="m-head-lg" style="width:40%; background: #800000;"></div><div style="border-top: 2px solid #800000; margin-bottom: 6px;"></div><div class="m-line-lg" style="margin-bottom:4px;"></div><div class="m-line-lg" style="width:80%;"></div></div>'}
    ]

    cols1 = st.columns(5)
    for i in range(5):
        with cols1[i]:
            st.markdown(templates_data[i]["html"], unsafe_allow_html=True)
            is_selected = (st.session_state.selected_template == templates_data[i]["name"])
            btn_label = "✅ Selected" if is_selected else templates_data[i]["title"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(btn_label, key=f"tpl_{i}", use_container_width=True, type=btn_type):
                st.session_state.selected_template = templates_data[i]["name"]
                st.rerun()

    st.write("") 
    cols2 = st.columns(5)
    for i in range(5, 10):
        with cols2[i - 5]:
            st.markdown(templates_data[i]["html"], unsafe_allow_html=True)
            is_selected = (st.session_state.selected_template == templates_data[i]["name"])
            btn_label = "✅ Selected" if is_selected else templates_data[i]["title"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(btn_label, key=f"tpl_{i}", use_container_width=True, type=btn_type):
                st.session_state.selected_template = templates_data[i]["name"]
                st.rerun()

    st.divider()
    
    if st.button("👁️ Generate & Preview PDF", type="primary", use_container_width=True):
        if name and contact:
            with st.spinner("Rendering High-Quality PDF..."):
                filename = generate_ats_resume(name, contact, user_profile, user_edu, user_experience, user_skills, st.session_state.selected_template)
                st.session_state.pdf_filename = filename
                with open(filename, "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf"></iframe>'
                st.session_state.pdf_display = pdf_display
        else:
            st.warning("Name and Contact Info are required to generate the PDF.")
            
    if st.session_state.pdf_display and st.session_state.pdf_filename:
        st.markdown(st.session_state.pdf_display, unsafe_allow_html=True)
        st.write("") 
        with open(st.session_state.pdf_filename, "rb") as pdf_file:
            st.download_button("⬇️ Download ATS Resume", data=pdf_file, file_name=st.session_state.pdf_filename, mime="application/pdf", use_container_width=True)

def render_website():
    st.title("🌐 Pro AI Website Builder")
    st.write("Code a stunning portfolio site in seconds.")
    
    with st.container(border=True):
        col_img, col_theme = st.columns(2)
        with col_img:
            img_url = st.text_input("Profile Image URL", placeholder="https://...", autocomplete="off")
        with col_theme:
            theme = st.selectbox("Design Theme", ["Ultra-Modern Dark Mode", "Clean Minimalist Light", "Neon Cyberpunk"])
            
        col_li, col_gh = st.columns(2)
        with col_li:
            web_linkedin = st.text_input("LinkedIn Profile URL", autocomplete="off")
        with col_gh:
            web_github = st.text_input("GitHub Profile URL", autocomplete="off")
            
        uploaded_resume = st.file_uploader("Upload Current Resume (PDF/TXT)", type=["pdf", "txt"])
        custom_instructions = st.text_area("Custom Code Instructions", placeholder="e.g., Use a vertical navigation bar, highlight technical skills...")

        if st.button("🚀 Architect Website", type="primary", use_container_width=True):
            with st.spinner("Synthesizing your site..."):
                extracted_data = ""
                if uploaded_resume:
                    if uploaded_resume.name.endswith('.pdf'):
                        extracted_data += extract_pdf_text(uploaded_resume)
                    else:
                        extracted_data += uploaded_resume.getvalue().decode("utf-8")
                
                gh_user = web_github.split('/')[-1] if web_github else "None"
                gh_text_data, gh_avatar = fetch_github_data(gh_user, DEFAULT_GITHUB_TOKEN)
                li_text_data = fetch_linkedin_scrapetable(web_linkedin, DEFAULT_SCRAPETABLE_KEY)
                
                web_prompt = f"CRITICAL: Generate a single-file HTML5 portfolio. Resume: {extracted_data} GH: {gh_text_data} LI: {li_text_data} Image: {img_url if img_url else gh_avatar} Theme: {theme} Custom: {custom_instructions}. Output ONLY raw HTML code."
                
                raw_html = ask_gemini_cli(web_prompt)
                
                if "TIMEOUT_ERROR" in raw_html:
                    st.error("Website generation timed out.")
                else:
                    clean_html = raw_html.replace("```html", "").replace("```", "").strip()
                    st.session_state.portfolio_html = clean_html
                    st.success("✨ Website coded successfully!")

    if st.session_state.portfolio_html:
        st.divider()
        st.subheader("🪄 The Magic Editor")
        edit_col, btn_col = st.columns([4, 1])
        with edit_col:
            user_edit_prompt = st.text_input("Command prompt:", placeholder="e.g., Change the accent color to gold...", autocomplete="off")
        with btn_col:
            st.write("") 
            if st.button("✨ Apply Edit", use_container_width=True):
                if user_edit_prompt:
                    with st.spinner("Applying edit..."):
                        edit_prompt = f"Apply change: {user_edit_prompt}. CODE: {st.session_state.portfolio_html}"
                        raw_updated_html = ask_gemini_cli(edit_prompt)
                        clean_html = raw_updated_html.replace("```html", "").replace("```", "").strip()
                        st.session_state.portfolio_html = clean_html
                        st.success("✨ Website updated!")

        st.subheader("💻 Live Preview & Export")
        st.download_button("⬇️ Download index.html", data=st.session_state.portfolio_html, file_name="pro_portfolio.html", mime="text/html", type="primary")
        with st.container(border=True):
            components.html(st.session_state.portfolio_html, height=800, scrolling=True)


def render_mapper():
    st.title("🧠 Smart Career Mapper")
    target_field = st.text_input("Enter ANY Career Field:", placeholder="e.g., Project Management", autocomplete="off")
    if st.button("🔍 Analyze Field"):
        if target_field:
            with st.spinner("Mining roles..."):
                num_roles = random.randint(5, 7)
                role_prompt = f"Output exactly {num_roles} job titles for '{target_field}', one per line."
                raw_output = ask_gemini_cli(role_prompt)
                st.session_state.generated_roles = [r.strip('1234567890. -*') for r in raw_output.split('\n') if r.strip()]

    if st.session_state.generated_roles:
        selected_role = st.selectbox("Select a role:", st.session_state.generated_roles + ["✨ Other"])
        if selected_role == "✨ Other": selected_role = st.text_input("Custom Role:", autocomplete="off")
        if st.button("🗺️ Generate Guide", type="primary"):
            with st.spinner("Curating roadmap..."):
                roadmap_prompt = f"Generate a markdown career roadmap for {selected_role}."
                st.session_state.roadmap = ask_gemini_cli(roadmap_prompt)
        if st.session_state.roadmap: st.markdown(st.session_state.roadmap)


def render_projects():
    st.title("💡 AI Project Ideator")
    target_project_field = st.text_input("Field/Role:", placeholder="e.g., Fullstack Web, IoT App...", autocomplete="off")
    if st.button("💡 Generate Ideas"):
        if target_project_field:
            with st.spinner("Brainstorming..."):
                idea_prompt = f"Output 10 project idea titles for '{target_project_field}', one per line."
                raw_output = ask_gemini_cli(idea_prompt)
                st.session_state.project_ideas = [r.strip('1234567890. -*') for r in raw_output.split('\n') if r.strip()]

    if st.session_state.project_ideas:
        selected_project = st.selectbox("Select a project:", st.session_state.project_ideas + ["✨ Other"])
        if selected_project == "✨ Other": selected_project = st.text_input("Custom Project:", autocomplete="off")
        if st.button("🏗️ Generate Guide", type="primary"):
            with st.spinner("Architecting..."):
                guide_prompt = f"Generate a markdown build guide for {selected_project}."
                st.session_state.project_guide = ask_gemini_cli(guide_prompt)
        if st.session_state.project_guide: st.markdown(st.session_state.project_guide)

# --- NAVIGATION ---
page_home = st.Page(render_home, title="Dashboard Home", icon="🏠", default=True)
page_resume = st.Page(render_resume, title="AI Resume Builder", icon="📝")
page_website = st.Page(render_website, title="Pro Website Builder", icon="🌐")
page_mapper = st.Page(render_mapper, title="Career Mapper", icon="🧠")
page_projects = st.Page(render_projects, title="Project Ideator", icon="💡")

pg = st.navigation([page_home, page_resume, page_website, page_mapper, page_projects])
pg.run()