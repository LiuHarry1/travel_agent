# Testing Guide

## How to Test the Scroll-to-Top Feature

The development server should be running. If not, start it with:
```bash
npm run dev
```

Then open your browser to the URL shown (usually `http://localhost:5173`)

## Test Scenarios

### Test 1: Basic Scroll Behavior
1. Open the chat interface
2. Type a message (e.g., "Hello")
3. Click "Send" or press Enter
4. **Expected**: Your message should automatically scroll to the top of the message area
5. Wait for the agent response to start appearing
6. **Expected**: As the agent response grows, your message should be pushed up naturally (not sticky)

### Test 2: Long Agent Response
1. Send a message that will trigger a longer response
2. **Expected**: 
   - Your message appears at the top initially
   - As the agent response streams in word-by-word, your message gradually moves up
   - The scrolling feels natural and smooth

### Test 3: Multiple Messages
1. Send a first message (e.g., "First message")
2. Wait for the agent to respond
3. Send a second message (e.g., "Second message")
4. **Expected**: 
   - The second message scrolls to the top
   - The first message and agent response remain in their positions above
   - No conflicts or jumping

### Test 4: Rapid Messages
1. Send multiple messages quickly (before agent responds)
2. **Expected**: Each new user message scrolls to the top when sent

## What to Look For

✅ **Correct Behavior:**
- User message scrolls to top when sent
- Agent response pushes user message up naturally
- Smooth scrolling animations
- No sticky or fixed positioning
- Messages maintain their order (user → assistant)

❌ **Incorrect Behavior:**
- User message doesn't scroll to top
- User message stays fixed/sticky at top
- Scrolling jumps or conflicts
- Messages appear in wrong order

## Implementation Details

The scroll-to-top feature uses:
- `useRef` to track the latest user message DOM element
- `useLayoutEffect` to trigger scroll after DOM update (before paint)
- `scrollIntoView({ block: 'start' })` to position message at viewport top
- Smooth scrolling behavior for better UX

The scroll happens within the `.chat-messages-wrapper` container, not the entire page.


