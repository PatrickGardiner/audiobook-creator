#!/usr/bin/env python3
"""
Test script to validate the retry assembly integration
"""

def test_imports():
    """Test that all required imports work"""
    try:
        # Test recovery utils import
        from utils.recovery_utils import can_resume_from_assembly
        print("✅ Recovery utils import successful")
        
        # Test retry assembly import
        from retry_audiobook_assembly import retry_assembly
        print("✅ Retry assembly import successful")
        
        # Test that the function exists and is callable
        import inspect
        if inspect.iscoroutinefunction(retry_assembly):
            print("✅ retry_assembly is an async function")
        else:
            print("⚠️ retry_assembly is not async")
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_recovery_status():
    """Test recovery status checking"""
    try:
        import os
        from utils.recovery_utils import can_resume_from_assembly
        
        temp_dir = "temp_audio"
        temp_line_audio_dir = os.path.join(temp_dir, "line_segments")
        
        # Check if directories exist
        print(f"Temp audio dir exists: {os.path.exists(temp_dir)}")
        print(f"Line segments dir exists: {os.path.exists(temp_line_audio_dir)}")
        
        if os.path.exists(temp_line_audio_dir):
            line_files = [f for f in os.listdir(temp_line_audio_dir) if f.startswith('line_') and f.endswith('.wav')]
            print(f"Line segments found: {len(line_files)}")
        
        # Try to check if can resume
        can_resume, checkpoint_data = can_resume_from_assembly(temp_dir, temp_line_audio_dir)
        print(f"Can resume: {can_resume}")
        if can_resume and checkpoint_data:
            print(f"Checkpoint has {checkpoint_data.get('total_lines', 0)} lines")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing recovery status: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing retry assembly integration...")
    print("=" * 50)
    
    import_success = test_imports()
    recovery_success = test_recovery_status()
    
    if import_success and recovery_success:
        print("\n✅ All tests passed! Integration should work correctly.")
    else:
        print("\n❌ Some tests failed. Check the errors above.")