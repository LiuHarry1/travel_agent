import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './MarkdownHighlightViewer.css';

interface MarkdownHighlightViewerProps {
  content: string;
  highlightStart: number;
  highlightEnd: number;
  onClose?: () => void;
}

export const MarkdownHighlightViewer: React.FC<MarkdownHighlightViewerProps> = ({
  content,
  highlightStart,
  highlightEnd,
  onClose,
}) => {
  const highlightRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to highlight when component mounts or highlight changes
    if (highlightRef.current) {
      highlightRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }, [highlightStart, highlightEnd]);

  // Split content into parts: before, highlight, after
  const beforeText = content.substring(0, highlightStart);
  const highlightText = content.substring(highlightStart, highlightEnd);
  const afterText = content.substring(highlightEnd);

  return (
    <div className="markdown-highlight-viewer">
      {onClose && (
        <div className="markdown-highlight-header">
          <h3>Markdown File Preview with Highlighted Chunk</h3>
          <button onClick={onClose} className="close-btn" title="Close">×</button>
        </div>
      )}
      <div className="markdown-highlight-content">
        {/* Before highlight */}
        <div className="markdown-before">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={vscDarkPlus}
                    language={match[1]}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
              table({ children }: any) {
                return (
                  <div className="table-wrapper">
                    <table>{children}</table>
                  </div>
                );
              },
            }}
          >
            {beforeText}
          </ReactMarkdown>
        </div>

        {/* Highlighted chunk */}
        <div ref={highlightRef} className="markdown-highlight-section">
          <div className="highlight-label">Highlighted Chunk</div>
          <div className="markdown-highlight">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, inline, className, children, ...props }: any) {
                  const match = /language-(\w+)/.exec(className || '');
                  return !inline && match ? (
                    <SyntaxHighlighter
                      style={vscDarkPlus}
                      language={match[1]}
                      PreTag="div"
                      {...props}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  );
                },
                table({ children }: any) {
                  return (
                    <div className="table-wrapper">
                      <table>{children}</table>
                    </div>
                  );
                },
              }}
            >
              {highlightText}
            </ReactMarkdown>
          </div>
        </div>

        {/* After highlight */}
        <div className="markdown-after">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={vscDarkPlus}
                    language={match[1]}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
              table({ children }: any) {
                return (
                  <div className="table-wrapper">
                    <table>{children}</table>
                  </div>
                );
              },
            }}
          >
            {afterText}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
};

