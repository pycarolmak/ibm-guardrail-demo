import os
import re
from pathlib import Path
from guardrails_client import GuardrailsClient, Direction
from translation_client import TranslationClient, get_cached_translation
# Load environment variables manually
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

# Initialize client
client = GuardrailsClient()

# Mapping filename -> detector_name
INPUT_MAPPING = {
    "bias.md": "social_bias",
    "hap.md": "hap",
    "harm.md": "harm",
    "jailbreak.md": "jailbreak",
    "keywords.md": "keyword",
    "pii.md": "pii",
    "profanity.md": "profanity",
    "prompt_safety_risk.md": "prompt_safety_risk",
    "regex.md": "regex",
    "sexual.md": "sexual_content",
    "topic_relevance.md": "topic_relevance",
    "unethical.md": "unethical_behavior",
    "violence.md": "violence"
}

OUTPUT_MAPPING = {
    "answer_relevance.md": "answer_relevance",
    "biased.md": "social_bias",
    "context_relevance.md": "context_relevance",
    "groundedness.md": "groundedness",
    "harmful.md": "harm",
    "hateful.md": "hap",
    "pii_leak.md": "pii",
    "profane.md": "profanity",
    "sexual.md": "sexual_content",
    "unethical.md": "unethical_behavior",
    "violent.md": "violence"
}

def load_sample(file_path):
    content = file_path.read_text(encoding="utf-8")
    data = {"file": file_path.name}
    
    # English Text
    text_match = re.search(r"## Sample Text\s*\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
    if text_match:
        data["text"] = text_match.group(1).strip()
        
    # Cantonese Text
    cantonese_match = re.search(r"## Sample Text \(Cantonese\)\s*\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
    if cantonese_match:
        data["text_cantonese"] = cantonese_match.group(1).strip()
        
    # Extra params
    # Extra params
    pm = re.search(r"## System Prompt\s*\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
    if pm: data["system_prompt"] = pm.group(1).strip()
        
    cm = re.search(r"## Context\s*\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
    if cm: data["context"] = cm.group(1).strip()
        
    uim = re.search(r"## User Input\s*\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
    if uim: data["user_input"] = uim.group(1).strip()

    return data

def test_detector(text, detector_name, direction, extra_params={}):
    # Prepare params
    detectors_config = {detector_name: {}}
    
    # Add specific params for stateful detectors
    if detector_name == "topic_relevance":
        detectors_config[detector_name]["system_prompt"] = extra_params.get("system_prompt", "You are a helpful assistant.")
    elif detector_name == "prompt_safety_risk":
         detectors_config[detector_name]["system_prompt"] = extra_params.get("system_prompt", "You are a helpful assistant.")
    elif detector_name == "groundedness":
        # Wrap context in list if string
        ctx = extra_params.get("context", "")
        detectors_config[detector_name]["context"] = [ctx] if isinstance(ctx, str) else ctx
        detectors_config[detector_name]["context_type"] = "docs"
    elif detector_name == "context_relevance":
        ctx = extra_params.get("context", "")
        detectors_config[detector_name]["context"] = [ctx] if isinstance(ctx, str) else ctx
        detectors_config[detector_name]["context_type"] = "docs"
    elif detector_name == "answer_relevance":
        detectors_config[detector_name]["prompt"] = extra_params.get("user_input", "")
        detectors_config[detector_name]["generated_text"] = text 
        
    # Call individual test method (checking just this detector)
    results, _ = client.test_detectors_individually(text, direction, detectors_config)
    
    for r in results:
        if r.name == detector_name:
            if r.detected:
                return "DETECTED"
            else:
                return "PASS"
                
    return "UNKNOWN"

def main():
    print(f"{'File':<25} {'Lang':<10} {'Detector':<20} {'Result':<10}")
    print("-" * 70)

    # Initialize Translation Client
    try:
        translator = TranslationClient()
    except Exception as e:
        print(f"Warning: Failed to initialize TranslationClient: {e}")
        translator = None
    
    # Process Inputs
    for f in sorted(Path("samples/input").glob("*.md")):
        if f.name in INPUT_MAPPING:
            data = load_sample(f)
            detector = INPUT_MAPPING[f.name]
            
            # English
            if "text" in data:
                res = test_detector(data["text"], detector, Direction.INPUT, data)
                print(f"{f.name:<25} {'EN':<10} {detector:<20} {res:<10}")
            
            # Cantonese
            if "text_cantonese" in data:
                text_to_test = data["text_cantonese"]
                if translator:
                    trans_result = get_cached_translation(text_to_test, translator)
                    if trans_result.success:
                        text_to_test = trans_result.translated_text
                
                res = test_detector(text_to_test, detector, Direction.INPUT, data)
                print(f"{f.name:<25} {'CN':<10} {detector:<20} {res:<10}")

    # Process Outputs
    for f in sorted(Path("samples/output").glob("*.md")):
        if f.name in OUTPUT_MAPPING:
            data = load_sample(f)
            detector = OUTPUT_MAPPING[f.name]
             
             # English
            if "text" in data:
                res = test_detector(data["text"], detector, Direction.OUTPUT, data)
                print(f"{f.name:<25} {'EN':<10} {detector:<20} {res:<10}")
            
            # Cantonese
            if "text_cantonese" in data:
                text_to_test = data["text_cantonese"]
                if translator:
                    trans_result = get_cached_translation(text_to_test, translator)
                    if trans_result.success:
                        text_to_test = trans_result.translated_text

                res = test_detector(text_to_test, detector, Direction.OUTPUT, data)
                print(f"{f.name:<25} {'CN':<10} {detector:<20} {res:<10}")

if __name__ == "__main__":
    main()
