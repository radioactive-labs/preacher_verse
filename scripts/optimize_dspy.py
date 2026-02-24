#!/usr/bin/env python3
"""Optimize DSPy signatures using GEPA (Gemini Efficient Prompting Adapter)."""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import dspy
from dspy.teleprompt.gepa import gepa_utils
from backend.dspy.signatures import (
    # V1 (Legacy)
    AnalyzeContext,
    IdentifyVerseContent,
    ANALYZE_EXAMPLES,
    IDENTIFY_EXAMPLES,
    # V2 (New)
    ContainsRelevantVerses,
    IdentifyRelevantVerses,
    CONTAINS_EXAMPLES,
    IDENTIFY_REL_EXAMPLES,
    # Shared
    RankVerses,
    RANK_EXAMPLES,
)
from backend.utils.config import config
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

# Path to store optimized instructions
OPTIMIZED_DIR = Path(__file__).parent.parent / "data" / "optimized_signatures"
OPTIMIZED_DIR.mkdir(parents=True, exist_ok=True)


def get_signature_hash(signature_class):
    """Generate a hash of the signature's input/output fields.

    This helps detect when the signature definition has changed,
    invalidating cached optimizations.
    """
    import hashlib

    # DSPy signatures use model_fields (Pydantic v2)
    # Collect field definitions
    fields_data = []
    for name, field in signature_class.model_fields.items():
        # Include field name, type, field type (input/output), and prefix
        field_type = field.json_schema_extra.get('__dspy_field_type', 'unknown')
        prefix = field.json_schema_extra.get('prefix', '')
        field_info = f"{name}:{field.annotation}:{field_type}:{prefix}"
        fields_data.append(field_info)

    # Sort for consistency
    fields_data.sort()

    # Create hash
    fields_str = "|".join(fields_data)
    return hashlib.sha256(fields_str.encode()).hexdigest()[:16]


def save_optimized_instructions(signature_name: str, result, original_instruction: str, signature_class=None):
    """Save optimized instructions to JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save detailed results with history
    history_file = OPTIMIZED_DIR / f"{signature_name}_history_{timestamp}.json"
    history_data = {
        "signature": signature_name,
        "timestamp": timestamp,
        "original_instruction": original_instruction,
        "best_candidate": result.best_candidate,
        "best_candidate_idx": result.best_idx,
        "total_metric_calls": result.total_metric_calls,
        "num_candidates": result.num_candidates,
    }

    # Add signature hash if provided
    if signature_class:
        history_data["signature_hash"] = get_signature_hash(signature_class)

    with open(history_file, 'w') as f:
        json.dump(history_data, f, indent=2)

    logger.info(f"Saved optimization history to {history_file}")

    # Save current best as active (this is what will be loaded at runtime)
    active_file = OPTIMIZED_DIR / f"{signature_name}.json"
    active_data = {
        "signature": signature_name,
        "optimized_at": timestamp,
        "best_candidate_idx": result.best_idx,
        "total_metric_calls": result.total_metric_calls,
        "instructions": result.best_candidate,
    }

    # Add signature hash if provided
    if signature_class:
        active_data["signature_hash"] = get_signature_hash(signature_class)

    with open(active_file, 'w') as f:
        json.dump(active_data, f, indent=2)

    logger.info(f"Saved active optimized instructions to {active_file}")

    return active_file


def load_optimized_instructions(signature_name: str, signature_class=None):
    """Load optimized instructions if they exist and signature hasn't changed.

    Args:
        signature_name: Name of the signature
        signature_class: The signature class to validate against

    Returns:
        Optimized instructions dict or None if not found/invalid
    """
    active_file = OPTIMIZED_DIR / f"{signature_name}.json"

    if not active_file.exists():
        logger.info(f"No optimized instructions found for {signature_name}")
        return None

    with open(active_file, 'r') as f:
        data = json.load(f)

    # Validate signature hash if signature class provided
    if signature_class and 'signature_hash' in data:
        current_hash = get_signature_hash(signature_class)
        saved_hash = data['signature_hash']

        if current_hash != saved_hash:
            logger.warning(
                f"Signature definition has changed for {signature_name}! "
                f"Saved hash: {saved_hash}, Current hash: {current_hash}. "
                f"Ignoring cached optimization - please re-run optimization."
            )
            return None

    logger.info(f"Loaded optimized instructions for {signature_name} (candidate {data.get('best_candidate_idx', 'unknown')})")
    return data['instructions']


def create_analyze_dataset():
    """Convert ANALYZE_EXAMPLES to DSPy Examples for training."""
    # GEPA needs both inputs and outputs
    return ANALYZE_EXAMPLES


def create_rank_dataset():
    """Convert RANK_EXAMPLES to DSPy Examples for training."""
    return RANK_EXAMPLES


def create_identify_dataset():
    """Convert IDENTIFY_EXAMPLES to DSPy Examples for training."""
    return IDENTIFY_EXAMPLES


def analyze_metric(example, prediction, trace=None):
    """
    Metric for AnalyzeContext signature.

    Returns float between 0-1 indicating quality.
    """
    try:
        # Check if edge case detection is correct
        if example.should_skip != prediction.should_skip:
            # Major error: wrong edge case decision
            return 0.0

        if example.should_skip:
            # Edge case detected - check skip reason
            if example.skip_reason == prediction.skip_reason:
                return 1.0  # Perfect match
            else:
                return 0.5  # Right to skip, wrong reason
        else:
            # Valid context - check theme extraction
            if not prediction.theme:
                return 0.0  # Failed to extract theme

            # Theme should be similar (simplified check)
            example_words = set(example.theme.lower().split())
            pred_words = set(prediction.theme.lower().split())

            # Jaccard similarity
            intersection = len(example_words & pred_words)
            union = len(example_words | pred_words)

            if union == 0:
                return 0.0

            similarity = intersection / union

            # Require at least 50% overlap
            if similarity < 0.5:
                return 0.3
            elif similarity < 0.7:
                return 0.7
            else:
                return 1.0

    except Exception as e:
        logger.error(f"Metric error: {e}")
        return 0.0


def rank_metric(example, prediction, trace=None):
    """
    Metric for RankVerses signature.

    Returns float between 0-1 indicating quality.
    """
    try:
        # Check if same verse was selected
        if example.verse_reference == prediction.verse_reference:
            # Perfect match
            # Also check if relevance score is similar
            score_diff = abs(example.relevance_score - prediction.relevance_score)
            if score_diff <= 10:
                return 1.0
            elif score_diff <= 20:
                return 0.9
            else:
                return 0.8
        else:
            # Different verse selected
            # Still give partial credit if relevance score is reasonable
            if prediction.relevance_score >= 70:
                return 0.3  # Acceptable alternative
            elif prediction.relevance_score >= 50:
                return 0.1  # Marginal
            else:
                return 0.0  # Poor choice

    except Exception as e:
        logger.error(f"Metric error: {e}")
        return 0.0


def identify_metric(example, prediction, trace=None):
    """
    Metric for IdentifyVerseContent signature.

    Returns float between 0-1 indicating quality.
    """
    try:
        score = 0.0

        # Check content type (40% weight)
        if example.content_type == prediction.content_type:
            score += 0.4
        elif prediction.content_type == "none":
            # Severe penalty for missing biblical content
            return 0.0

        # Check biblical entities (30% weight)
        if example.biblical_entities and prediction.biblical_entities:
            example_entities = set(e.strip().lower() for e in example.biblical_entities.split(','))
            pred_entities = set(e.strip().lower() for e in prediction.biblical_entities.split(','))

            if example_entities and pred_entities:
                intersection = len(example_entities & pred_entities)
                union = len(example_entities | pred_entities)
                entity_similarity = intersection / union if union > 0 else 0
                score += 0.3 * entity_similarity

        # Check search queries (30% weight)
        if example.search_queries and prediction.search_queries:
            example_queries = set(q.strip().lower() for q in example.search_queries.split(';'))
            pred_queries = set(q.strip().lower() for q in prediction.search_queries.split(';'))

            # Check for keyword overlap in queries
            example_words = set()
            for q in example_queries:
                example_words.update(q.split())

            pred_words = set()
            for q in pred_queries:
                pred_words.update(q.split())

            if example_words and pred_words:
                intersection = len(example_words & pred_words)
                union = len(example_words | pred_words)
                query_similarity = intersection / union if union > 0 else 0
                score += 0.3 * query_similarity

        return min(score, 1.0)

    except Exception as e:
        logger.error(f"Metric error: {e}")
        return 0.0


def analyze_feedback(predictor_output, predictor_inputs, module_inputs, module_outputs, captured_trace):
    """
    Provide feedback for AnalyzeContext predictor.

    This helps GEPA understand what went wrong.
    """
    score = analyze_metric(module_inputs, module_outputs)

    if score == 1.0:
        feedback = "Perfect prediction - correctly identified edge case status and extracted appropriate theme."
    elif module_inputs.should_skip and not module_outputs.should_skip:
        feedback = f"Failed to detect edge case. This is {module_inputs.skip_reason} content and should be skipped."
    elif not module_inputs.should_skip and module_outputs.should_skip:
        feedback = f"False positive edge case detection. This is valid theological content about '{module_inputs.theme}' and should not be skipped."
    elif module_inputs.should_skip and module_inputs.skip_reason != module_outputs.skip_reason:
        feedback = f"Detected edge case but wrong category. This is {module_inputs.skip_reason}, not {module_outputs.skip_reason}."
    else:
        # Theme extraction issue
        feedback = f"Theme extraction needs improvement. Expected theme focused on '{module_inputs.theme}', got '{module_outputs.theme}'."

    return gepa_utils.ScoreWithFeedback(score=score, feedback=feedback)


def rank_feedback(predictor_output, predictor_inputs, module_inputs, module_outputs, captured_trace):
    """
    Provide feedback for RankVerses predictor.
    """
    score = rank_metric(module_inputs, module_outputs)

    if score >= 0.8:
        feedback = f"Good verse selection. {module_inputs.verse_reference} is the ideal choice for this sermon context."
    elif module_inputs.verse_reference != module_outputs.verse_reference:
        feedback = (
            f"Suboptimal verse selection. Selected {module_outputs.verse_reference} but {module_inputs.verse_reference} "
            f"provides better theological alignment with the sermon's theme."
        )
    else:
        feedback = f"Relevance score calibration needed. Expected {module_inputs.relevance_score}, got {module_outputs.relevance_score}."

    return gepa_utils.ScoreWithFeedback(score=score, feedback=feedback)


def identify_feedback(predictor_output, predictor_inputs, module_inputs, module_outputs, captured_trace):
    """
    Provide feedback for IdentifyVerseContent predictor.
    """
    score = identify_metric(module_inputs, module_outputs)

    if score >= 0.9:
        feedback = "Excellent biblical content identification with accurate entities and search queries."
    elif module_inputs.content_type != module_outputs.content_type:
        feedback = (
            f"Content type mismatch. This is '{module_inputs.content_type}' content, not '{module_outputs.content_type}'. "
            f"Expected entities: {module_inputs.biblical_entities}. Expected queries: {module_inputs.search_queries}"
        )
    elif not module_outputs.biblical_entities and module_inputs.biblical_entities:
        feedback = f"Missing biblical entities. Should identify: {module_inputs.biblical_entities}"
    elif not module_outputs.search_queries and module_inputs.search_queries:
        feedback = f"Missing search queries. Should generate: {module_inputs.search_queries}"
    else:
        feedback = (
            f"Partially correct identification. Improve entity extraction ({module_inputs.biblical_entities}) "
            f"and search query formulation ({module_inputs.search_queries[:100]}...)"
        )

    return gepa_utils.ScoreWithFeedback(score=score, feedback=feedback)


def optimize_analyze_context():
    """Optimize AnalyzeContext signature using GEPA."""
    logger.info("Optimizing AnalyzeContext signature...")

    # Initialize LM with higher token limit for GEPA optimization
    lm = dspy.LM(model="gemini/gemini-2.5-flash", api_key=config.GEMINI_API_KEY, max_tokens=10000)
    dspy.configure(lm=lm)

    # Create student program
    student = dspy.Predict(AnalyzeContext)

    # Prepare dataset
    trainset = create_analyze_dataset()
    logger.info(f"Training with {len(trainset)} examples")

    # Split into train/val
    split_idx = int(len(trainset) * 0.8)
    train_examples = trainset[:split_idx]
    val_examples = trainset[split_idx:]

    logger.info(f"Train: {len(train_examples)}, Val: {len(val_examples)}")

    # Create DSPy adapter
    # Note: Predict names its predictor "self"
    adapter = gepa_utils.DspyAdapter(
        student_module=student,
        metric_fn=analyze_metric,
        feedback_map={"self": analyze_feedback},
        failure_score=0.0,
        num_threads=1
    )

    # Get seed candidate (current instruction)
    seed_candidate = {}
    for name, pred in student.named_predictors():
        seed_candidate[name] = pred.signature.instructions

    logger.info(f"Seed candidate: {seed_candidate}")

    # Run GEPA optimization
    from gepa import optimize

    logger.info("Starting GEPA optimization...")
    result = optimize(
        seed_candidate=seed_candidate,
        trainset=train_examples,
        valset=val_examples,
        adapter=adapter,
        reflection_lm="gemini/gemini-2.5-flash",
        max_metric_calls=50,  # Budget
        reflection_minibatch_size=3,
        candidate_selection_strategy="pareto",
        skip_perfect_score=True,
        perfect_score=1.0,
        seed=42,
        display_progress_bar=True
    )

    logger.info("\n" + "="*60)
    logger.info("GEPA Optimization Complete!")
    logger.info("="*60)
    logger.info(f"Total metric calls: {result.total_metric_calls}")
    logger.info(f"Number of candidates explored: {result.num_candidates}")
    logger.info(f"Best candidate (index {result.best_idx}):")
    for name, instruction in result.best_candidate.items():
        logger.info(f"\n{name}:")
        logger.info(f"{instruction}")
    logger.info("="*60)

    # Save optimized instructions
    original_instruction = seed_candidate.get('predict', '')
    save_optimized_instructions("analyze_context", result, original_instruction, AnalyzeContext)

    return result


def optimize_rank_verses():
    """Optimize RankVerses signature using GEPA."""
    logger.info("Optimizing RankVerses signature...")

    # Initialize LM with higher token limit for GEPA optimization
    lm = dspy.LM(model="gemini/gemini-2.5-flash", api_key=config.GEMINI_API_KEY, max_tokens=10000)
    dspy.configure(lm=lm)

    # Create student program with ChainOfThought
    student = dspy.ChainOfThought(RankVerses)

    # Prepare dataset
    trainset = create_rank_dataset()
    logger.info(f"Training with {len(trainset)} examples")

    # Split into train/val
    split_idx = int(len(trainset) * 0.8)
    train_examples = trainset[:split_idx]
    val_examples = trainset[split_idx:]

    logger.info(f"Train: {len(train_examples)}, Val: {len(val_examples)}")

    # Create DSPy adapter
    # Note: ChainOfThought names its predictor "predict"
    adapter = gepa_utils.DspyAdapter(
        student_module=student,
        metric_fn=rank_metric,
        feedback_map={"predict": rank_feedback},
        failure_score=0.0,
        num_threads=1
    )

    # Get seed candidate
    seed_candidate = {}
    for name, pred in student.named_predictors():
        seed_candidate[name] = pred.signature.instructions

    logger.info(f"Seed candidate: {seed_candidate}")

    # Run GEPA optimization
    from gepa import optimize

    logger.info("Starting GEPA optimization...")
    result = optimize(
        seed_candidate=seed_candidate,
        trainset=train_examples,
        valset=val_examples,
        adapter=adapter,
        reflection_lm="gemini/gemini-2.5-flash",
        max_metric_calls=50,  # Budget
        reflection_minibatch_size=3,
        candidate_selection_strategy="pareto",
        skip_perfect_score=True,
        perfect_score=1.0,
        seed=42,
        display_progress_bar=True
    )

    logger.info("\n" + "="*60)
    logger.info("GEPA Optimization Complete!")
    logger.info("="*60)
    logger.info(f"Total metric calls: {result.total_metric_calls}")
    logger.info(f"Number of candidates explored: {result.num_candidates}")
    logger.info(f"Best candidate (index {result.best_idx}):")
    for name, instruction in result.best_candidate.items():
        logger.info(f"\n{name}:")
        logger.info(f"{instruction}")
    logger.info("="*60)

    # Save optimized instructions
    original_instruction = seed_candidate.get('predict', '')
    save_optimized_instructions("rank_verses", result, original_instruction, RankVerses)

    return result


def optimize_identify_verse_content():
    """Optimize IdentifyVerseContent signature using GEPA."""
    logger.info("Optimizing IdentifyVerseContent signature...")

    # Initialize LM with higher token limit for GEPA optimization
    lm = dspy.LM(model="gemini/gemini-2.5-flash", api_key=config.GEMINI_API_KEY, max_tokens=10000)
    dspy.configure(lm=lm)

    # Create student program with ChainOfThought
    student = dspy.ChainOfThought(IdentifyVerseContent)

    # Prepare dataset
    trainset = create_identify_dataset()
    logger.info(f"Training with {len(trainset)} examples")

    # Split into train/val
    split_idx = int(len(trainset) * 0.8)
    train_examples = trainset[:split_idx]
    val_examples = trainset[split_idx:]

    logger.info(f"Train: {len(train_examples)}, Val: {len(val_examples)}")

    # Create DSPy adapter
    # Note: ChainOfThought names its predictor "predict"
    adapter = gepa_utils.DspyAdapter(
        student_module=student,
        metric_fn=identify_metric,
        feedback_map={"predict": identify_feedback},
        failure_score=0.0,
        num_threads=1
    )

    # Get seed candidate
    seed_candidate = {}
    for name, pred in student.named_predictors():
        seed_candidate[name] = pred.signature.instructions

    logger.info(f"Seed candidate: {seed_candidate}")

    # Run GEPA optimization
    from gepa import optimize

    logger.info("Starting GEPA optimization...")
    result = optimize(
        seed_candidate=seed_candidate,
        trainset=train_examples,
        valset=val_examples,
        adapter=adapter,
        reflection_lm="gemini/gemini-2.5-flash",
        max_metric_calls=50,
        reflection_minibatch_size=3,
        candidate_selection_strategy="pareto",
        skip_perfect_score=True,
        perfect_score=1.0,
        seed=42,
        display_progress_bar=True
    )

    logger.info("\n" + "="*60)
    logger.info("GEPA Optimization Complete!")
    logger.info("="*60)
    logger.info(f"Total metric calls: {result.total_metric_calls}")
    logger.info(f"Number of candidates explored: {result.num_candidates}")
    logger.info(f"Best candidate (index {result.best_idx}):")
    for name, instruction in result.best_candidate.items():
        logger.info(f"\n{name}:")
        logger.info(f"{instruction}")
    logger.info("="*60)

    # Save optimized instructions
    original_instruction = seed_candidate.get('predict', '')
    save_optimized_instructions("identify_verse_content", result, original_instruction, IdentifyVerseContent)

    return result


def contains_metric(example, prediction, trace=None):
    """Metric for ContainsRelevantVerses signature."""
    try:
        # Check if contains_verses decision is correct
        if example.contains_verses != prediction.contains_verses:
            return 0.0

        # Check if retrieval_type is correct
        if example.retrieval_type != prediction.retrieval_type:
            return 0.3

        return 1.0
    except Exception as e:
        logger.error(f"Metric error: {e}")
        return 0.0


def contains_feedback(predictor_output, predictor_inputs, module_inputs, module_outputs, captured_trace):
    """Feedback for ContainsRelevantVerses predictor."""
    score = contains_metric(module_inputs, module_outputs)

    if score == 1.0:
        feedback = "Perfect detection of biblical content and retrieval type."
    elif module_inputs.contains_verses != module_outputs.contains_verses:
        feedback = f"Incorrect biblical content detection. Should be {module_inputs.contains_verses}."
    else:
        feedback = f"Wrong retrieval type. Expected {module_inputs.retrieval_type}, got {module_outputs.retrieval_type}."

    return gepa_utils.ScoreWithFeedback(score=score, feedback=feedback)


def identify_rel_metric(example, prediction, trace=None):
    """Metric for IdentifyRelevantVerses signature."""
    try:
        score = 0.0

        # Check verse_references (50% weight)
        if example.verse_references and prediction.verse_references:
            example_refs = set(r.strip().lower() for r in example.verse_references.split(';'))
            pred_refs = set(r.strip().lower() for r in prediction.verse_references.split(';'))
            if example_refs and pred_refs:
                intersection = len(example_refs & pred_refs)
                union = len(example_refs | pred_refs)
                score += 0.5 * (intersection / union if union > 0 else 0)
        elif not example.verse_references and not prediction.verse_references:
            score += 0.5

        # Check search_queries (50% weight)
        if example.search_queries and prediction.search_queries:
            example_words = set(example.search_queries.lower().split())
            pred_words = set(prediction.search_queries.lower().split())
            if example_words and pred_words:
                intersection = len(example_words & pred_words)
                union = len(example_words | pred_words)
                score += 0.5 * (intersection / union if union > 0 else 0)
        elif not example.search_queries and not prediction.search_queries:
            score += 0.5

        return min(score, 1.0)
    except Exception as e:
        logger.error(f"Metric error: {e}")
        return 0.0


def identify_rel_feedback(predictor_output, predictor_inputs, module_inputs, module_outputs, captured_trace):
    """Feedback for IdentifyRelevantVerses predictor."""
    score = identify_rel_metric(module_inputs, module_outputs)

    if score >= 0.9:
        feedback = "Excellent extraction of verse references and/or search queries."
    elif not module_outputs.verse_references and module_inputs.verse_references:
        feedback = f"Missing verse references. Should extract: {module_inputs.verse_references}"
    elif not module_outputs.search_queries and module_inputs.search_queries:
        feedback = f"Missing search queries. Should generate: {module_inputs.search_queries}"
    else:
        feedback = "Partially correct extraction. Improve reference and query accuracy."

    return gepa_utils.ScoreWithFeedback(score=score, feedback=feedback)


def optimize_contains_relevant_verses():
    """Optimize ContainsRelevantVerses signature using GEPA."""
    logger.info("Optimizing ContainsRelevantVerses signature...")

    lm = dspy.LM(model="gemini/gemini-2.5-flash", api_key=config.GEMINI_API_KEY, max_tokens=10000)
    dspy.configure(lm=lm)

    student = dspy.ChainOfThought(ContainsRelevantVerses)
    trainset = CONTAINS_EXAMPLES

    split_idx = int(len(trainset) * 0.8)
    train_examples = trainset[:split_idx]
    val_examples = trainset[split_idx:]

    logger.info(f"Train: {len(train_examples)}, Val: {len(val_examples)}")

    # Note: ChainOfThought names its predictor "predict"
    adapter = gepa_utils.DspyAdapter(
        student_module=student,
        metric_fn=contains_metric,
        feedback_map={"predict": contains_feedback},
        failure_score=0.0,
        num_threads=1
    )

    seed_candidate = {}
    for name, pred in student.named_predictors():
        seed_candidate[name] = pred.signature.instructions

    from gepa import optimize

    result = optimize(
        seed_candidate=seed_candidate,
        trainset=train_examples,
        valset=val_examples,
        adapter=adapter,
        reflection_lm="gemini/gemini-2.5-flash",
        max_metric_calls=50,
        reflection_minibatch_size=3,
        candidate_selection_strategy="pareto",
        skip_perfect_score=True,
        perfect_score=1.0,
        seed=42,
        display_progress_bar=True
    )

    logger.info("\n" + "="*60)
    logger.info("GEPA Optimization Complete!")
    logger.info("="*60)
    logger.info(f"Best candidate (index {result.best_idx}):")
    for name, instruction in result.best_candidate.items():
        logger.info(f"\n{name}:\n{instruction}")

    original_instruction = seed_candidate.get('self', '')
    save_optimized_instructions("contains_relevant_verses", result, original_instruction, ContainsRelevantVerses)

    return result


def optimize_identify_relevant_verses():
    """Optimize IdentifyRelevantVerses signature using GEPA."""
    logger.info("Optimizing IdentifyRelevantVerses signature...")

    lm = dspy.LM(model="gemini/gemini-2.5-flash", api_key=config.GEMINI_API_KEY, max_tokens=10000)
    dspy.configure(lm=lm)

    student = dspy.ChainOfThought(IdentifyRelevantVerses)
    trainset = IDENTIFY_REL_EXAMPLES

    split_idx = int(len(trainset) * 0.8)
    train_examples = trainset[:split_idx]
    val_examples = trainset[split_idx:]

    logger.info(f"Train: {len(train_examples)}, Val: {len(val_examples)}")

    adapter = gepa_utils.DspyAdapter(
        student_module=student,
        metric_fn=identify_rel_metric,
        feedback_map={"predict": identify_rel_feedback},
        failure_score=0.0,
        num_threads=1
    )

    seed_candidate = {}
    for name, pred in student.named_predictors():
        seed_candidate[name] = pred.signature.instructions

    from gepa import optimize

    result = optimize(
        seed_candidate=seed_candidate,
        trainset=train_examples,
        valset=val_examples,
        adapter=adapter,
        reflection_lm="gemini/gemini-2.5-flash",
        max_metric_calls=50,
        reflection_minibatch_size=3,
        candidate_selection_strategy="pareto",
        skip_perfect_score=True,
        perfect_score=1.0,
        seed=42,
        display_progress_bar=True
    )

    logger.info("\n" + "="*60)
    logger.info("GEPA Optimization Complete!")
    logger.info("="*60)
    logger.info(f"Best candidate (index {result.best_idx}):")
    for name, instruction in result.best_candidate.items():
        logger.info(f"\n{name}:\n{instruction}")

    original_instruction = seed_candidate.get('predict', '')
    save_optimized_instructions("identify_relevant_verses", result, original_instruction, IdentifyRelevantVerses)

    return result


def main():
    """Run GEPA optimization for signatures."""
    import argparse

    parser = argparse.ArgumentParser(description="Optimize DSPy signatures using GEPA")
    parser.add_argument(
        "--signature",
        choices=["analyze", "rank", "identify", "contains", "identify-rel", "v1", "v2", "all"],
        default="v2",
        help="Which signature to optimize (v1=legacy, v2=new, all=both)"
    )

    args = parser.parse_args()

    logger.info("="*60)
    logger.info("DSPy GEPA Optimization")
    logger.info("="*60)

    # V1 signatures (legacy)
    if args.signature in ["analyze", "v1", "all"]:
        optimize_analyze_context()

    if args.signature in ["identify", "v1", "all"]:
        optimize_identify_verse_content()

    # V2 signatures (new)
    if args.signature in ["contains", "v2", "all"]:
        optimize_contains_relevant_verses()

    if args.signature in ["identify-rel", "v2", "all"]:
        optimize_identify_relevant_verses()

    # Shared signature
    if args.signature in ["rank", "v1", "v2", "all"]:
        optimize_rank_verses()

    logger.info("\n✓ Optimization complete!")


if __name__ == "__main__":
    main()
