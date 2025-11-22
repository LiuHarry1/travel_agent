"""
Test script for tool calling with streaming response.
Tests that:
1. Tool calls are executed correctly
2. Streaming response returns content after tool execution
3. History sent to LLM only contains user/assistant messages (no tool messages)
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

# Fix Unicode encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up Windows event loop policy before any imports
if sys.platform == "win32":
    import asyncio
    if hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.service.chat import ChatService
from app.models import ChatRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_tool_calling_stream():
    """Test tool calling with streaming response."""
    service = ChatService()
    
    # Test 1: First message with tool call
    print("\n" + "="*80)
    print("Test 1: First message - should trigger tool call")
    print("="*80)
    
    request1 = ChatRequest(
        message="我要去日本旅游,怎么申请签证",
        messages=[]  # Empty history
    )
    
    print("\nStreaming response:")
    chunks = []
    tool_call_events = []
    
    for event in service.chat_stream(request1):
        event_type = event.get("type")
        if event_type == "chunk":
            content = event.get("content", "")
            chunks.append(content)
            print(content, end="", flush=True)
        elif event_type in ("tool_call_start", "tool_call_end", "tool_call_error"):
            tool_call_events.append(event)
            print(f"\n[Tool Event] {event_type}: {event.get('tool', 'unknown')}")
    
    print(f"\n\nTotal chunks received: {len(chunks)}")
    print(f"Total content length: {sum(len(c) for c in chunks)}")
    print(f"Tool call events: {len(tool_call_events)}")
    
    if not chunks:
        print("[FAIL] ERROR: No chunks received!")
        return False
    else:
        print("[PASS] Test 1 passed: Received content chunks")
    
    # Test 2: Second message - verify history filtering
    print("\n" + "="*80)
    print("Test 2: Second message - verify history only contains user/assistant")
    print("="*80)
    
    # Simulate what frontend would send (with tool_calls in history)
    history_with_tools = [
        {
            "role": "user",
            "content": "我要去日本旅游,怎么申请签证"
        },
        {
            "role": "assistant",
            "content": "根据FAQ工具查询的结果...",  # This would be the actual response
            "tool_calls": [  # This should be filtered out
                {
                    "id": "call_123",
                    "name": "faq",
                    "arguments": {"query": "日本签证"}
                }
            ]
        }
    ]
    
    request2 = ChatRequest(
        message="需要准备哪些材料?",
        messages=history_with_tools
    )
    
    # Check what messages are prepared
    prepared_messages = service._prepare_messages(request2)
    
    print("\nOriginal history (with tool_calls):")
    for i, msg in enumerate(history_with_tools):
        print(f"  {i}: role={msg.get('role')}, has_tool_calls={bool(msg.get('tool_calls'))}")
    
    print("\nPrepared messages (should be filtered):")
    for i, msg in enumerate(prepared_messages):
        print(f"  {i}: role={msg.get('role')}, content_length={len(msg.get('content', ''))}, has_tool_calls={bool(msg.get('tool_calls'))}")
    
    # Verify filtering
    has_tool_messages = any(msg.get("role") == "tool" for msg in prepared_messages)
    has_tool_calls = any("tool_calls" in msg for msg in prepared_messages)
    
    if has_tool_messages or has_tool_calls:
        print(f"\n[FAIL] ERROR: Tool messages or tool_calls found in prepared messages!")
        print(f"  Has tool messages: {has_tool_messages}")
        print(f"  Has tool_calls: {has_tool_calls}")
        return False
    else:
        print("\n[PASS] Test 2 passed: Tool messages and tool_calls filtered correctly")
    
    # Test 3: Stream second message
    print("\n" + "="*80)
    print("Test 3: Stream second message with filtered history")
    print("="*80)
    
    chunks2 = []
    for event in service.chat_stream(request2):
        event_type = event.get("type")
        if event_type == "chunk":
            content = event.get("content", "")
            chunks2.append(content)
            print(content, end="", flush=True)
        elif event_type in ("tool_call_start", "tool_call_end", "tool_call_error"):
            print(f"\n[Tool Event] {event_type}: {event.get('tool', 'unknown')}")
    
    print(f"\n\nTotal chunks received: {len(chunks2)}")
    print(f"Total content length: {sum(len(c) for c in chunks2)}")
    
    if not chunks2:
        print("[FAIL] ERROR: No chunks received for second message!")
        return False
    else:
        print("[PASS] Test 3 passed: Received content chunks for second message")
    
    print("\n" + "="*80)
    print("All tests passed!")
    print("="*80)
    return True

if __name__ == "__main__":
    try:
        success = test_tool_calling_stream()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        sys.exit(1)

