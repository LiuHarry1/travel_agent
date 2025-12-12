# KB Builder UI

A modern React-based UI for the KB Builder service.

## Features

- 📤 **File Upload**: Drag and drop or select multiple files
- ⚙️ **Configuration Management**: Configure Milvus, embedding providers, and chunking settings
- 📚 **Collection Management**: Create, view, and delete collections
- 📊 **Real-time Progress**: Track upload and indexing progress
- 💾 **Settings Persistence**: Configuration saved to localStorage

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- KB Builder Service backend running on port 8006

### Installation

```bash
cd knowledge-base-builder-ui
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build

```bash
npm run build
```

## Configuration

Create a `.env` file in the root directory:

```env
VITE_API_URL=http://localhost:8006
```

## Usage

1. **Configure Settings**: Click the Settings button to configure:
   - Milvus connection (host, port, credentials)
   - Embedding provider (Qwen, OpenAI, BGE)
   - Chunking parameters (size, overlap, strategy)

2. **Select Collection**: Choose or create a collection from the sidebar

3. **Upload Files**: 
   - Drag and drop files or click to select
   - Supports: .md, .pdf, .docx, .html, .txt
   - Multiple files can be uploaded at once

4. **Monitor Progress**: Watch the upload and indexing progress

## Project Structure

```
src/
├── api/           # API client
├── components/    # React components
├── types/         # TypeScript types
└── styles/        # CSS files
```

## Technologies

- React 18
- TypeScript
- Vite
- CSS3
