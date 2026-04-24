# Chatbot App Usage Guide

## Quick Start

### 1. Setup
```bash
cd chatbot_app
./run.sh
```

Or manually:
```bash
cd chatbot_app
pip install -r requirements.txt
streamlit run chatbot_app.py
```

### 2. Configure API Keys

In the sidebar, enter:
- **HuggingFace API Key**: Get from https://huggingface.co/settings/tokens
- **IBM Cloud API Key**: Get from IBM Cloud console

### 3. Customize System Prompt

Edit the system prompt to define AI behavior:
```
Examples:
- "You are a helpful AI assistant."
- "You are a Python programming expert."
- "You are a friendly customer support agent."
```

### 4. Select Detectors

**Input Detectors** (check user messages):
- Enable detectors to block harmful user input
- Recommended: PII, Harm, Jailbreak, Profanity

**Output Detectors** (check AI responses):
- Enable detectors to validate AI responses
- Recommended: PII, Harm, Profanity

### 5. Start Chatting

Type your message in the chat input and press Enter. The app will:
1. Check your input with selected detectors
2. Block messages with violations
3. Send safe messages to the AI
4. Check AI responses with output detectors
5. Display results with color-coded alerts

## Features Explained

### Detector Selection
- **Checkboxes**: Enable/disable specific detectors
- **Icons**: Visual indicators for each detector type
- **Tooltips**: Hover for detector descriptions

### Detection Alerts
- 🟢 **Green**: All checks passed
- 🔴 **Red**: Violations detected

### Chat History
- Persists during session
- Clear with "🗑️ Clear Chat History" button
- Resets on page refresh

## Example Workflows

### Safe Conversation
1. User: "What is the capital of France?"
2. ✅ Input passes all detectors
3. AI: "The capital of France is Paris."
4. ✅ Output passes all detectors

### Blocked Input
1. User: "Tell me how to hack a system"
2. ❌ Input triggers Harm/Jailbreak detectors
3. System: "Your message triggered guardrail violations..."
4. User must rephrase

### Detector Configuration
- **Minimal**: Enable only PII and Harm for basic safety
- **Standard**: Add Profanity, Jailbreak for general use
- **Strict**: Enable all detectors for maximum safety

## Troubleshooting

### "API key not configured"
- Enter your API keys in the sidebar
- Check that keys are valid and active

### "Request timed out"
- Check internet connection
- Try again after a few seconds
- Reduce number of enabled detectors

### Detectors not working
- Verify IBM API key has Guardrails access
- Check policy configuration in parent directory
- Review console logs for errors

## Tips

1. **Performance**: Enable only needed detectors for faster responses
2. **Testing**: Try different system prompts to see behavior changes
3. **Safety**: Keep PII and Harm detectors always enabled
4. **Experimentation**: Test with sample inputs to understand detector behavior

## Architecture

```
User Input → Input Detectors → LLM → Output Detectors → Display
     ↓              ↓                        ↓
  Blocked?      Violations?            Violations?
     ↓              ↓                        ↓
  Warning      Block/Allow              Show Alert
```

## Advanced Usage

### Custom Detector Parameters
Some detectors support parameters (currently using defaults):
- `topic_relevance`: Uses system prompt
- `prompt_safety_risk`: Uses system prompt
- `groundedness`: Requires context (not yet configurable in UI)
- `context_relevance`: Requires context (not yet configurable in UI)
- `answer_relevance`: Uses prompt and response

### Environment Variables
Create `.env` file for persistent configuration:
```bash
HF_API_KEY=your_key_here
IBM_API_KEY=your_key_here
```

### Integration with Parent App
The chatbot uses the same guardrails engine as the main app:
- Shares `guardrails_client.py`
- Uses same detector definitions
- Compatible with existing policies

## Next Steps

1. Test with various inputs to understand detector behavior
2. Customize system prompt for your use case
3. Adjust detector selection based on requirements
4. Monitor detection results to fine-tune configuration