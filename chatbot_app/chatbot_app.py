"""
Chatbot Application with IBM watsonx Guardrails Integration
A chat interface with detector selection and system prompt configuration.
"""

import streamlit as st
import sys
import os
from openai import OpenAI
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path to import guardrails_client and translation_client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guardrails_client import GuardrailsClient, Direction, INPUT_DETECTORS, OUTPUT_DETECTORS
from translation_client import TranslationClient

# Page configuration
st.set_page_config(
    page_title="Guardrails Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = "You are a helpful AI assistant."

if "selected_input_detectors" not in st.session_state:
    st.session_state.selected_input_detectors = ["topic_relevance", "prompt_safety_risk", "social_bias", "hap"]

if "selected_output_detectors" not in st.session_state:
    st.session_state.selected_output_detectors = ["harm", "social_bias", "hap"]

if "guardrails_client" not in st.session_state:
    st.session_state.guardrails_client = None

if "hf_api_key" not in st.session_state:
    st.session_state.hf_api_key = os.getenv("HF_API_KEY", "")

if "ibm_api_key" not in st.session_state:
    st.session_state.ibm_api_key = os.getenv("IBM_API_KEY", "")

if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = True

if "multilingual_enabled" not in st.session_state:
    st.session_state.multilingual_enabled = True

if "watsonx_project_id" not in st.session_state:
    st.session_state.watsonx_project_id = os.getenv("WATSONX_PROJECT_ID", "")

if "selected_model" not in st.session_state:
    st.session_state.selected_model = "deepseek-ai/DeepSeek-V4-Pro:novita"

if "processing_response" not in st.session_state:
    st.session_state.processing_response = False


def apply_custom_css():
    """Apply custom CSS styling."""
    st.markdown("""
    <style>
    /* Main container */
    .main {
        padding: 1rem;
    }
    
    /* Chat messages */
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    
    .user-message {
    }
    
    .assistant-message {
    }
    
    .detector-alert {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
    }
    
    .detector-warning {
        background-color: #fff3cd !important;
        border-left: 4px solid #ffc107 !important;
        color: #856404 !important;
    }
    
    .detector-danger {
        background-color: #f8d7da !important;
        border-left: 4px solid #dc3545 !important;
        color: #721c24 !important;
    }
    
    .detector-safe {
        background-color: #d4edda;
        border-left: 3px solid #28a745;
        color: #155724;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    
    /* Detector checkboxes */
    .detector-section {
        padding: 0.5rem;
        margin-bottom: 1rem;
        border-radius: 0.3rem;
        background-color: white;
    }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar with detector selection and configuration."""
    with st.sidebar:
        st.title("⚙️ Configuration")
        
        # API Keys Section
        st.subheader("🔑 API Keys")
        
        # Show status of environment variables
        hf_from_env = bool(os.getenv("HF_API_KEY"))
        ibm_from_env = bool(os.getenv("IBM_API_KEY"))
        
        if hf_from_env or ibm_from_env:
            st.info("✅ API keys loaded from .env file")
        
        hf_key = st.text_input(
            "HuggingFace API Key" + (" (Override)" if hf_from_env else ""),
            value=st.session_state.hf_api_key,
            type="password",
            help="Your HuggingFace API key for the chat model" +
                 (" - Currently using .env value" if hf_from_env else ""),
            placeholder="Enter key or use .env file"
        )
        if hf_key != st.session_state.hf_api_key:
            st.session_state.hf_api_key = hf_key
        
        ibm_key = st.text_input(
            "IBM Cloud API Key" + (" (Override)" if ibm_from_env else ""),
            value=st.session_state.ibm_api_key,
            type="password",
            help="Your IBM Cloud API key for guardrails" +
                 (" - Currently using .env value" if ibm_from_env else ""),
            placeholder="Enter key or use .env file"
        )
        if ibm_key != st.session_state.ibm_api_key:
            st.session_state.ibm_api_key = ibm_key
            # Reinitialize guardrails client with new key
            if ibm_key:
                st.session_state.guardrails_client = GuardrailsClient(api_key=ibm_key)
        
        st.divider()
        
        # Model Selection Section
        st.subheader("🤖 Model Selection")
        
        # Available models
        available_models = {
            # "Qwen/Qwen3.5-9B:fastest": "Qwen 3.5 (9B)",
            "Qwen/Qwen3-8B:fireworks-ai": "Qwen 3 (8B)",
            "deepseek-ai/DeepSeek-V4-Pro:novita": "DeepSeek V4 Pro (1.6T 49B)",
            # "deepseek-ai/DeepSeek-V4-Flash:fastest": "DeepSeek V4 Flash",
        }
        
        selected_model = st.selectbox(
            "Select Model",
            options=list(available_models.keys()),
            format_func=lambda x: available_models[x],
            index=list(available_models.keys()).index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0,
            help="Choose the HuggingFace model to use for chat responses"
        )
        
        if selected_model != st.session_state.selected_model:
            st.session_state.selected_model = selected_model
        
        st.divider()
        
        # System Prompt Section
        st.subheader("📝 System Prompt")
        system_prompt = st.text_area(
            "System Prompt",
            value=st.session_state.system_prompt,
            height=100,
            help="Define the behavior and personality of the AI assistant"
        )
        if system_prompt != st.session_state.system_prompt:
            st.session_state.system_prompt = system_prompt
        
        st.divider()
        
        # Input Detectors Section
        st.subheader("🛡️ Input Detectors")
        st.caption("Select detectors to check user messages")
        
        input_detectors = []
        for detector_key, detector_info in INPUT_DETECTORS.items():
            if st.checkbox(
                f"{detector_info['icon']} {detector_info['name']}",
                value=detector_key in st.session_state.selected_input_detectors,
                key=f"input_{detector_key}",
                help=detector_info['description']
            ):
                input_detectors.append(detector_key)
        
        st.session_state.selected_input_detectors = input_detectors
        
        st.divider()
        
        # Output Detectors Section
        st.subheader("🔍 Output Detectors")
        st.caption("Select detectors to check AI responses")
        
        output_detectors = []
        for detector_key, detector_info in OUTPUT_DETECTORS.items():
            # Skip detectors that require additional parameters for now
            if detector_info.get('has_params', False):
                continue
                
            if st.checkbox(
                f"{detector_info['icon']} {detector_info['name']}",
                value=detector_key in st.session_state.selected_output_detectors,
                key=f"output_{detector_key}",
                help=detector_info['description']
            ):
                output_detectors.append(detector_key)
        
        st.session_state.selected_output_detectors = output_detectors
        
        st.divider()
        
        # Multilingual Support Section
        st.subheader("🌐 Multilingual Support")
        multilingual_enabled = st.checkbox(
            "Enable Chinese-to-English Translation",
            value=st.session_state.multilingual_enabled,
            help="Automatically detect and translate Chinese text to English before guardrails check"
        )
        if multilingual_enabled != st.session_state.multilingual_enabled:
            st.session_state.multilingual_enabled = multilingual_enabled
        
        if multilingual_enabled:
            watsonx_project_id = st.text_input(
                "watsonx.ai Project ID",
                value=st.session_state.watsonx_project_id,
                type="password",
                help="Your watsonx.ai project ID for translation",
                placeholder="Enter project ID or use .env file"
            )
            if watsonx_project_id != st.session_state.watsonx_project_id:
                st.session_state.watsonx_project_id = watsonx_project_id
        
        st.divider()
        
        # Debug mode toggle
        st.subheader("🔧 Debug")
        debug_mode = st.checkbox(
            "Enable Debug Mode",
            value=st.session_state.debug_mode,
            help="Show detailed detector information and API responses"
        )
        if debug_mode != st.session_state.debug_mode:
            st.session_state.debug_mode = debug_mode
        
        st.divider()
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()


def check_text_with_guardrails(text: str, direction: Direction, detectors: List[str], enable_translation: bool = False) -> Dict:
    """
    Check text with selected guardrails detectors.
    Optionally translates Chinese text to English before checking.
    
    Args:
        text: Text to check
        direction: INPUT or OUTPUT
        detectors: List of detector names to use
        enable_translation: Whether to detect and translate Chinese text
    
    Returns:
        Dictionary with detection results including translation info
    """
    original_text = text
    translated_text = None
    source_language = None
    translation_error = None
    
    # Step 1: Translation (if enabled)
    if enable_translation and st.session_state.multilingual_enabled:
        try:
            if not st.session_state.watsonx_project_id:
                translation_error = "watsonx.ai Project ID not configured"
            else:
                translation_client = TranslationClient(
                    api_key=st.session_state.ibm_api_key,
                    project_id=st.session_state.watsonx_project_id
                )
                translation_result = translation_client.detect_and_translate(text)
                
                if translation_result.success:
                    source_language = translation_result.source_language
                    if not translation_result.is_english:
                        # Use translated text for guardrails check
                        text = translation_result.translated_text
                        translated_text = translation_result.translated_text
                else:
                    translation_error = translation_result.error_message
        except Exception as e:
            translation_error = str(e)
    
    # Step 2: Guardrails check (on translated text if available, otherwise original)
    if not st.session_state.guardrails_client:
        if st.session_state.ibm_api_key:
            st.session_state.guardrails_client = GuardrailsClient(
                api_key=st.session_state.ibm_api_key
            )
        else:
            return {
                "success": False,
                "error": "IBM API key not configured",
                "detections": [],
                "missing_policies": []
            }
    
    # Check for missing policy IDs
    missing_policies = []
    detector_name_map = {
        "pii": "POLICY_ID_PII",
        "harm": "POLICY_ID_HARM",
        "jailbreak": "POLICY_ID_JAILBREAK",
        "social_bias": "POLICY_ID_SOCIAL_BIAS",
        "profanity": "POLICY_ID_PROFANITY",
        "sexual_content": "POLICY_ID_SEXUAL_CONTENT",
        "unethical_behavior": "POLICY_ID_UNETHICAL_BEHAVIOR",
        "violence": "POLICY_ID_VIOLENCE",
        "hap": "POLICY_ID_HAP",
        "topic_relevance": "POLICY_ID_TOPIC_RELEVANCE",
        "prompt_safety_risk": "POLICY_ID_PROMPT_SAFETY_RISK",
        "groundedness": "POLICY_ID_GROUNDEDNESS",
        "context_relevance": "POLICY_ID_CONTEXT_RELEVANCE",
        "answer_relevance": "POLICY_ID_ANSWER_RELEVANCE",
        "keyword": "POLICY_ID_KEYWORD",
        "regex": "POLICY_ID_REGULAR_EXPRESSION"
    }
    
    for detector in detectors:
        env_var = detector_name_map.get(detector)
        if env_var:
            policy_id = os.getenv(env_var)
            if not policy_id or policy_id.startswith("your_"):
                missing_policies.append({
                    "detector": detector,
                    "env_var": env_var,
                    "current_value": policy_id or "Not set"
                })
    
    # Build detector configuration
    detector_config = {}
    for detector in detectors:
        if detector in ["topic_relevance", "prompt_safety_risk"]:
            detector_config[detector] = {"system_prompt": st.session_state.system_prompt}
        else:
            detector_config[detector] = {}
    
    try:
        # Use individual detector testing for clearer results
        individual_results, raw_response = st.session_state.guardrails_client.test_detectors_individually(
            text=text,
            direction=direction,
            selected_detectors=detector_config
        )

        # Debug output
        if st.session_state.debug_mode:
            print('-'*50)
            print(f'Direction: {direction}')
            print(f'Text: {text[:100]}...' if len(text) > 100 else f'Text: {text}')
            print(f'Detectors checked: {len(individual_results)}')
            print('\n'.join([
                f"  {k.name}: detected={k.detected}, score={k.score}" for k in individual_results
            ]))
            print('-'*50)
        
        return {
            "success": True,
            "detections": individual_results,
            "raw_response": raw_response,
            "has_violations": any(d.detected for d in individual_results),
            "missing_policies": missing_policies,
            "original_text": original_text,
            "translated_text": translated_text,
            "source_language": source_language,
            "translation_error": translation_error
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "detections": [],
            "original_text": original_text,
            "translated_text": translated_text,
            "source_language": source_language,
            "translation_error": translation_error
        }


def render_detection_results(detections: List, direction: str, total_selected: int = 0, missing_policies: Optional[List[Dict]] = None):
    """Render detection results as alerts."""
    # Show missing policy warnings first
    if missing_policies:
        content = f"**⚠️ Missing or Invalid Policy IDs for {len(missing_policies)} detector(s):**\n\n"
        for policy in missing_policies:
            detector_info = INPUT_DETECTORS.get(policy['detector']) or OUTPUT_DETECTORS.get(policy['detector'])
            icon = detector_info['icon'] if detector_info else "🔧"
            name = detector_info['name'] if detector_info else policy['detector']
            content += f"- {icon} **{name}**: `{policy['env_var']}` = `{policy['current_value']}`\n"
        content += "\nPlease configure these in your `.env` file"
        st.markdown(f"<div class='detector-alert detector-warning'>{content}</div>", unsafe_allow_html=True)
    
    if not detections:
        st.markdown(
            f"<div class='detector-alert detector-warning'>⚠️ **No detector results available** (Selected: {total_selected})</div>",
            unsafe_allow_html=True
        )
        return
    
    violations = [d for d in detections if d.detected]
    total_checked = len(detections)
    
    if violations:
        content = f"**⚠️ {direction} Violations Detected: {len(violations)}/{total_checked} detectors triggered**\n\n"
        for detection in violations:
            detector_info = INPUT_DETECTORS.get(detection.name) or OUTPUT_DETECTORS.get(detection.name)
            icon = detector_info['icon'] if detector_info else "🚨"
            name = detector_info['name'] if detector_info else detection.name
            content += f"- {icon} **{name}** (Score: {detection.score:.2f})\n"
        st.markdown(f"<div class='detector-alert detector-danger'>{content}</div>", unsafe_allow_html=True)


def get_llm_response(messages: List[Dict]) -> str:
    """
    Get response from HuggingFace LLM.
    
    Args:
        messages: List of message dictionaries with role and content
    
    Returns:
        LLM response text
    """
    if not st.session_state.hf_api_key:
        return "Error: HuggingFace API key not configured. Please add it in the sidebar."
    
    try:
        client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=st.session_state.hf_api_key,
        )
        print(st.session_state.selected_model)
        completion = client.chat.completions.create(
            model=st.session_state.selected_model,
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )
        
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error getting LLM response: {str(e)}"


def render_chat_interface():
    """Render the main chat interface."""
    st.title("🤖 Guardrails Chatbot")
    st.caption("Chat with AI while monitoring for policy violations")
    
    # Show current detector configuration
    col1, col2, col3 = st.columns(3)
    with col1:
        input_count = len(st.session_state.selected_input_detectors)
        st.metric("Input Detectors", input_count, help="Number of enabled input detectors")
    with col2:
        output_count = len(st.session_state.selected_output_detectors)
        st.metric("Output Detectors", output_count, help="Number of enabled output detectors")
    with col3:
        api_status = "✅ Ready" if st.session_state.hf_api_key and st.session_state.ibm_api_key else "⚠️ Missing Keys"
        st.metric("API Status", api_status)
    
    st.divider()
    
    # Display chat messages
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            st.markdown(f"<div class='chat-message user-message'>", unsafe_allow_html=True)
            st.markdown("**👤 You:**")
            st.markdown(content)
            
            # Show translation info if available
            if message.get("translated_text"):
                st.info(f"🌐 Detected: **{message.get('source_language')}** - Analyzed translated text")
                with st.expander("📄 View Translated Text"):
                    st.markdown(message.get("translated_text"))
            elif message.get("translation_error") and message.get("source_language") and message.get("source_language").lower() != "english":
                # Only show translation error if text was detected as non-English
                st.warning(f"⚠️ Translation warning: {message.get('translation_error')}")
            
            # Show input detection results if available
            if "input_detections" in message:
                total_selected = message.get("total_input_detectors", len(st.session_state.selected_input_detectors))
                missing_policies = message.get("missing_input_policies", [])
                render_detection_results(message["input_detections"], "Input", total_selected, missing_policies)
                
                # Show error if check failed
                if message.get("input_error"):
                    st.error(f"Error: {message['input_error']}")
                
                # Show debug info if enabled
                if st.session_state.debug_mode:
                    with st.expander("🔍 Debug: Input Check Details"):
                        st.write(f"**Selected Detectors:** {total_selected}")
                        st.write(f"**Check Success:** {message.get('input_check_success', 'Unknown')}")
                        if message.get("input_detections"):
                            st.write("**Detector Results:**")
                            for det in message["input_detections"]:
                                st.write(f"- {det.name}: detected={det.detected}, score={det.score}")
                                if det.details:
                                    st.json(det.details)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        elif role == "assistant":
            st.markdown(f"<div class='chat-message assistant-message'>", unsafe_allow_html=True)
            st.markdown("**🤖 Assistant:**")
            
            # Check if this is a warning message about violations
            if content.startswith("⚠️ Your message triggered guardrail violations"):
                st.markdown(f"<div class='detector-alert detector-warning'>{content}</div>", unsafe_allow_html=True)
            else:
                # Extract thinking process and actual response
                import re
                think_pattern = r'<think>(.*?)</think>'
                think_matches = re.findall(think_pattern, content, re.DOTALL)
                
                if think_matches:
                    # Remove <think>...</think> sections from content
                    clean_content = re.sub(think_pattern, '', content, flags=re.DOTALL).strip()
                    
                    # Display clean content
                    st.markdown(clean_content)
                    
                    # Show thinking process in expandable section
                    with st.expander("💭 View Thinking Process"):
                        for i, think_content in enumerate(think_matches, 1):
                            if len(think_matches) > 1:
                                st.markdown(f"**Thought {i}:**")
                            st.markdown(think_content.strip())
                            if i < len(think_matches):
                                st.markdown("---")
                else:
                    # No thinking tags, display content as-is
                    st.markdown(content)
            
            # Show output detection results if available
            if "output_detections" in message:
                total_selected = message.get("total_output_detectors", len(st.session_state.selected_output_detectors))
                missing_policies = message.get("missing_output_policies", [])
                render_detection_results(message["output_detections"], "Output", total_selected, missing_policies)
                
                # Show error if check failed
                if message.get("output_error"):
                    st.error(f"Error: {message['output_error']}")
                
                # Show debug info if enabled
                if st.session_state.debug_mode:
                    with st.expander("🔍 Debug: Output Check Details"):
                        st.write(f"**Selected Detectors:** {total_selected}")
                        st.write(f"**Check Success:** {message.get('output_check_success', 'Unknown')}")
                        if message.get("output_detections"):
                            st.write("**Detector Results:**")
                            for det in message["output_detections"]:
                                st.write(f"- {det.name}: detected={det.detected}, score={det.score}")
                                if det.details:
                                    st.json(det.details)
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Check if any detectors are selected
        if not st.session_state.selected_input_detectors:
            st.warning("⚠️ No input detectors selected. Enable detectors in the sidebar.")
        
        # Check input with guardrails (with translation if enabled)
        input_check_result = check_text_with_guardrails(
            user_input,
            Direction.INPUT,
            st.session_state.selected_input_detectors,
            enable_translation=True
        )
        
        # Add user message to chat with metadata
        user_message = {
            "role": "user",
            "content": user_input,
            "input_detections": input_check_result.get("detections", []),
            "total_input_detectors": len(st.session_state.selected_input_detectors),
            "input_check_success": input_check_result.get("success", False),
            "input_error": input_check_result.get("error"),
            "missing_input_policies": input_check_result.get("missing_policies", []),
            "translated_text": input_check_result.get("translated_text"),
            "source_language": input_check_result.get("source_language"),
            "translation_error": input_check_result.get("translation_error")
        }
        st.session_state.messages.append(user_message)
        
        # Show error if check failed
        if not input_check_result.get("success", False):
            error_msg = input_check_result.get("error", "Unknown error")
            warning_message = {
                "role": "assistant",
                "content": f"❌ **Error checking input:** {error_msg}",
                "output_detections": []
            }
            st.session_state.messages.append(warning_message)
            st.rerun()
        
        # Check if input has violations
        if input_check_result.get("has_violations", False):
            # Add warning message
            warning_message = {
                "role": "assistant",
                "content": "⚠️ Your message triggered guardrail violations and cannot be processed. Please rephrase your message.",
                "output_detections": []
            }
            st.session_state.messages.append(warning_message)
            st.rerun()
        
        # Set flag to process response and rerun to show user message immediately
        st.session_state.processing_response = True
        st.rerun()
    
    # Process LLM response if flag is set
    if st.session_state.processing_response:
        st.session_state.processing_response = False
        
        # Prepare messages for LLM
        llm_messages = [{"role": "system", "content": st.session_state.system_prompt}]
        for msg in st.session_state.messages:
            if msg["role"] in ["user", "assistant"]:
                llm_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Get LLM response
        with st.spinner("🤔 Thinking..."):
            assistant_response = get_llm_response(llm_messages)
        
        # Validate response is not empty
        if not assistant_response or not assistant_response.strip():
            assistant_response = "Error: Received empty response from the model. Please try again."
            output_check_result = {
                "success": False,
                "error": "Empty response from LLM",
                "detections": [],
                "missing_policies": []
            }
        else:
            # Check output with guardrails
            if not st.session_state.selected_output_detectors:
                st.info("ℹ️ No output detectors selected. Response will not be checked.")
            
            output_check_result = check_text_with_guardrails(
                assistant_response,
                Direction.OUTPUT,
                st.session_state.selected_output_detectors,
                enable_translation=False  # Don't translate output
            )
        
        # Add assistant message to chat with metadata
        assistant_message = {
            "role": "assistant",
            "content": assistant_response,
            "output_detections": output_check_result.get("detections", []),
            "total_output_detectors": len(st.session_state.selected_output_detectors),
            "output_check_success": output_check_result.get("success", False),
            "output_error": output_check_result.get("error"),
            "missing_output_policies": output_check_result.get("missing_policies", [])
        }
        st.session_state.messages.append(assistant_message)
        
        st.rerun()


def main():
    """Main application entry point."""
    apply_custom_css()
    render_sidebar()
    render_chat_interface()


if __name__ == "__main__":
    main()

# Made with Bob
