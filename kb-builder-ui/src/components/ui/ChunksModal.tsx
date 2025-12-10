import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import './ChunksModal.css';

interface ChunksModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export const ChunksModal: React.FC<ChunksModalProps> = ({
  isOpen,
  onClose,
  children,
}) => {
  // Handle ESC key to close modal
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="chunks-modal-overlay" onClick={onClose}>
      <div className="chunks-modal" onClick={(e) => e.stopPropagation()}>
        <div className="chunks-modal-header">
          <button 
            className="chunks-modal-close" 
            onClick={onClose} 
            aria-label="Close"
            title="Close (ESC)"
          >
            <X size={24} />
          </button>
        </div>
        <div className="chunks-modal-body">
          {children}
        </div>
      </div>
    </div>
  );
};

