import React from 'react';
import './Skeleton.css';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'circular' | 'rectangular';
  className?: string;
  lines?: number; // For text variant with multiple lines
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width,
  height,
  variant = 'rectangular',
  className = '',
  lines = 1,
}) => {
  const style: React.CSSProperties = {
    width: width || (variant === 'circular' ? height : '100%'),
    height: height || (variant === 'circular' ? width : '1em'),
  };

  if (variant === 'text' && lines > 1) {
    return (
      <div className={`skeleton-text-container ${className}`}>
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className={`skeleton skeleton-${variant}`}
            style={{
              ...style,
              width: index === lines - 1 ? '80%' : '100%',
              marginBottom: index < lines - 1 ? '0.5em' : 0,
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`skeleton skeleton-${variant} ${className}`}
      style={style}
    />
  );
};

