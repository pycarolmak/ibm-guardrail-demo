"""
IBM watsonx Guardrails Demo Application
A Streamlit web app demonstrating AI risk assessment and content moderation.
"""

import streamlit as st
from dotenv import load_dotenv
import os
import json
import re
from pathlib import Path

# Load environment variables
load_dotenv()


def load_samples_from_folder(folder_path: str) -> dict:
    """Load sample texts from markdown files in a folder."""
    samples = {}
    folder = Path(folder_path)

    if not folder.exists():
        return samples

    for md_file in sorted(folder.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")

            # Parse the markdown file
            sample_data = {}

            # Extract button label
            label_match = re.search(r"## Button Label\s*\n(.+)", content)
            if label_match:
                button_label = label_match.group(1).strip()
            else:
                button_label = md_file.stem.replace("_", " ").title()

            # Extract sample text
            text_match = re.search(r"## Sample Text\s*\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
            if text_match:
                sample_data["text"] = text_match.group(1).strip()

            # Extract Cantonese sample text
            cantonese_match = re.search(r"## Sample Text \(Cantonese\)\s*\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
            if cantonese_match:
                sample_data["text_cantonese"] = cantonese_match.group(1).strip()


            # Extract detector (if specified)
            detector_match = re.search(r"detector:\s*(\w+)", content)
            if detector_match:
                sample_data["detector"] = detector_match.group(1).strip()

            # Extract system prompt (if specified)
            prompt_match = re.search(r"## System Prompt\s*\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
            if prompt_match:
                sample_data["system_prompt"] = prompt_match.group(1).strip()

            # Extract context (if specified)
            context_match = re.search(r"## Context\s*\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
            if context_match:
                sample_data["context"] = context_match.group(1).strip()

            # Extract user input (if specified)
            user_input_match = re.search(r"## User Input\s*\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
            if user_input_match:
                sample_data["user_input"] = user_input_match.group(1).strip()

            if sample_data.get("text"):
                samples[button_label] = sample_data

        except Exception as e:
            st.warning(f"Error loading {md_file.name}: {e}")

    return samples

from guardrails_client import (
    GuardrailsClient,
    GuardrailResult,
    DetectionResult,
    Direction,
    INPUT_DETECTORS,
    OUTPUT_DETECTORS,
    get_default_config
)
from token_manager import TokenManager
from translation_client import TranslationClient, TranslationResult

# Page configuration
st.set_page_config(
    page_title="IBM watsonx Guardrails Demo",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS that works with both light and dark Streamlit themes
st.markdown("""
<style>
    /* IBM Carbon Design System Colors */
    :root {
        --ibm-blue: #0f62fe;
        --ibm-purple: #8a3ffc;
        --ibm-green: #24a148;
        --ibm-green-light: #42be65;
        --ibm-red: #da1e28;
        --ibm-red-light: #fa4d56;
        --ibm-yellow: #f1c21b;
        --ibm-cyan: #1192e8;
    }

    /* Header styling - works in both themes */
    .main-header {
        background: linear-gradient(135deg, var(--ibm-blue) 0%, var(--ibm-purple) 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 4px 20px rgba(15, 98, 254, 0.3);
    }

    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 600;
        color: white !important;
    }

    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
        color: white !important;
    }

    /* Detector result cards - TRIGGERED (red) */
    .detector-triggered {
        background: linear-gradient(135deg, rgba(218, 30, 40, 0.15) 0%, rgba(250, 77, 86, 0.1) 100%);
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid var(--ibm-red);
        border: 1px solid rgba(218, 30, 40, 0.3);
    }

    .detector-triggered strong {
        color: var(--ibm-red-light);
    }

    .detector-triggered .status {
        color: var(--ibm-red);
        font-weight: bold;
    }

    /* Detector result cards - PASSED (green) */
    .detector-passed {
        background: linear-gradient(135deg, rgba(36, 161, 72, 0.1) 0%, rgba(66, 190, 101, 0.05) 100%);
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid var(--ibm-green);
        border: 1px solid rgba(36, 161, 72, 0.2);
    }

    .detector-passed strong {
        color: var(--ibm-green-light);
    }

    .detector-passed .status {
        color: var(--ibm-green);
    }

    /* Score bar */
    .score-bar {
        height: 8px;
        background: rgba(128, 128, 128, 0.2);
        border-radius: 4px;
        overflow: hidden;
        margin-top: 0.5rem;
    }

    .score-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
    }

    /* Text comparison boxes */
    .text-diff {
        font-family: 'IBM Plex Mono', monospace;
        padding: 1rem;
        border-radius: 8px;
        white-space: pre-wrap;
        word-wrap: break-word;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Primary button styling */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--ibm-blue) 0%, var(--ibm-purple) 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 500;
        border-radius: 8px;
        transition: all 0.2s ease;
    }

    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(15, 98, 254, 0.4);
    }

    /* Sample text buttons */
    .stButton > button {
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
    }

    /* Info/Success/Error boxes */
    .stAlert {
        border-radius: 8px;
    }

    /* Metrics styling */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 600;
    }

    /* Section dividers */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(128,128,128,0.3), transparent);
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


def render_header():
    """Render the main header."""
    st.markdown("""
    <div class="main-header">
        <h1>🛡️ IBM watsonx Guardrails</h1>
        <p>Enterprise AI Risk Assessment & Content Moderation Demo</p>
    </div>
    """, unsafe_allow_html=True)


def apply_theme_css(is_dark: bool):
    """Apply theme-specific CSS overrides."""
    if is_dark:
        st.markdown("""
        <style>
            /* Fix white banner at top */
            .stApp, .stApp > header, [data-testid="stHeader"],
            [data-testid="stToolbar"], .stDeployButton, header[data-testid="stHeader"] {
                background-color: #161616 !important;
            }

            /* Main app background */
            .stApp { background-color: #161616 !important; }

            /* Top toolbar/header area */
            header, header[data-testid="stHeader"], [data-testid="stHeader"] {
                background-color: #161616 !important;
                background: #161616 !important;
            }

            /* Sidebar */
            [data-testid="stSidebar"],
            [data-testid="stSidebar"] > div,
            [data-testid="stSidebarContent"],
            section[data-testid="stSidebar"] {
                background-color: #262626 !important;
            }

            /* All text elements - comprehensive */
            .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
            .stText, p, span, label, div,
            .stSelectbox label, .stRadio label, .stCheckbox label,
            [data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"],
            [data-testid="stExpander"] summary, .stTextArea label,
            [data-testid="stCaptionContainer"], .stCaption,
            .st-emotion-cache-16idsys p, .st-emotion-cache-1629p8f h1,
            .element-container, [data-testid="element-container"] {
                color: #f4f4f4 !important;
            }

            /* Metric values */
            [data-testid="stMetricValue"], [data-testid="stMetricLabel"],
            [data-testid="stMetricDelta"] { color: #f4f4f4 !important; }

            /* Input fields */
            .stTextInput input, .stTextArea textarea,
            [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
                background-color: #262626 !important;
                color: #f4f4f4 !important;
                border-color: #525252 !important;
            }

            /* Selectbox */
            .stSelectbox > div > div, [data-testid="stSelectbox"] > div > div {
                background-color: #262626 !important;
                color: #f4f4f4 !important;
            }

            /* Expander */
            [data-testid="stExpander"], .streamlit-expanderHeader {
                background-color: #262626 !important;
                border-color: #525252 !important;
                color: #f4f4f4 !important;
            }

            /* Buttons in sample area */
            .stButton > button {
                background-color: #393939 !important;
                color: #f4f4f4 !important;
                border-color: #525252 !important;
            }
            .stButton > button:hover {
                background-color: #4c4c4c !important;
                border-color: #6f6f6f !important;
            }

            /* Cards and containers */
            .detection-card { background: #262626 !important; color: #f4f4f4 !important; }
            .text-diff { background: #393939 !important; color: #f4f4f4 !important; }

            /* Detector result cards - Dark theme */
            .detector-triggered {
                background: linear-gradient(135deg, rgba(218, 30, 40, 0.25) 0%, rgba(250, 77, 86, 0.15) 100%) !important;
                border: 1px solid rgba(250, 77, 86, 0.5) !important;
                color: #f4f4f4 !important;
            }
            .detector-triggered strong { color: #fa4d56 !important; }
            .detector-triggered .status { color: #fa4d56 !important; }

            .detector-passed {
                background: linear-gradient(135deg, rgba(36, 161, 72, 0.2) 0%, rgba(66, 190, 101, 0.1) 100%) !important;
                border: 1px solid rgba(66, 190, 101, 0.4) !important;
                color: #f4f4f4 !important;
            }
            .detector-passed strong { color: #42be65 !important; }
            .detector-passed .status { color: #42be65 !important; }

            /* Alert boxes */
            [data-testid="stAlert"], .stAlert {
                background-color: #262626 !important;
                color: #f4f4f4 !important;
            }

            /* JSON display - Dark theme */
            [data-testid="stJson"], .stJson,
            pre, code, .stCodeBlock,
            [data-testid="stExpander"] [data-testid="stJson"],
            [data-testid="stExpander"] pre {
                background-color: #1e1e1e !important;
                color: #d4d4d4 !important;
                border-color: #3e3e3e !important;
            }

            /* Expander - all nested elements dark */
            [data-testid="stExpander"],
            [data-testid="stExpander"] > div,
            [data-testid="stExpander"] > div > div,
            [data-testid="stExpander"] > div > div > div,
            [data-testid="stExpander"] details,
            [data-testid="stExpander"] details > div,
            [data-testid="stExpander"] details[open] > div,
            [data-testid="stExpander"] [data-testid="stExpanderDetails"],
            details[data-testid="stExpander"] > div {
                background-color: #262626 !important;
                color: #f4f4f4 !important;
            }

            /* Expander summary/header */
            [data-testid="stExpander"] summary,
            [data-testid="stExpander"] [data-testid="stExpanderToggleIcon"] {
                background-color: #262626 !important;
                color: #f4f4f4 !important;
            }

            /* JSON viewer specifically */
            [data-testid="stJson"] > div,
            [data-testid="stJson"] > div > div,
            .stJson > div,
            .react-json-view,
            .react-json-view > div {
                background-color: #1e1e1e !important;
                color: #d4d4d4 !important;
            }

            /* JSON keys and values */
            .stJson span { color: #9cdcfe !important; }
            pre span, code span { color: #ce9178 !important; }
            .react-json-view .string-value { color: #ce9178 !important; }
            .react-json-view .boolean-value { color: #569cd6 !important; }
            .react-json-view .null-value { color: #569cd6 !important; }
            .react-json-view .number-value { color: #b5cea8 !important; }
            .react-json-view .key { color: #9cdcfe !important; }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            /* Fix header for light mode */
            .stApp, .stApp > header, [data-testid="stHeader"],
            [data-testid="stToolbar"], header[data-testid="stHeader"] {
                background-color: #ffffff !important;
            }

            /* Main app background */
            .stApp { background-color: #ffffff !important; }

            /* Top toolbar/header area */
            header, header[data-testid="stHeader"], [data-testid="stHeader"] {
                background-color: #ffffff !important;
                background: #ffffff !important;
            }

            /* Sidebar */
            [data-testid="stSidebar"],
            [data-testid="stSidebar"] > div,
            [data-testid="stSidebarContent"],
            section[data-testid="stSidebar"] {
                background-color: #f4f4f4 !important;
            }

            /* All text elements */
            .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
            .stText, p, span, label, div,
            .stSelectbox label, .stRadio label, .stCheckbox label,
            [data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"],
            [data-testid="stExpander"] summary, .stTextArea label,
            [data-testid="stCaptionContainer"], .stCaption,
            .element-container, [data-testid="element-container"] {
                color: #161616 !important;
            }

            /* Metric values */
            [data-testid="stMetricValue"], [data-testid="stMetricLabel"],
            [data-testid="stMetricDelta"] { color: #161616 !important; }

            /* Input fields */
            .stTextInput input, .stTextArea textarea,
            [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
                background-color: #ffffff !important;
                color: #161616 !important;
                border-color: #d3d3d3 !important;
            }

            /* Selectbox */
            .stSelectbox > div > div, [data-testid="stSelectbox"] > div > div {
                background-color: #ffffff !important;
                color: #161616 !important;
            }

            /* Expander */
            [data-testid="stExpander"], .streamlit-expanderHeader {
                background-color: #f4f4f4 !important;
                border-color: #d3d3d3 !important;
                color: #161616 !important;
            }

            /* Buttons */
            .stButton > button {
                background-color: #e0e0e0 !important;
                color: #161616 !important;
                border-color: #c6c6c6 !important;
            }
            .stButton > button:hover {
                background-color: #d0d0d0 !important;
                border-color: #a8a8a8 !important;
            }

            /* Cards and containers */
            .detection-card { background: #f4f4f4 !important; color: #161616 !important; }
            .text-diff { background: #e8e8e8 !important; color: #161616 !important; }

            /* Detector result cards - Light theme */
            .detector-triggered {
                background: linear-gradient(135deg, rgba(218, 30, 40, 0.12) 0%, rgba(250, 77, 86, 0.08) 100%) !important;
                border: 1px solid rgba(218, 30, 40, 0.4) !important;
                color: #161616 !important;
            }
            .detector-triggered strong { color: #a2191f !important; }
            .detector-triggered .status { color: #da1e28 !important; font-weight: bold; }

            .detector-passed {
                background: linear-gradient(135deg, rgba(36, 161, 72, 0.12) 0%, rgba(66, 190, 101, 0.08) 100%) !important;
                border: 1px solid rgba(36, 161, 72, 0.4) !important;
                color: #161616 !important;
            }
            .detector-passed strong { color: #198038 !important; }
            .detector-passed .status { color: #24a148 !important; }

            /* Alert boxes */
            [data-testid="stAlert"], .stAlert {
                background-color: #f4f4f4 !important;
                color: #161616 !important;
            }
        </style>
        """, unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar with configuration and info."""
    with st.sidebar:
        # Theme toggle
        st.markdown("## 🎨 Theme")
        is_dark_mode = st.toggle("🌙 Dark Mode", value=True, key="theme_toggle")

        # Apply theme CSS based on toggle
        apply_theme_css(is_dark_mode)

        st.markdown("---")

        # Multilingual Support Toggle
        st.markdown("## 🌐 Language Support")
        
        # Sample Language Selection
        sample_language = st.radio(
            "Sample Text Language",
            options=["English", "Cantonese"],
            index=0,
            horizontal=True,
            help="Select the language for the sample text buttons."
        )
        
        multilingual_enabled = st.toggle(
            "Enable Multilingual Translation",
            value=False,
            key="multilingual_toggle",
            help="Auto-detect non-English text and translate to English. Analyzes BOTH original and translated text."
        )

        if multilingual_enabled:
            st.info("Text will be analyzed in both original language AND English translation. A detector triggers if either version flags content.")

        st.markdown("---")

        st.markdown("## ⚙️ Configuration")

        # Direction selector
        direction = st.radio(
            "Check Direction",
            options=["input", "output"],
            format_func=lambda x: "🔵 User Input" if x == "input" else "🟢 LLM Output",
            help="Input: Check text sent TO the AI. Output: Check text FROM the AI."
        )

        st.markdown("---")

        # API Configuration
        st.markdown("## 🔑 API Settings")

        defaults = get_default_config()
        use_custom_config = st.checkbox("Use custom API configuration", value=False, help="[API Documentation](https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/fm-hap-wxai.html?context=wx&audience=wdp)")

        if use_custom_config:
            api_key = st.text_input(
                "IBM API Key",
                type="password",
                placeholder="Enter your IBM Cloud API key",
                help="Your IBM Cloud API key for authentication"
            )
            policy_id = st.text_input(
                "Policy ID",
                value="",
                placeholder="Enter policy ID (UUID)",
                help="The guardrails policy ID"
            )
            inventory_id = st.text_input(
                "Inventory ID",
                value="",
                placeholder="Enter inventory ID (UUID)",
                help="The inventory ID"
            )
            governance_id = st.text_input(
                "Governance Instance ID",
                value="",
                placeholder="Enter governance instance ID (UUID)",
                help="The governance instance ID"
            )

            # watsonx.ai Translation Settings
            st.markdown("#### 🌐 Translation Settings")
            watsonx_project_id = st.text_input(
                "watsonx.ai Project ID",
                value="",
                placeholder="Enter watsonx.ai project ID (UUID)",
                help="Required for multilingual translation feature"
            )

            # Use custom values or fall back to defaults
            config = {
                "api_key": api_key if api_key else defaults["api_key"],
                "policy_id": policy_id if policy_id else defaults["policy_id"],
                "inventory_id": inventory_id if inventory_id else defaults["inventory_id"],
                "governance_instance_id": governance_id if governance_id else defaults["governance_instance_id"],
                "watsonx_project_id": watsonx_project_id if watsonx_project_id else os.getenv("WATSONX_PROJECT_ID", "")
            }
        else:
            config = defaults
            config["watsonx_project_id"] = os.getenv("WATSONX_PROJECT_ID", "")
            st.info("ℹ️ Using default configuration from environment")

        st.markdown("---")

        # Token status
        st.markdown("## 🔐 API Status")
        try:
            if config["api_key"]:
                token_mgr = TokenManager(api_key=config["api_key"])
                token_info = token_mgr.get_token_info()
                if token_info["valid"]:
                    st.success(f"✅ {token_info['message']}")
                else:
                    st.warning(f"⚠️ {token_info['message']}")
            else:
                st.warning("⚠️ No API key configured")
        except Exception as e:
            st.error(f"❌ Token error: {str(e)}")

        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This demo showcases IBM watsonx.governance
        Guardrails for enterprise AI safety.

        [Learn more about watsonx AI Guardrails](https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/fm-hap.html?context=wx)

        [🚀 Try it on HKSTP Open API Hub](https://hub.openapi.hkstp.org/en-us/p/ibm-watsonx-guardrail-2eaik/api/watsonx-guardrail-rtrjg/readme)
        """)

        return direction, config, multilingual_enabled, sample_language


def render_detector_selection(direction: str):
    """Render detector selection based on direction."""
    st.markdown("### 🔍 Select Detectors")

    detectors = INPUT_DETECTORS if direction == "input" else OUTPUT_DETECTORS
    selected_detectors = {}

    # Basic detectors (no parameters)
    st.markdown("#### Basic Detectors")
    basic_cols = st.columns(4)
    basic_detectors = {k: v for k, v in detectors.items() if not v.get("has_params", False)}

    for i, (key, info) in enumerate(basic_detectors.items()):
        with basic_cols[i % 4]:
            if st.checkbox(f"{info['icon']} {info['name']}", value=True, key=f"detector_{key}"):
                selected_detectors[key] = {}

    # Advanced detectors (with parameters)
    advanced_detectors = {k: v for k, v in detectors.items() if v.get("has_params", False)}

    if advanced_detectors:
        st.markdown("---")
        st.markdown("### ⚡ Advanced Detectors")
        st.caption("These detectors require additional configuration parameters")

        for key, info in advanced_detectors.items():
            # Auto-expand if detector was enabled via sample button
            is_enabled_in_session = st.session_state.get(f"enable_{key}", False)
            with st.expander(f"{info['icon']} {info['name']} - {info['description']}", expanded=is_enabled_in_session):
                enabled = st.checkbox(f"Enable {info['name']}", value=False, key=f"enable_{key}")

                if enabled:
                    params = {}

                    if key == "topic_relevance" or key == "prompt_safety_risk":
                        # System prompt is now configured in the global input below
                        st.info("💡 System prompt is configured in the input section below.")

                    elif key == "groundedness" or key == "context_relevance":
                        # Context is now configured in the global input below
                        st.info("💡 Reference context is configured in the input section below.")

                    elif key == "answer_relevance":
                        # User question is now configured in the global input below
                        st.info("💡 Original user question is configured in the input section below.")

                    selected_detectors[key] = params

    return selected_detectors


def render_sample_texts(direction: str, language: str = "English"):
    """Render sample text buttons based on direction - loads from markdown files."""
    st.markdown("### 📝 Try Sample Texts")
    st.caption("Click any sample to test different detectors (edit samples in /samples folder)")

    # Get the samples folder path
    app_dir = Path(__file__).parent
    if direction == "input":
        samples_folder = app_dir / "samples" / "input"
    else:
        samples_folder = app_dir / "samples" / "output"

    # Load samples from markdown files
    samples = load_samples_from_folder(samples_folder)

    # Fallback if no samples loaded
    if not samples:
        st.warning(f"No samples found in {samples_folder}. Please create .md files.")
        return

    # Display samples in a grid (4 columns for better layout with more samples)
    sample_list = list(samples.items())
    num_cols = 4

    def set_sample(sample_data):
        """Set sample text and optionally enable detector with system prompt."""
        if language == "Cantonese" and "text_cantonese" in sample_data:
            text = sample_data.get("text_cantonese", "")
        else:
            text = sample_data.get("text", "")
            
        st.session_state.sample_text = text
        st.session_state.text_to_analyze = text

        # Set global system prompt if provided (for the main system prompt input)
        if "system_prompt" in sample_data:
            st.session_state.global_system_prompt = sample_data["system_prompt"]

        # If this sample has an associated detector, enable it
        detector = sample_data.get("detector")
        if detector:
            st.session_state[f"enable_{detector}"] = True

            # Also set detector-specific system prompt for backward compatibility
            if "system_prompt" in sample_data:
                st.session_state[f"{detector}_system_prompt"] = sample_data["system_prompt"]

            # Set context if provided (for groundedness, context_relevance)
            if "context" in sample_data:
                st.session_state[f"{detector}_context"] = sample_data["context"]
                st.session_state.global_context = sample_data["context"]  # Set global too

            # Set user_input if provided (for answer_relevance)
            if "user_input" in sample_data:
                st.session_state[f"{detector}_user_input"] = sample_data["user_input"]
                st.session_state.global_user_question = sample_data["user_input"]  # Set global too


    for row_start in range(0, len(sample_list), num_cols):
        cols = st.columns(num_cols)
        for col_idx, (name, sample_data) in enumerate(sample_list[row_start:row_start + num_cols]):
            with cols[col_idx]:
                st.button(
                    name,
                    key=f"sample_{direction}_{row_start + col_idx}",
                    use_container_width=True,
                    on_click=set_sample,
                    args=(sample_data,)
                )


def get_status_class(detected: bool, score: float) -> str:
    """Get the CSS class based on detection status."""
    if detected:
        return "danger" if score >= 0.7 else "warning"
    return "safe"


def get_status_icon(detected: bool, score: float) -> str:
    """Get the status icon based on detection status."""
    if detected:
        return "🔴" if score >= 0.7 else "🟡"
    return "🟢"


def render_individual_detector_results(text: str, results: list, raw_response: dict = None):
    """Render results from individual detector testing."""

    # Count violations
    violations = [r for r in results if r.detected]
    safe_detectors = [r for r in results if not r.detected]

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if violations:
            st.metric("Overall Status", "🚫 BLOCKED", delta=f"{len(violations)} triggered", delta_color="inverse")
        else:
            st.metric("Overall Status", "✅ Safe", delta="No Issues")

    with col2:
        st.metric("Detectors Tested", len(results))

    with col3:
        st.metric("Violations", len(violations), delta_color="inverse" if violations else "normal")

    with col4:
        st.metric("Safe", len(safe_detectors))

    st.markdown("---")

    # Show ALL detector results
    st.markdown("### 📊 Individual Detector Test Results")
    st.info(f"Each detector was tested with a separate API call using its own policy. Total calls: {raw_response.get('total_calls', len(results)) if raw_response else len(results)}")

    # Create columns for results
    cols = st.columns(3)

    for i, detection in enumerate(results):
        detector_info = INPUT_DETECTORS.get(detection.name) or OUTPUT_DETECTORS.get(detection.name) or {}
        icon = detector_info.get("icon", "📋")
        name = detector_info.get("name", detection.name.replace('_', ' ').title())

        with cols[i % 3]:
            if detection.detected:
                st.markdown(f"""
                <div class="detector-triggered">
                    <strong>{icon} {name}</strong><br>
                    <span class="status">🔴 TRIGGERED</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="detector-passed">
                    <strong>{icon} {name}</strong><br>
                    <span class="status">🟢 Passed</span>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # Detailed results per detector - more visible
    st.markdown("### 📋 Detailed Results Per Detector")
    for detection in results:
        detector_info = INPUT_DETECTORS.get(detection.name) or OUTPUT_DETECTORS.get(detection.name) or {}
        icon = detector_info.get("icon", "📋")
        name = detector_info.get("name", detection.name.replace('_', ' ').title())
        status = "🔴 TRIGGERED" if detection.detected else "🟢 Passed"

        with st.expander(f"{icon} {name}: {status}", expanded=detection.detected):
            if detection.details:
                st.json(detection.details)
            else:
                st.write("No additional details")

    st.markdown("---")

    # RAW API Responses - more visible (not collapsed by default for triggered)
    st.markdown("### 🔧 Raw API Responses (All Calls)")
    if raw_response:
        # Show summary first
        if raw_response.get("detectors_triggered"):
            st.success(f"**Triggered Detectors:** {', '.join(raw_response.get('detectors_triggered', []))}")

        # Show each call's response
        for i, call in enumerate(raw_response.get("calls", [])):
            detector = call.get("detector", f"Call {i+1}")
            policy_id = call.get("policy_id", "N/A")
            blocked = call.get("blocked", False)

            status_icon = "🔴" if blocked else "🟢"
            with st.expander(f"{status_icon} {detector.upper()} - Policy: {policy_id[:8]}...", expanded=blocked):
                st.json(call)
    else:
        st.warning("No raw response available")



def render_detection_results(result: GuardrailResult):
    """Render the detection results."""
    if not result.success:
        st.error(f"❌ Error: {result.error_message}")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if result.has_violations:
            st.metric("Overall Status", "⚠️ Issues Found", delta="Review Required", delta_color="inverse")
        else:
            st.metric("Overall Status", "✅ Safe", delta="No Issues")

    with col2:
        st.metric("Detectors Run", result.total_detectors)

    with col3:
        st.metric("Succeeded", result.succeeded_detectors)

    with col4:
        violations = sum(1 for d in result.detections if d.detected)
        st.metric("Violations", violations, delta=f"-{violations}" if violations > 0 else None, delta_color="inverse" if violations > 0 else "normal")

    st.markdown("---")

    # Text comparison
    st.markdown("### 📄 Text Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Original Text:**")
        st.markdown(f"""
        <div class="text-diff text-original">{result.original_text}</div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("**Processed Text:**")
        processed_class = "text-processed" if result.original_text != result.processed_text else "text-original"
        st.markdown(f"""
        <div class="text-diff {processed_class}">{result.processed_text}</div>
        """, unsafe_allow_html=True)

    if result.original_text != result.processed_text:
        st.info("ℹ️ PII has been automatically redacted in the processed text.")

    st.markdown("---")

    # Detector breakdown
    st.markdown("### 🔍 Detector Results")

    if result.detections:
        cols = st.columns(3)
        for i, detection in enumerate(result.detections):
            with cols[i % 3]:
                status_class = get_status_class(detection.detected, detection.score)
                status_icon = get_status_icon(detection.detected, detection.score)

                if detection.detected:
                    bar_color = "#da1e28" if detection.score >= 0.7 else "#f1c21b"
                else:
                    bar_color = "#24a148"

                st.markdown(f"""
                <div class="detection-card {status_class}">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong>{detection.name.replace('_', ' ').title()}</strong>
                        <span>{status_icon}</span>
                    </div>
                    <div style="margin-top: 0.5rem; opacity: 0.7;">
                        Score: {detection.score:.2f}
                    </div>
                    <div class="score-bar">
                        <div class="score-fill" style="width: {detection.score * 100}%; background: {bar_color};"></div>
                    </div>
                    <div style="margin-top: 0.5rem; font-size: 0.85rem; opacity: 0.7;">
                        {'Detected' if detection.detected else 'Not detected'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("No detector results available.")

    # Raw response expander
    with st.expander("🔧 View Raw API Response"):
        st.json(result.raw_response)


def main():
    """Main application entry point."""
    # Initialize session state for sample text
    if "sample_text" not in st.session_state:
        st.session_state.sample_text = ""

    # Render sidebar and get config
    direction, config, multilingual_enabled, language = render_sidebar()

    render_header()

    # Main content area
    st.markdown("## 🔍 Test Content Moderation")

    # Sample text buttons (set session_state.sample_text via callback)
    render_sample_texts(direction, language)

    st.markdown("---")

    # Detector selection
    selected_detectors = render_detector_selection(direction)

    st.markdown("---")

    # Text input - directly use sample_text from session state
    text_input = st.text_area(
        "Enter text to analyze:",
        value=st.session_state.get("sample_text", ""),
        height=150,
        placeholder="Type or paste text here to check for policy violations...",
        help="Enter the text you want to analyze. Click a sample button above for quick testing."
    )

    # Additional inputs based on direction
    system_prompt_input = ""
    context_input = ""
    user_question_input = ""

    if direction == "input":
        # Check if topic_relevance or prompt_safety_risk is enabled
        topic_relevance_enabled = st.session_state.get("enable_topic_relevance", False)
        prompt_safety_enabled = st.session_state.get("enable_prompt_safety_risk", False)
        requires_system_prompt = topic_relevance_enabled or prompt_safety_enabled

        with st.expander("📝 System Prompt (Required for Topic Relevance & Prompt Safety Risk)", expanded=requires_system_prompt):
            system_prompt_input = st.text_area(
                "System Prompt:",
                value=st.session_state.get("global_system_prompt", ""),
                height=100,
                placeholder="Define your AI assistant's role and allowed topics...\nExample: You are a financial analyst assistant. Stay focused on financial topics only.",
                help="System prompt defines the AI's role and boundaries. Required for Topic Relevance and Prompt Safety Risk detectors.",
                key="global_system_prompt"
            )

            if requires_system_prompt and not system_prompt_input.strip():
                st.warning("⚠️ System prompt is required for Topic Relevance and/or Prompt Safety Risk detectors.")

    else:  # Output direction
        # Check if groundedness, context_relevance, or answer_relevance is enabled
        groundedness_enabled = st.session_state.get("enable_groundedness", False)
        context_relevance_enabled = st.session_state.get("enable_context_relevance", False)
        answer_relevance_enabled = st.session_state.get("enable_answer_relevance", False)

        requires_context = groundedness_enabled or context_relevance_enabled
        requires_user_question = answer_relevance_enabled

        # Context input for Groundedness and Context Relevance
        with st.expander("📚 Context (Required for Groundedness & Context Relevance)", expanded=requires_context):
            context_input = st.text_area(
                "Reference Context:",
                value=st.session_state.get("global_context", ""),
                height=100,
                placeholder="Enter the reference documents or context that the LLM response should be grounded in...\nExample: IBM HR Policy: Section 1 - Dress code is business casual. Section 2 - Work hours are 9am to 5pm.",
                help="The context/documents that the LLM output should be based on. Required for Groundedness and Context Relevance detectors.",
                key="global_context"
            )

            if requires_context and not context_input.strip():
                st.warning("⚠️ Context is required for Groundedness and/or Context Relevance detectors.")

        # User question input for Answer Relevance
        with st.expander("❓ Original User Question (Required for Answer Relevance)", expanded=requires_user_question):
            user_question_input = st.text_area(
                "Original User Question:",
                value=st.session_state.get("global_user_question", ""),
                height=80,
                placeholder="Enter the original question/prompt that generated this LLM response...\nExample: What were the sales figures for Q3?",
                help="The original user question that the LLM was responding to. Required for Answer Relevance detector.",
                key="global_user_question"
            )

            if requires_user_question and not user_question_input.strip():
                st.warning("⚠️ Original user question is required for Answer Relevance detector.")

    # Analyze button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_clicked = st.button(
            "🔍 Analyze Text",
            use_container_width=True,
            type="primary"
        )

    # Store current text for next rerun
    if text_input:
        st.session_state.sample_text = text_input

    st.markdown("---")

    # Results section
    if analyze_clicked and text_input:
        if not config["api_key"]:
            st.error("❌ Please configure your IBM API Key in the sidebar.")
        elif not selected_detectors:
            st.warning("⚠️ Please select at least one detector.")
        else:
            client = GuardrailsClient(
                api_key=config["api_key"],
                policy_id=config["policy_id"],
                inventory_id=config["inventory_id"],
                governance_instance_id=config["governance_instance_id"]
            )

            # Test each detector individually
            try:
                dir_enum = Direction.INPUT if direction == "input" else Direction.OUTPUT

                # Inject global inputs into detectors that need them
                if direction == "input" and system_prompt_input.strip():
                    for detector_key in ["topic_relevance", "prompt_safety_risk"]:
                        if detector_key in selected_detectors:
                            selected_detectors[detector_key]["system_prompt"] = system_prompt_input.strip()

                if direction == "output":
                    # Inject context for groundedness and context_relevance
                    if context_input.strip():
                        for detector_key in ["groundedness", "context_relevance"]:
                            if detector_key in selected_detectors:
                                selected_detectors[detector_key]["context"] = [context_input.strip()]
                                selected_detectors[detector_key]["context_type"] = "docs"

                    # Inject user question for answer_relevance
                    if user_question_input.strip():
                        if "answer_relevance" in selected_detectors:
                            selected_detectors["answer_relevance"]["prompt"] = user_question_input.strip()

                # Check if multilingual mode is enabled
                if multilingual_enabled:
                    # Step 1: Translate
                    with st.spinner("🌐 Detecting language and translating..."):
                        try:
                            translation_client = TranslationClient(
                                api_key=config["api_key"],
                                project_id=config.get("watsonx_project_id")
                            )
                            translation_result = translation_client.detect_and_translate(text_input)

                            if not translation_result.success:
                                st.warning(f"Translation warning: {translation_result.error_message}. Proceeding with original text only.")
                                # Fall back to single analysis
                                with st.spinner(f"🔬 Testing {len(selected_detectors)} detectors..."):
                                    individual_results, raw_response = client.test_detectors_individually(
                                        text_input,
                                        direction=dir_enum,
                                        selected_detectors=selected_detectors
                                    )
                                    render_individual_detector_results(text_input, individual_results, raw_response)
                            elif translation_result.is_english:

                                # User requested silent handling if already English
                                with st.spinner(f"🔬 Testing {len(selected_detectors)} detectors..."):
                                    individual_results, raw_response = client.test_detectors_individually(
                                        text_input,
                                        direction=dir_enum,
                                        selected_detectors=selected_detectors
                                    )
                                    render_individual_detector_results(text_input, individual_results, raw_response)
                            else:
                                st.success(f"Detected: **{translation_result.source_language}** - Running analysis on translated text.")
                                
                                # Show translated text clearly to the user
                                with st.expander("📄 View Translated Text (used for analysis)", expanded=True):
                                    st.markdown(translation_result.translated_text)

                                # Run analysis ONLY on translated text
                                with st.spinner(f"🔬 Testing {len(selected_detectors)} detectors on translated text..."):
                                    translated_results, translated_raw = client.test_detectors_individually(
                                        translation_result.translated_text,
                                        direction=dir_enum,
                                        selected_detectors=selected_detectors
                                    )
                                
                                # Render results as if it were a normal single-text analysis
                                render_individual_detector_results(translation_result.translated_text, translated_results, translated_raw)

                        except ValueError as e:
                            st.error(f"Translation setup error: {str(e)}")
                            st.info("💡 Make sure WATSONX_PROJECT_ID is set in your .env file.")
                else:
                    # Standard single analysis (no translation)
                    with st.spinner(f"🔬 Testing {len(selected_detectors)} detectors individually..."):
                        individual_results, raw_response = client.test_detectors_individually(
                            text_input,
                            direction=dir_enum,
                            selected_detectors=selected_detectors
                        )
                        render_individual_detector_results(text_input, individual_results, raw_response)

            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
                st.info("💡 Make sure your API configuration is correct.")

    elif analyze_clicked and not text_input:
        st.warning("⚠️ Please enter some text to analyze.")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; opacity: 0.7; padding: 1rem;">
        <p>Powered by <strong>IBM watsonx.governance</strong></p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
