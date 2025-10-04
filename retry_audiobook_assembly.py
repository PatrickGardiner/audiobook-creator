#!/usr/bin/env python3
"""
Manual Recovery Script for Audiobook Generation

This script allows you to manually retry the FFmpeg assembly and post-processing
phases without regenerating all the individual line segments.

Usage:
    python retry_audiobook_assembly.py [options]

Options:
    --temp-dir DIR          Temporary audio directory (default: temp_audio)
    --output-format FORMAT  Output format (default: m4a)
    --narrator-gender GENDER Narrator gender (default: male)
    --book-path PATH        Path to source book file
    --generate-m4b          Generate M4B format instead of M4A
    --add-emotion-tags      Include emotion tags in processing
    --force-cleanup         Clean up all existing chapter files before retry
"""

import os
import sys
import argparse
import asyncio
from typing import Dict, List

def main():
    parser = argparse.ArgumentParser(description='Retry audiobook assembly from existing line segments')
    parser.add_argument('--temp-dir', default='temp_audio', help='Temporary audio directory')
    parser.add_argument('--output-format', default='m4a', help='Output format (m4a, mp3, etc.)')
    parser.add_argument('--narrator-gender', default='male', choices=['male', 'female'], help='Narrator gender')
    parser.add_argument('--book-path', help='Path to source book file (required for M4B generation)')
    parser.add_argument('--generate-m4b', action='store_true', help='Generate M4B format')
    parser.add_argument('--add-emotion-tags', action='store_true', help='Include emotion tags')
    parser.add_argument('--force-cleanup', action='store_true', help='Clean up existing chapter files first')
    
    args = parser.parse_args()
    
    # Validate required arguments
    if args.generate_m4b and not args.book_path:
        print("❌ Error: --book-path is required when using --generate-m4b")
        return 1
    
    return asyncio.run(retry_assembly(
        temp_dir=args.temp_dir,
        output_format=args.output_format,
        narrator_gender=args.narrator_gender,
        book_path=args.book_path,
        generate_m4b=args.generate_m4b,
        add_emotion_tags=args.add_emotion_tags,
        force_cleanup=args.force_cleanup
    ))

async def retry_assembly(temp_dir: str = 'temp_audio', 
                        output_format: str = 'm4a',
                        narrator_gender: str = 'male',
                        book_path: str = None,
                        generate_m4b: bool = False,
                        add_emotion_tags: bool = False,
                        force_cleanup: bool = False) -> int:
    """
    Retry the audiobook assembly process from existing line segments.
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    try:
        from utils.recovery_utils import (
            can_resume_from_assembly, resume_from_assembly_phase, 
            assembly_and_post_processing_phase, cleanup_partial_chapters
        )
    except ImportError:
        print("❌ Error: Recovery utilities not found. Make sure utils/recovery_utils.py exists.")
        return 1
    
    temp_line_audio_dir = os.path.join(temp_dir, "line_segments")
    
    print("🔍 Checking for existing line segments and recovery data...")
    
    # Check if we can resume
    can_resume, checkpoint_data = can_resume_from_assembly(temp_dir, temp_line_audio_dir)
    
    if not can_resume:
        print("❌ Cannot resume: Missing line segments or checkpoint data")
        print("💡 You need to run the full generation process first to create line segments")
        return 1
    
    print("✅ Recovery data found!")
    print(f"📊 Found {checkpoint_data['total_lines']} line segments")
    print(f"📚 Chapters to assemble: {len(checkpoint_data['chapter_files'])}")
    
    # Get chapter data
    chapter_files, chapter_line_map = resume_from_assembly_phase(
        temp_dir, temp_line_audio_dir, checkpoint_data
    )
    
    if force_cleanup:
        print("🧹 Force cleanup enabled - removing existing chapter files...")
        cleanup_partial_chapters(temp_dir, chapter_files)
    
    print("🚀 Starting assembly and post-processing...")
    
    try:
        # Run the assembly and post-processing
        async for status_message in assembly_and_post_processing_phase(
            chapter_files=chapter_files,
            chapter_line_map=chapter_line_map,
            temp_audio_dir=temp_dir,
            temp_line_audio_dir=temp_line_audio_dir,
            output_format=output_format,
            narrator_gender=narrator_gender,
            generate_m4b_audiobook_file=generate_m4b,
            book_path=book_path,
            add_emotion_tags=add_emotion_tags
        ):
            print(status_message)
        
        print("🎉 Assembly completed successfully!")
        
        # List generated files
        generated_dir = "generated_audiobooks"
        if os.path.exists(generated_dir):
            print(f"\n📁 Generated files in {generated_dir}:")
            for file in os.listdir(generated_dir):
                file_path = os.path.join(generated_dir, file)
                if os.path.isfile(file_path):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    print(f"   📄 {file} ({size_mb:.1f} MB)")
        
        return 0
        
    except Exception as e:
        print(f"❌ Assembly failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("   • Check that FFmpeg is properly installed and accessible")
        print("   • Ensure temp_audio directory has sufficient disk space")
        print("   • Try running with --force-cleanup to remove partial files")
        print("   • Check file permissions in the temp_audio directory")
        return 1

def print_recovery_status():
    """Print current recovery status and available options."""
    temp_dir = "temp_audio"
    temp_line_audio_dir = os.path.join(temp_dir, "line_segments")
    
    print("🔍 Recovery Status Check")
    print("=" * 50)
    
    # Check line segments
    if os.path.exists(temp_line_audio_dir):
        line_files = [f for f in os.listdir(temp_line_audio_dir) if f.startswith('line_') and f.endswith('.wav')]
        print(f"📁 Line segments directory: {temp_line_audio_dir}")
        print(f"🎵 Line segments found: {len(line_files)}")
    else:
        print(f"❌ Line segments directory not found: {temp_line_audio_dir}")
        return
    
    # Check checkpoint
    checkpoint_file = os.path.join(temp_dir, "recovery_checkpoint.json")
    if os.path.exists(checkpoint_file):
        print(f"✅ Recovery checkpoint found: {checkpoint_file}")
        
        try:
            import json
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
            print(f"📊 Total lines in checkpoint: {checkpoint.get('total_lines', 'Unknown')}")
            print(f"📚 Chapters in checkpoint: {len(checkpoint.get('chapter_files', []))}")
        except Exception as e:
            print(f"⚠️ Could not read checkpoint details: {e}")
    else:
        print(f"❌ Recovery checkpoint not found: {checkpoint_file}")
        return
    
    # Check existing chapter files
    if os.path.exists(temp_dir):
        chapter_files = [f for f in os.listdir(temp_dir) if f.endswith('.wav') and not f.startswith('line_')]
        if chapter_files:
            print(f"🎯 Existing chapter files: {len(chapter_files)}")
            for chapter in chapter_files[:5]:  # Show first 5
                print(f"   • {chapter}")
            if len(chapter_files) > 5:
                print(f"   ... and {len(chapter_files) - 5} more")
        else:
            print("📝 No existing chapter files found")
    
    print("\n🚀 You can retry assembly with:")
    print("   python retry_audiobook_assembly.py")
    print("   python retry_audiobook_assembly.py --force-cleanup  # Clean existing chapters first")
    print("   python retry_audiobook_assembly.py --generate-m4b --book-path 'path/to/book.epub'")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in ['--status', '-s']:
        print_recovery_status()
    else:
        exit_code = main()
        sys.exit(exit_code)