"""
Recovery utilities for resuming audiobook generation from assembly phase.
Allows skipping line segment regeneration when they already exist.
"""

import os
import json
import glob
from typing import Dict, List, Tuple, Optional
from utils.audiobook_utils import validate_file_path
from utils.file_utils import sanitize_filename

def create_recovery_checkpoint(temp_audio_dir: str, chapter_line_map: Dict, chapter_files: List, results: List) -> None:
    """
    Creates a recovery checkpoint file with the current state.
    
    Args:
        temp_audio_dir (str): Directory containing temporary audio files
        chapter_line_map (Dict): Mapping of chapters to their line indices
        chapter_files (List): List of chapter filenames
        results (List): List of results from line generation
    """
    checkpoint_data = {
        "chapter_line_map": chapter_line_map,
        "chapter_files": chapter_files,
        "total_lines": len(results),
        "results_metadata": [
            {
                "index": r["index"],
                "line": r["line"],
                "is_chapter_heading": r["is_chapter_heading"]
            } for r in results
        ]
    }
    
    checkpoint_path = os.path.join(temp_audio_dir, "recovery_checkpoint.json")
    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
    
    print(f"Recovery checkpoint created at: {checkpoint_path}")

def load_recovery_checkpoint(temp_audio_dir: str) -> Optional[Dict]:
    """
    Loads a recovery checkpoint if it exists.
    
    Args:
        temp_audio_dir (str): Directory containing temporary audio files
        
    Returns:
        Dict or None: Checkpoint data if exists and valid, None otherwise
    """
    checkpoint_path = os.path.join(temp_audio_dir, "recovery_checkpoint.json")
    
    if not os.path.exists(checkpoint_path):
        return None
        
    try:
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load recovery checkpoint: {e}")
        return None

def validate_line_segments(temp_line_audio_dir: str, expected_line_count: int) -> Tuple[bool, List[int]]:
    """
    Validates that all expected line segment audio files exist.
    
    Args:
        temp_line_audio_dir (str): Directory containing line audio segments
        expected_line_count (int): Number of lines expected
        
    Returns:
        Tuple[bool, List[int]]: (all_present, missing_indices)
    """
    if not os.path.exists(temp_line_audio_dir):
        return False, list(range(expected_line_count))
    
    missing_indices = []
    
    for i in range(expected_line_count):
        line_file = os.path.join(temp_line_audio_dir, f"line_{i:06d}.wav")
        if not os.path.exists(line_file) or os.path.getsize(line_file) == 0:
            missing_indices.append(i)
    
    return len(missing_indices) == 0, missing_indices

def can_resume_from_assembly(temp_audio_dir: str, temp_line_audio_dir: str) -> Tuple[bool, Optional[Dict]]:
    """
    Checks if the audiobook generation can be resumed from the assembly phase.
    
    Args:
        temp_audio_dir (str): Directory containing temporary audio files
        temp_line_audio_dir (str): Directory containing line audio segments
        
    Returns:
        Tuple[bool, Optional[Dict]]: (can_resume, checkpoint_data)
    """
    # Load checkpoint data
    checkpoint_data = load_recovery_checkpoint(temp_audio_dir)
    if not checkpoint_data:
        return False, None
    
    # Validate that all line segments exist
    expected_lines = checkpoint_data.get("total_lines", 0)
    all_present, missing = validate_line_segments(temp_line_audio_dir, expected_lines)
    
    if not all_present:
        print(f"Cannot resume: Missing {len(missing)} line segments out of {expected_lines}")
        return False, None
    
    print(f"✅ All {expected_lines} line segments found. Can resume from assembly phase.")
    return True, checkpoint_data

def cleanup_partial_chapters(temp_audio_dir: str, chapter_files: List[str]) -> None:
    """
    Removes any partially created chapter files to ensure clean assembly.
    
    Args:
        temp_audio_dir (str): Directory containing temporary audio files
        chapter_files (List[str]): List of chapter filenames to clean up
    """
    for chapter_file in chapter_files:
        chapter_path = os.path.join(temp_audio_dir, chapter_file)
        if os.path.exists(chapter_path):
            try:
                os.remove(chapter_path)
                print(f"Removed partial chapter file: {chapter_file}")
            except OSError as e:
                print(f"Warning: Could not remove {chapter_file}: {e}")
    
    # Also clean up any temporary files
    temp_patterns = [
        os.path.join(temp_audio_dir, "chapter_list_*.txt"),
        os.path.join(temp_audio_dir, "*.temp.wav"),
        os.path.join(temp_audio_dir, "*.concat_list.txt")
    ]
    
    for pattern in temp_patterns:
        for temp_file in glob.glob(pattern):
            try:
                os.remove(temp_file)
                print(f"Removed temp file: {os.path.basename(temp_file)}")
            except OSError:
                pass

def resume_from_assembly_phase(temp_audio_dir: str, temp_line_audio_dir: str, 
                             checkpoint_data: Dict) -> Tuple[List[str], Dict]:
    """
    Resumes audiobook generation from the assembly phase using checkpoint data.
    
    Args:
        temp_audio_dir (str): Directory containing temporary audio files
        temp_line_audio_dir (str): Directory containing line audio segments
        checkpoint_data (Dict): Recovery checkpoint data
        
    Returns:
        Tuple[List[str], Dict]: (chapter_files, chapter_line_map)
    """
    chapter_files = checkpoint_data["chapter_files"]
    chapter_line_map = checkpoint_data["chapter_line_map"]
    
    # Clean up any partial chapter files before resuming
    cleanup_partial_chapters(temp_audio_dir, chapter_files)
    
    print(f"🔄 Resuming from assembly phase with {len(chapter_files)} chapters")
    return chapter_files, chapter_line_map

def create_recovery_enabled_generator(original_generator_func):
    """
    Decorator to add recovery capabilities to an audiobook generation function.
    
    Args:
        original_generator_func: The original generator function to wrap
        
    Returns:
        Wrapped generator function with recovery capabilities
    """
    async def wrapped_generator(*args, **kwargs):
        # Extract common parameters (adjust based on your function signature)
        temp_audio_dir = "temp_audio"
        temp_line_audio_dir = os.path.join(temp_audio_dir, "line_segments")
        
        # Check if we can resume from assembly phase
        can_resume, checkpoint_data = can_resume_from_assembly(temp_audio_dir, temp_line_audio_dir)
        
        if can_resume:
            yield "🔄 **Recovery Mode**: Found existing line segments, resuming from assembly phase..."
            
            # Skip to assembly phase
            chapter_files, chapter_line_map = resume_from_assembly_phase(
                temp_audio_dir, temp_line_audio_dir, checkpoint_data
            )
            
            # Continue with assembly and post-processing
            async for result in assembly_and_post_processing_phase(
                chapter_files, chapter_line_map, temp_audio_dir, temp_line_audio_dir, *args, **kwargs
            ):
                yield result
        else:
            # Run the original generator function
            async for result in original_generator_func(*args, **kwargs):
                yield result
    
    return wrapped_generator

async def assembly_and_post_processing_phase(chapter_files: List[str], chapter_line_map: Dict,
                                           temp_audio_dir: str, temp_line_audio_dir: str,
                                           output_format: str, narrator_gender: str, 
                                           generate_m4b_audiobook_file: bool, book_path: str, 
                                           add_emotion_tags: bool):
    """
    Handles the assembly and post-processing phases of audiobook generation.
    This function can be called either during normal generation or recovery.
    
    Args:
        chapter_files (List[str]): List of chapter filenames
        chapter_line_map (Dict): Mapping of chapters to line indices
        temp_audio_dir (str): Directory for temporary audio files
        temp_line_audio_dir (str): Directory for line segments
        output_format (str): Output format for the audiobook
        narrator_gender (str): Gender for narrator voice
        generate_m4b_audiobook_file (bool): Whether to generate M4B format
        book_path (str): Path to the source book file
        add_emotion_tags (bool): Whether to add emotion tags
    """
    from tqdm import tqdm
    from utils.audiobook_utils import (
        assemble_chapter_with_ffmpeg, add_silence_to_chapter_with_ffmpeg,
        convert_chapter_to_m4a_with_ffmpeg, generate_m4b_audiobook_with_ffmpeg
    )
    
    # Assembly phase
    chapter_assembly_bar = tqdm(total=len(chapter_files), unit="chapter", desc="Assembling Chapters")
    
    for chapter_file in chapter_files:
        assemble_chapter_with_ffmpeg(
            chapter_file, 
            chapter_line_map[chapter_file], 
            temp_line_audio_dir, 
            temp_audio_dir
        )
        
        chapter_assembly_bar.update(1)
        yield f"Assembled chapter: {chapter_file}"
    
    chapter_assembly_bar.close()
    yield "Completed assembling all chapters"
    
    # Post-processing phase
    post_processing_bar = tqdm(total=len(chapter_files)*2, unit="task", desc="Post Processing")
    
    # Add silence to each chapter file
    for chapter_file in chapter_files:
        chapter_path = os.path.join(temp_audio_dir, chapter_file)
        add_silence_to_chapter_with_ffmpeg(chapter_path, 1000)  # 1 second silence
        
        post_processing_bar.update(1)
        yield f"Added silence to chapter: {chapter_file}"

    m4a_chapter_files = []

    # Convert to M4A format
    for chapter_file in chapter_files:
        chapter_name = chapter_file.split('.')[0]
        m4a_chapter_file = f"{chapter_name}.m4a"
        
        convert_chapter_to_m4a_with_ffmpeg(
            os.path.join(temp_audio_dir, chapter_file),
            os.path.join(temp_audio_dir, m4a_chapter_file)
        )
        
        m4a_chapter_files.append(m4a_chapter_file)
        post_processing_bar.update(1)
        yield f"Converted to M4A: {m4a_chapter_file}"

    post_processing_bar.close()
    yield "Completed post-processing all chapters"

    # Final audiobook generation
    if generate_m4b_audiobook_file:
        yield "Generating final M4B audiobook file..."
        generate_m4b_audiobook_with_ffmpeg(
            m4a_chapter_files, 
            temp_audio_dir, 
            book_path, 
            narrator_gender
        )
        yield "✅ M4B audiobook file generated successfully"
    
    yield "🎉 Audiobook generation completed successfully!"