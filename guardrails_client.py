"""
IBM watsonx Guardrails API Client
Handles communication with the Guardrails enforcement API.
"""

import os
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class Direction(str, Enum):
    """Direction of text flow for guardrail checking."""
    INPUT = "input"
    OUTPUT = "output"


@dataclass
class DetectionResult:
    """Result from a single detector."""
    name: str
    detected: bool
    score: float
    details: Optional[List[Dict]] = None


@dataclass
class GuardrailResult:
    """Complete result from guardrail enforcement."""
    success: bool
    original_text: str
    processed_text: str
    direction: str
    detections: List[DetectionResult]
    has_violations: bool
    total_detectors: int
    succeeded_detectors: int
    failed_detectors: int
    error_message: Optional[str] = None
    raw_response: Optional[Dict] = None


# Detector definitions by direction
INPUT_DETECTORS = {
    "pii": {
        "name": "PII Detection",
        "description": "Personally Identifiable Information (emails, phones, SSN, etc.)",
        "icon": "🔒",
        "has_params": False
    },
    "topic_relevance": {
        "name": "Topic Relevance",
        "description": "Check if input is relevant to the system prompt topic",
        "icon": "🎯",
        "has_params": True,
        "params": ["system_prompt"]
    },
    "prompt_safety_risk": {
        "name": "Prompt Safety Risk",
        "description": "Detect risky prompts based on system context",
        "icon": "⚡",
        "has_params": True,
        "params": ["system_prompt"]
    },
    "harm": {
        "name": "Harm Detection",
        "description": "Harmful or dangerous content",
        "icon": "⚠️",
        "has_params": False
    },
    "jailbreak": {
        "name": "Jailbreak Detection",
        "description": "Prompt injection or jailbreak attempts",
        "icon": "🚫",
        "has_params": False
    },
    "social_bias": {
        "name": "Social Bias",
        "description": "Social bias and discrimination",
        "icon": "⚖️",
        "has_params": False
    },
    "profanity": {
        "name": "Profanity",
        "description": "Profane or vulgar language",
        "icon": "🤬",
        "has_params": False
    },
    "sexual_content": {
        "name": "Sexual Content",
        "description": "Sexually explicit content",
        "icon": "🔞",
        "has_params": False
    },
    "unethical_behavior": {
        "name": "Unethical Behavior",
        "description": "Unethical or illegal behavior",
        "icon": "⛔",
        "has_params": False
    },
    "violence": {
        "name": "Violence",
        "description": "Violent content or threats",
        "icon": "💢",
        "has_params": False
    },
    "hap": {
        "name": "HAP",
        "description": "Hate, Abuse, and Profanity combined",
        "icon": "😠",
        "has_params": False
    }
}

OUTPUT_DETECTORS = {
    "pii": {
        "name": "PII Detection",
        "description": "Personally Identifiable Information (emails, phones, SSN, etc.)",
        "icon": "🔒",
        "has_params": False
    },
    "harm": {
        "name": "Harm Detection",
        "description": "Harmful or dangerous content",
        "icon": "⚠️",
        "has_params": False
    },
    "jailbreak": {
        "name": "Jailbreak Detection",
        "description": "Prompt injection or jailbreak attempts",
        "icon": "🚫",
        "has_params": False
    },
    "social_bias": {
        "name": "Social Bias",
        "description": "Social bias and discrimination",
        "icon": "⚖️",
        "has_params": False
    },
    "profanity": {
        "name": "Profanity",
        "description": "Profane or vulgar language",
        "icon": "🤬",
        "has_params": False
    },
    "sexual_content": {
        "name": "Sexual Content",
        "description": "Sexually explicit content",
        "icon": "🔞",
        "has_params": False
    },
    "unethical_behavior": {
        "name": "Unethical Behavior",
        "description": "Unethical or illegal behavior",
        "icon": "⛔",
        "has_params": False
    },
    "violence": {
        "name": "Violence",
        "description": "Violent content or threats",
        "icon": "💢",
        "has_params": False
    },
    "hap": {
        "name": "HAP",
        "description": "Hate, Abuse, and Profanity combined",
        "icon": "😠",
        "has_params": False
    },
    "groundedness": {
        "name": "Groundedness",
        "description": "Check if response is grounded in provided context",
        "icon": "📚",
        "has_params": True,
        "params": ["context_type", "context"]
    },
    "context_relevance": {
        "name": "Context Relevance",
        "description": "Check if response is relevant to the context",
        "icon": "🔗",
        "has_params": True,
        "params": ["context_type", "context"]
    },
    "answer_relevance": {
        "name": "Answer Relevance",
        "description": "Check if answer is relevant to the prompt",
        "icon": "💬",
        "has_params": True,
        "params": ["prompt", "generated_text"]
    }
}


class GuardrailsClient:
    """Client for IBM watsonx Guardrails API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        policy_id: Optional[str] = None,
        inventory_id: Optional[str] = None,
        governance_instance_id: Optional[str] = None
    ):
        """
        Initialize the Guardrails client.
        
        Args:
            api_key: IBM Cloud API key. If not provided, reads from IBM_API_KEY env var.
            base_url: API base URL. Defaults to GUARDRAILS_API_URL env var.
            policy_id: Policy ID. Defaults to POLICY_ID env var.
            inventory_id: Inventory ID. Defaults to INVENTORY_ID env var.
            governance_instance_id: Governance instance ID. Defaults to GOVERNANCE_INSTANCE_ID env var.
        """
        self.api_key = api_key
        self.base_url = base_url or os.getenv(
            "GUARDRAILS_API_URL", 
            "https://api.aiopenscale.cloud.ibm.com"
        )
        self.policy_id = policy_id or os.getenv(
            "POLICY_ID",
            "4af9a4b1-6801-440e-8f81-5254221915cc"
        )
        self.inventory_id = inventory_id or os.getenv(
            "INVENTORY_ID",
            "a65bc085-8137-4293-b505-ac682c99da35"
        )
        self.governance_instance_id = governance_instance_id or os.getenv(
            "GOVERNANCE_INSTANCE_ID",
            "90e1f320-a1aa-4527-b4d9-1a9ad75d2182"
        )
    
    @property
    def endpoint(self) -> str:
        """Get the full API endpoint URL."""
        return f"{self.base_url}/guardrails-manager/v1/enforce/{self.policy_id}"
    
    def _get_bearer_token(self) -> str:
        """Get a bearer token using the configured API key."""
        if self.api_key:
            # Use provided API key
            from token_manager import TokenManager
            mgr = TokenManager(api_key=self.api_key)
            return f"Bearer {mgr.get_token()}"
        else:
            # Use default from env
            from token_manager import get_bearer_token
            return get_bearer_token()
    
    def enforce(
        self,
        text: str,
        direction: Direction = Direction.INPUT,
        detectors: Optional[Dict[str, Dict]] = None
    ) -> GuardrailResult:
        """
        Enforce guardrail policy on the provided text.
        
        Args:
            text: Text content to check.
            direction: Direction of text flow (input or output).
            detectors: Custom detector configuration.
            
        Returns:
            GuardrailResult with detection results.
        """
        # Build complete detector list - ALL policy detectors must be included
        # Start with required detectors based on direction
        if direction == Direction.INPUT or direction == "input":
            # All input detectors with their required default params
            all_detectors = {
                "pii": {},
                "harm": {},
                "jailbreak": {},
                "social_bias": {},
                "profanity": {},
                "sexual_content": {},
                "unethical_behavior": {},
                "violence": {},
                "hap": {},
                # These are required by the policy - include with defaults
                "topic_relevance": {"system_prompt": "You are a helpful AI assistant."},
                "prompt_safety_risk": {"system_prompt": "You are a helpful AI assistant."}
            }
        else:
            # All output detectors with their required default params
            all_detectors = {
                "pii": {},
                "harm": {},
                "jailbreak": {},
                "social_bias": {},
                "profanity": {},
                "sexual_content": {},
                "unethical_behavior": {},
                "violence": {},
                "hap": {},
                # Output-specific detectors with defaults
                "groundedness": {"context_type": "docs", "context": []},
                "context_relevance": {"context_type": "docs", "context": []},
                "answer_relevance": {"prompt": "", "generated_text": ""}
            }
        
        # Merge user-provided detectors with defaults
        if detectors is not None:
            all_detectors.update(detectors)
        
        detectors = all_detectors
        
        payload = {
            "text": text,
            "direction": direction.value if isinstance(direction, Direction) else direction,
            "detectors_properties": detectors
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-governance-instance-id": self.governance_instance_id,
            "Authorization": self._get_bearer_token()
        }
        
        try:
            response = requests.post(
                self.endpoint,
                params={"inventory_id": self.inventory_id},
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                return self._parse_success_response(text, direction, response.json())
            else:
                return GuardrailResult(
                    success=False,
                    original_text=text,
                    processed_text=text,
                    direction=direction.value if isinstance(direction, Direction) else direction,
                    detections=[],
                    has_violations=False,
                    total_detectors=0,
                    succeeded_detectors=0,
                    failed_detectors=0,
                    error_message=f"API Error {response.status_code}: {response.text}",
                    raw_response=None
                )
                
        except requests.exceptions.Timeout:
            return GuardrailResult(
                success=False,
                original_text=text,
                processed_text=text,
                direction=direction.value if isinstance(direction, Direction) else direction,
                detections=[],
                has_violations=False,
                total_detectors=0,
                succeeded_detectors=0,
                failed_detectors=0,
                error_message="Request timed out. Please try again.",
                raw_response=None
            )
        except requests.exceptions.RequestException as e:
            return GuardrailResult(
                success=False,
                original_text=text,
                processed_text=text,
                direction=direction.value if isinstance(direction, Direction) else direction,
                detections=[],
                has_violations=False,
                total_detectors=0,
                succeeded_detectors=0,
                failed_detectors=0,
                error_message=f"Request failed: {str(e)}",
                raw_response=None
            )
    
    def _parse_success_response(
        self,
        original_text: str,
        direction: Direction,
        response: Dict[str, Any]
    ) -> GuardrailResult:
        """Parse a successful API response into a GuardrailResult."""
        entity = response.get("entity", {})
        
        # Get processed text from multiple possible locations
        processed_text = response.get("text") or entity.get("text") or original_text
        
        status = entity.get("status", {})
        summary = status.get("summary", {})
        
        # Parse individual detector results
        # Try multiple possible locations per API variations
        detections = []
        results = (
            response.get("detections") or  # Per swagger spec
            entity.get("detections") or  # Wrapped version
            entity.get("results") or  # Alternative
            response.get("results") or  # Another alternative
            {}
        )
        
        for detector_name, detector_data in results.items():
            if isinstance(detector_data, dict):
                # Check for detection - API may use different indicators
                is_detected = detector_data.get("detected", False)
                score = detector_data.get("score", 0.0)
                
                # Get details/entities - these indicate findings
                details = detector_data.get("details") or detector_data.get("entities") or []
                
                # Also check for 'flagged', 'blocked', 'risk_level', etc.
                if not is_detected:
                    is_detected = detector_data.get("flagged", False)
                if not is_detected:
                    is_detected = detector_data.get("blocked", False)
                if not is_detected and detector_data.get("risk_level"):
                    is_detected = detector_data.get("risk_level", "").lower() in ["high", "medium"]
                
                # KEY: If has entities/details, it's a detection (e.g., PII found SSN, email)
                if not is_detected and details and len(details) > 0:
                    is_detected = True
                    score = max(score, 0.9)
                
                # If score is high, consider it detected
                if not is_detected and score > 0.5:
                    is_detected = True
                
                detection = DetectionResult(
                    name=detector_name,
                    detected=is_detected,
                    score=score,
                    details=details if details else None
                )
                detections.append(detection)
        
        # Check if content was blocked/modified by the API
        content_was_blocked = "blocked" in processed_text.lower() or "redacted" in processed_text.lower()
        content_was_modified = processed_text != original_text
        
        # If content was blocked but no detector explicitly flagged it, mark as policy violation
        # This relies entirely on the API's detection - no hardcoded inference
        if (content_was_blocked or content_was_modified) and not any(d.detected for d in detections):
            detections.append(DetectionResult(
                name="content_policy",
                detected=True,
                score=1.0,
                details=[{"reason": "Content was modified or blocked by guardrails policy"}]
            ))
        
        # Determine if there are any violations
        has_violations = any(d.detected for d in detections)
        
        # Count actual violations
        violation_count = sum(1 for d in detections if d.detected)
        
        return GuardrailResult(
            success=True,
            original_text=original_text,
            processed_text=processed_text,
            direction=direction.value if isinstance(direction, Direction) else direction,
            detections=detections,
            has_violations=has_violations,
            total_detectors=summary.get("total_detectors", len(detections)),
            succeeded_detectors=summary.get("succeeded", len(detections)),
            failed_detectors=summary.get("failed", 0),
            error_message=None,
            raw_response=response
        )
    
    def _get_policy_id_for_detector(self, detector_name: str) -> str:
        """Get the specific policy ID for a detector, or fall back to default."""
        # Map detector names to environment variable names
        detector_policy_map = {
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
            "answer_relevance": "POLICY_ID_ANSWER_RELEVANCE"
        }
        
        env_var = detector_policy_map.get(detector_name)
        if env_var:
            policy_id = os.getenv(env_var)
            if policy_id and policy_id != f"your_{detector_name}_policy_id_here":
                return policy_id
        
        # Fall back to default policy
        return self.policy_id
    
    def _get_endpoint_for_detector(self, detector_name: str) -> str:
        """Get the API endpoint for a specific detector's policy."""
        policy_id = self._get_policy_id_for_detector(detector_name)
        return f"{self.base_url}/guardrails-manager/v1/enforce/{policy_id}"

    def test_detectors_individually(
        self,
        text: str,
        direction: Direction = Direction.INPUT,
        selected_detectors: Optional[dict] = None
    ) -> tuple:
        """
        Test each detector INDIVIDUALLY with separate API calls.
        Each detector uses its own policy ID (if configured) for clean testing.
        
        Args:
            text: Text content to check.
            direction: Direction of text flow (input or output).
            selected_detectors: Dict of {detector_name: params} to test individually.
            
        Returns:
            Tuple of (List[DetectionResult], raw_responses_dict)
        """
        if selected_detectors is None:
            selected_detectors = {
                "pii": {},
                "harm": {},
                "profanity": {},
                "violence": {},
                "sexual_content": {},
                "social_bias": {}
            }
        
        # Default params for detectors that need them (used as fallback)
        default_params = {
            "topic_relevance": {"system_prompt": "You are a helpful AI assistant."},
            "prompt_safety_risk": {"system_prompt": "You are a helpful AI assistant."},
            "groundedness": {"context_type": "docs", "context": []},
            "context_relevance": {"context_type": "docs", "context": []},
            "answer_relevance": {"prompt": "", "generated_text": ""}
        }
        
        individual_results = []
        all_responses = {"calls": []}
        
        # Test each detector with a SEPARATE API call using its own policy
        for detector_name, user_params in selected_detectors.items():
            # Get the specific endpoint for this detector's policy
            endpoint = self._get_endpoint_for_detector(detector_name)
            policy_id = self._get_policy_id_for_detector(detector_name)
            
            # Use user-provided params, fall back to defaults if needed
            detector_config = user_params if user_params else default_params.get(detector_name, {})
            
            payload = {
                "text": text,
                "direction": direction.value if isinstance(direction, Direction) else direction,
                "detectors_properties": {
                    detector_name: detector_config
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "x-governance-instance-id": self.governance_instance_id,
                "Authorization": self._get_bearer_token()
            }
            
            call_result = {
                "detector": detector_name,
                "policy_id": policy_id,
                "endpoint": endpoint,
                "payload": payload,
                "response": None
            }
            
            try:
                response = requests.post(
                    endpoint,
                    params={"inventory_id": self.inventory_id},
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                call_result["status_code"] = response.status_code
                
                try:
                    call_result["response"] = response.json()
                except:
                    call_result["response"] = response.text
                
                if response.status_code == 200:
                    data = response.json()
                    entity = data.get("entity", {})
                    processed_text = entity.get("text") or data.get("text") or text
                    
                    # Check if THIS detector blocked/modified the content
                    text_was_blocked = (
                        processed_text != text or 
                        "blocked" in processed_text.lower()
                    )
                    
                    # Check for redaction (text modified but not fully blocked)
                    text_was_redacted = processed_text != text and "blocked" not in processed_text.lower()
                    
                    call_result["blocked"] = text_was_blocked
                    call_result["redacted"] = text_was_redacted
                    call_result["processed_text"] = processed_text
                    
                    if text_was_blocked or text_was_redacted:
                        # This specific detector triggered!
                        individual_results.append(DetectionResult(
                            name=detector_name,
                            detected=True,
                            score=1.0,
                            details=[{
                                "triggered": True,
                                "action": "blocked" if text_was_blocked else "redacted",
                                "original_text": text[:100] + "..." if len(text) > 100 else text,
                                "processed_text": processed_text
                            }]
                        ))
                    else:
                        # This detector passed
                        individual_results.append(DetectionResult(
                            name=detector_name,
                            detected=False,
                            score=0.0,
                            details=[{"triggered": False, "processed_text": processed_text}]
                        ))
                else:
                    # API error for this detector
                    error_msg = call_result.get("response", f"HTTP {response.status_code}")
                    individual_results.append(DetectionResult(
                        name=detector_name,
                        detected=False,
                        score=0.0,
                        details=[{"error": str(error_msg)[:200]}]
                    ))
                    
            except Exception as e:
                call_result["error"] = str(e)
                individual_results.append(DetectionResult(
                    name=detector_name,
                    detected=False,
                    score=0.0,
                    details=[{"error": str(e)}]
                ))
            
            all_responses["calls"].append(call_result)
        
        # Summary
        all_responses["total_calls"] = len(selected_detectors)
        all_responses["detectors_triggered"] = [r.name for r in individual_results if r.detected]
        
        return individual_results, all_responses

    def check_input(self, text: str, detectors: Optional[Dict[str, Dict]] = None) -> GuardrailResult:
        """
        Check user input text for policy violations.
        
        Args:
            text: User input text to check.
            detectors: Optional custom detector configuration.
            
        Returns:
            GuardrailResult with detection results.
        """
        return self.enforce(text, Direction.INPUT, detectors)
    
    def check_output(self, text: str, detectors: Optional[Dict[str, Dict]] = None) -> GuardrailResult:
        """
        Check LLM output text for policy violations.
        
        Args:
            text: LLM-generated text to check.
            detectors: Optional custom detector configuration.
            
        Returns:
            GuardrailResult with detection results.
        """
        return self.enforce(text, Direction.OUTPUT, detectors)


def get_default_config() -> Dict[str, str]:
    """Get default configuration from environment variables."""
    return {
        "api_key": os.getenv("IBM_API_KEY", ""),
        "policy_id": os.getenv("POLICY_ID", "4af9a4b1-6801-440e-8f81-5254221915cc"),
        "inventory_id": os.getenv("INVENTORY_ID", "a65bc085-8137-4293-b505-ac682c99da35"),
        "governance_instance_id": os.getenv("GOVERNANCE_INSTANCE_ID", "90e1f320-a1aa-4527-b4d9-1a9ad75d2182")
    }
