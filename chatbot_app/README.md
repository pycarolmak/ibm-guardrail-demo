# Guardrails Chatbot Application

A chat application with IBM watsonx Guardrails integration for real-time content moderation and safety checks.

## Features

- 🤖 **AI Chat Interface**: Chat with HuggingFace LLM (Qwen/Qwen3-8B)
- 🛡️ **Input Guardrails**: Check user messages for policy violations before processing
- 🔍 **Output Guardrails**: Validate AI responses before displaying to users
- ⚙️ **Configurable Detectors**: Enable/disable specific detectors in the sidebar
- 📝 **Custom System Prompts**: Define AI behavior and personality
- 🎨 **Clean UI**: Streamlit-based interface with color-coded detection alerts

## Available Detectors

### Input Detectors
- 🔒 PII Detection - Personally Identifiable Information
- ⚠️ Harm Detection - Harmful or dangerous content
- 🚫 Jailbreak Detection - Prompt injection attempts
- ⚖️ Social Bias - Discrimination and bias
- 🤬 Profanity - Vulgar language
- 🔞 Sexual Content - Explicit content
- ⛔ Unethical Behavior - Illegal activities
- 💢 Violence - Violent content
- 😠 HAP - Hate, Abuse, and Profanity
- 🔑 Keyword - Block specific keywords
- 🔡 Regular Expression - Pattern matching

### Output Detectors
- All input detectors plus:
- 📚 Groundedness - Response grounded in context
- 🔗 Context Relevance - Relevant to context
- 💬 Answer Relevance - Relevant to prompt

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API keys:**
   
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   - `HF_API_KEY`: Your HuggingFace API key
   - `IBM_API_KEY`: Your IBM Cloud API key for Guardrails

3. **Run the application:**
   ```bash
   streamlit run chatbot_app.py
   ```

## Usage

1. **Configure API Keys**: Enter your HuggingFace and IBM Cloud API keys in the sidebar
2. **Set System Prompt**: Customize the AI's behavior using the system prompt field
3. **Select Detectors**: Choose which guardrails to enable for input and output checking
4. **Start Chatting**: Type messages in the chat input and interact with the AI
5. **Monitor Detections**: View real-time alerts when detectors are triggered

## How It Works

1. **User Input**: When you send a message, it's first checked against selected input detectors
2. **Violation Handling**: If violations are detected, the message is blocked and you're prompted to rephrase
3. **LLM Processing**: Safe messages are sent to the HuggingFace LLM with the system prompt
4. **Output Checking**: The AI's response is checked against selected output detectors
5. **Display**: Both the message and detection results are displayed in the chat interface

## Architecture

```
chatbot_app/
├── chatbot_app.py          # Main application
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file

Dependencies:
├── ../guardrails_client.py  # IBM Guardrails API client
└── ../token_manager.py      # IBM Cloud token management
```

## Configuration

### System Prompt
The system prompt defines the AI's behavior. Examples:
- "You are a helpful AI assistant."
- "You are a technical support specialist."
- "You are a creative writing assistant."

### Detector Selection
- **Input Detectors**: Check user messages before processing
- **Output Detectors**: Validate AI responses before display
- Enable only the detectors relevant to your use case for better performance

## Detection Results

Detection results are color-coded:
- 🟢 **Green**: All checks passed
- 🟡 **Yellow**: Warnings detected
- 🔴 **Red**: Violations detected (message blocked)

## Troubleshooting

**API Key Issues:**
- Ensure your HuggingFace API key has access to the Qwen model
- Verify your IBM Cloud API key has Guardrails permissions

**Detector Errors:**
- Check that your IBM Guardrails policy is properly configured
- Ensure the policy ID, inventory ID, and governance instance ID are correct

**Connection Issues:**
- Verify internet connectivity
- Check if API endpoints are accessible
- Review firewall settings

## Notes

- The app uses the HuggingFace Inference API with the Qwen/Qwen3-8B model
- Guardrails checks are performed using IBM watsonx Guardrails API
- Each detector runs independently for accurate violation detection
- Chat history is stored in session state and cleared on page refresh

## License

This application uses IBM watsonx Guardrails and HuggingFace APIs. Ensure you comply with their respective terms of service.