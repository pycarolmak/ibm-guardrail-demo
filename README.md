# IBM watsonx Guardrails Demo

A Streamlit web application demonstrating IBM watsonx Guardrails capabilities for enterprise AI risk assessment and content moderation.

## Try it Now!

Scan the QR code below to test the live demo:

<div align="center">
  <img src="qrcode.png" alt="QR Code for Live Demo" width="200"/>
  <p><em>Scan with your mobile device to access the demo</em></p>
</div>

## Features

- **Interactive Demo Interface**: Test text against 9+ content detectors
- **Input/Output Modes**: Check both user inputs and LLM-generated responses
- **Real-time Results**: Visual dashboard with color-coded risk indicators
- **PII Redaction**: Automatic masking of personal information
- **Mobile-Friendly**: Responsive design for QR code scanning

## Detectors

| Detector | Description |
|----------|-------------|
| PII | Personal data (emails, phones, SSN) |
| Jailbreak | Prompt injection attempts |
| Harm | Harmful or dangerous content |
| Social Bias | Discrimination and bias |
| Profanity | Vulgar language |
| Sexual Content | Explicit material |
| Unethical Behavior | Illegal activities |
| Violence | Violent content |
| HAP | Hate, Abuse, Profanity |

## Local Development

### Prerequisites

- Python 3.11+
- IBM Cloud API Key

### Setup

1. Clone the repository and navigate to the directory:
   ```bash
   cd guardrails-demo
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your IBM Cloud API key
   ```

5. Run the application:
   ```bash
   streamlit run app.py
   ```

6. Open http://localhost:8501 in your browser.

## IBM Cloud Code Engine Deployment

### Prerequisites

- IBM Cloud CLI installed
- IBM Cloud Code Engine plugin installed
- Container registry (IBM Container Registry or Docker Hub)

### Deployment Steps

1. **Login to IBM Cloud:**
   ```bash
   ibmcloud login
   # Or use SSO if required:
   ibmcloud login --sso
   ```

2. **Select or create a Code Engine project:**
   ```bash
   # List available projects
   ibmcloud ce project list

   # Select your project
   ibmcloud ce project select -n YOUR_PROJECT_NAME

   # If you don't have a project, create one first:
   ibmcloud ce project create --name guardrails-demo-project
   ```

3. **Deploy from source (no Docker required):**
   ```bash
   cd guardrails-demo
   
   ibmcloud ce app create \
     --name guardrails-demo \
     --build-source . \
     --strategy dockerfile \
     --port 8501 \
     --min-scale 0 \
     --max-scale 3 \
     --env IBM_API_KEY=your_api_key_here \
     --env POLICY_ID_PII=your_pii_policy_id \
     --env INVENTORY_ID=your_inventory_id \
     --env GOVERNANCE_INSTANCE_ID=your_instance_id
   ```

4. **Alternative: Build and push Docker image manually (requires Docker):**
   ```bash
   docker build -t us.icr.io/your-namespace/guardrails-demo:latest .
   docker push us.icr.io/your-namespace/guardrails-demo:latest
   
   ibmcloud ce app create \
     --name guardrails-demo \
     --image us.icr.io/your-namespace/guardrails-demo:latest \
     --port 8501
   ```

5. **Get the application URL:**
   ```bash
   ibmcloud ce app get --name guardrails-demo --output url
   ```

### Using Secrets (Recommended)

For production, use secrets instead of environment variables:

```bash
# Create a secret for the API key
ibmcloud ce secret create --name guardrails-secrets \
  --from-literal IBM_API_KEY=your_api_key_here

# Update the app to use the secret
ibmcloud ce app update --name guardrails-demo \
  --env-from-secret guardrails-secrets
```

## QR Code Generation

Once deployed, generate a QR code for the application URL:

```bash
# Using qrencode (install via: brew install qrencode or apt install qrencode)
qrencode -o qrcode.png "https://your-app-url.us-east.codeengine.appdomain.cloud"
```

Or use online QR code generators like:
- https://www.qr-code-generator.com/
- https://www.the-qrcode-generator.com/

## Project Structure

```
guardrails-demo/
├── app.py                 # Main Streamlit application
├── guardrails_client.py   # IBM Guardrails API client
├── token_manager.py       # IBM IAM token management
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container configuration
├── .env.example           # Environment variable template
├── .dockerignore          # Docker ignore rules
├── .ceignore              # Code Engine ignore rules
├── .streamlit/
│   └── config.toml        # Streamlit theme configuration
├── samples/               # Sample texts for testing
│   ├── input/             # Input detector samples
│   └── output/            # Output detector samples
└── test/
    └── test_cases.md      # Comprehensive test cases (EN/Cantonese)
```

## License

This demo is for educational and demonstration purposes.

---

Powered by **IBM watsonx.governance**

