# Fix Windows Conversion Error with Comprehensive Logging

## Problem Description

Windows version of the app shows "completed with error" during conversion, but no log files are generated on the desktop even when debug mode is enabled. The macOS version works correctly.

## Root Causes Identified

1. **PATH separator issue**: Hard-coded Unix-style colon (`:`) separator was used instead of platform-specific separator
2. **Error logging only on exceptions**: Log files were only created when exceptions were thrown, not when conversion returned `False`
3. **Windows desktop path detection**: Inconsistent desktop path detection on Windows systems

## Changes Made

### 1. Fixed PATH Separator Issue

**File: `components/resource_manager.py`**
- Changed hard-coded colon separator to `os.pathsep` for cross-platform compatibility
- Windows uses semicolon (`;`), Unix systems use colon (`:`)

```python
# Before:
new_path = ':'.join(paths_to_add) + ':' + original_path

# After:
new_path = os.pathsep.join(paths_to_add) + os.pathsep + original_path
```

**File: `components/conversion/converter.py`**
- Fixed another instance of hard-coded PATH separator

```python
# Before:
path_sep = ';' if platform.system() == "Windows" else ':'

# After:
# Use os.pathsep for cross-platform compatibility
os.environ['PATH'] = f"{z7_dir}{os.pathsep}{current_path}"
```

### 2. Enhanced Error Logging System

**File: `components/conversion/converter.py`**
- Added `_write_error_log()` method to centralize error log writing
- Now writes error logs even when conversion returns `False` without throwing exceptions
- Improved Windows desktop path detection using `USERPROFILE` environment variable
- Added fallback to temp directory if desktop is not accessible
- Includes comprehensive debugging information (PATH, environment variables, etc.)

**File: `components/conversion/progress_worker.py`**
- Added `_write_worker_error_log()` method for worker-level error logging
- Captures and logs exceptions with full traceback
- Provides clear error messages to users about log file location

### 3. Added Global Exception Handler

**File: `main.py`**
- Added `setup_global_exception_handler()` to catch all unhandled exceptions
- Writes critical error logs for any uncaught exceptions
- Ensures no error goes unlogged

### 4. Error Log Types

The system now generates three types of error logs:

1. **`eReader_CBZ_Error_[timestamp].txt`** - Detailed conversion failure logs
2. **`eReader_Worker_Error_[timestamp].txt`** - Worker thread error logs  
3. **`eReader_Critical_Error_[timestamp].txt`** - Uncaught exception logs

All logs include:
- Timestamp and platform information
- Full error messages and tracebacks
- Environment details (PATH, frozen state, etc.)
- Input/output file information

## Testing

### Windows Testing Steps

1. Build the Windows version:
   ```bash
   python build.py build-win
   ```

2. Run the converter and attempt to convert an EPUB file

3. If conversion fails, check for error logs in:
   - Desktop folder
   - `%TEMP%` directory
   - Program directory

### Expected Behavior

- On conversion failure, an error log file should be created
- The status bar should show the log file location
- Users can press Ctrl+Shift+D to enable debug mode for more detailed logging

## Code Quality

- All changes maintain cross-platform compatibility
- Error handling is defensive with multiple fallback options
- Logging is comprehensive but avoids sensitive information
- Code follows existing project patterns and conventions

## Files Modified

1. `components/resource_manager.py` - Fixed PATH separator
2. `components/conversion/converter.py` - Enhanced error logging, fixed PATH separator
3. `components/conversion/progress_worker.py` - Added worker error logging
4. `main.py` - Added global exception handler

## Impact

- Fixes critical issue preventing Windows users from debugging conversion failures
- Improves overall error reporting across all platforms
- Makes troubleshooting easier for both users and developers

## Backwards Compatibility

All changes are backward compatible. The enhanced logging system works on all platforms while fixing Windows-specific issues.