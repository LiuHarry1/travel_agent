# Chatbot - Scroll to Top Demo

A simple React chatbot demonstrating scroll-to-top functionality for user messages.

## Features

- **Scroll to Top**: When a user sends a message, it automatically scrolls to show that message at the top of the viewport
- **Natural Scrolling**: Agent responses naturally push user messages up (no sticky behavior)
- **Streaming Simulation**: Agent responses are streamed word-by-word to demonstrate real-time behavior
- **Smooth Animations**: Smooth scrolling and fade-in animations for messages

## How to Run

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open your browser to the URL shown (usually `http://localhost:5173`)

## How to Test

1. **Basic Scroll Test**:
   - Send a message
   - Observe that your message automatically scrolls to the top of the viewport
   - Wait for the agent response
   - Notice how the agent's response pushes your message up naturally

2. **Long Response Test**:
   - Send multiple messages
   - Send a message that triggers a longer agent response
   - Watch how your message stays visible initially, then gets pushed up as the response grows

3. **Multiple Messages Test**:
   - Send several messages in quick succession
   - Each new user message should scroll to the top
   - Previous messages should remain in their positions

## Implementation Details

The scroll-to-top functionality is implemented using:

- `useRef` to track the latest user message element
- `useLayoutEffect` to scroll the message to top when it's added
- `scrollIntoView({ block: 'start' })` to position the message at the viewport top

## Project Structure

```
front_new/
├── src/
│   ├── components/
│   │   ├── ChatPage.tsx      # Main chat interface
│   │   └── MessageList.tsx   # Message list with scroll logic
│   ├── App.tsx
│   ├── main.tsx
│   └── styles.css
├── index.html
├── package.json
└── vite.config.ts
```

## Technologies

- React 18
- TypeScript
- Vite
- CSS3 (no external UI libraries)


