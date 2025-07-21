#!/usr/bin/env python3
"""Debug import issues."""

try:
    print("Importing orchestration_tools_real...")
    import video_system.orchestration_tools_real as ot
    print("Import successful!")
    
    print("Available attributes:")
    attrs = [x for x in dir(ot) if not x.startswith('_')]
    for attr in attrs:
        print(f"  - {attr}")
    
    print("\nLooking for coordinate functions:")
    coord_funcs = [x for x in attrs if 'coordinate' in x]
    print(f"Found: {coord_funcs}")
    
    print("\nChecking if functions exist:")
    funcs_to_check = [
        'coordinate_research_real',
        'coordinate_story_real', 
        'coordinate_assets_real',
        'coordinate_audio_real',
        'coordinate_assembly_real'
    ]
    
    for func_name in funcs_to_check:
        exists = hasattr(ot, func_name)
        print(f"  {func_name}: {'✓' if exists else '✗'}")
    
    print("\nChecking tool wrappers:")
    tools_to_check = [
        'coordinate_research_tool_real',
        'coordinate_story_tool_real',
        'coordinate_assets_tool_real', 
        'coordinate_audio_tool_real',
        'coordinate_assembly_tool_real'
    ]
    
    for tool_name in tools_to_check:
        exists = hasattr(ot, tool_name)
        print(f"  {tool_name}: {'✓' if exists else '✗'}")

except Exception as e:
    print(f"Error importing: {e}")
    import traceback
    traceback.print_exc()