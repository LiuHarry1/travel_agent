import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import './ConfirmDialog.css';

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info';
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'warning',
  onConfirm,
  onCancel,
}) => {
  if (!isOpen) return null;

  return (
    <div className="confirm-dialog-overlay" onClick={onCancel}>
      <div className={`confirm-dialog confirm-dialog-${variant}`} onClick={(e) => e.stopPropagation()}>
        <div className="confirm-dialog-header">
          <div className="confirm-dialog-icon">
            <AlertTriangle size={24} />
          </div>
          <h3>{title}</h3>
          <button className="confirm-dialog-close" onClick={onCancel} aria-label="Close">
            <X size={20} />
          </button>
        </div>
        
        <div className="confirm-dialog-body">
          <p>{message}</p>
        </div>
        
        <div className="confirm-dialog-actions">
          <button className="confirm-dialog-btn confirm-dialog-btn-cancel" onClick={onCancel}>
            {cancelText}
          </button>
          <button className={`confirm-dialog-btn confirm-dialog-btn-confirm confirm-dialog-btn-${variant}`} onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

