from typing import List, Dict
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

class VerseEnricher:
    """Enriches Bible verses with contextual information using local LLM."""

    def __init__(self, model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"):
        """
        Initialize the enrichment model.

        Args:
            model_name: HuggingFace model to use (default: Qwen2.5-1.5B-Instruct, no auth needed)
        """
        logger.info(f"Loading enrichment model: {model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Determine best dtype for device
        if torch.cuda.is_available():
            dtype = torch.float16
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            dtype = torch.float16
        else:
            dtype = torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=dtype,
            device_map="auto",
            low_cpu_mem_usage=True
        )

        logger.info(f"Enrichment model loaded successfully")

    def enrich_verse(self, reference: str, text: str) -> str:
        """
        Enrich a single verse with contextual information.

        Args:
            reference: Verse reference (e.g., "John 3:16")
            text: Verse text

        Returns:
            Enriched text with themes, concepts, and context
        """
        prompt = f"""Analyze this Bible verse and extract key information:

Reference: {reference}
Verse: "{text}"

Provide:
1. Main themes (2-3 keywords)
2. Key concepts or doctrines
3. Emotional tone
4. Context (who, what, when applicable)

Keep response concise (max 2 sentences)."""

        # Format for Qwen chat template
        messages = [{"role": "user", "content": prompt}]
        formatted = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        self.model_name = "Qwen"  # Store for response parsing

        # Generate enrichment
        inputs = self.tokenizer(formatted, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.3,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        # Decode with special tokens first to find split point
        full_response_with_tokens = self.tokenizer.decode(outputs[0], skip_special_tokens=False)

        # Extract just the model's response (after the prompt)
        # Qwen uses <|im_start|>assistant\n format
        if "<|im_start|>assistant\n" in full_response_with_tokens:
            response = full_response_with_tokens.split("<|im_start|>assistant\n")[-1]
            # Remove end token if present
            if "<|im_end|>" in response:
                response = response.split("<|im_end|>")[0]
            response = response.strip()
        else:
            # Fallback: decode without special tokens and extract after prompt
            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response = full_response[len(formatted):].strip() if len(full_response) > len(formatted) else full_response.strip()

        return response

    def enrich_verses_batch(self, verses: List[tuple], checkpoint_callback=None) -> List[str]:
        """
        Enrich multiple verses one at a time (not batched to avoid losing progress).

        Args:
            verses: List of (reference, text, tags) tuples
            checkpoint_callback: Optional callback(index, enrichment) to save progress

        Returns:
            List of enriched text strings
        """
        enrichments = []
        total = len(verses)

        for i, (reference, text, _tags) in enumerate(verses):
            try:
                enriched = self.enrich_verse(reference, text)
                enrichments.append(enriched)

                # Call checkpoint callback if provided (for saving progress)
                if checkpoint_callback:
                    checkpoint_callback(i, enriched)

                if (i + 1) % 10 == 0:
                    logger.info(f"Enriched {i + 1}/{total} verses...")

            except Exception as e:
                logger.warning(f"Failed to enrich {reference}: {e}")
                # Fallback to empty string (will use original text in embeddings)
                enrichments.append('')

        return enrichments
