import React from 'react';
import { ProcessingStage, type FileProcessingStatus } from '../types/processing';
import './ProcessingTimeline.css';

interface ProcessingTimelineProps {
  fileStatus: FileProcessingStatus;
}

const STAGES = [
  { key: ProcessingStage.UPLOADING, label: '上传', icon: '📤' },
  { key: ProcessingStage.PARSING, label: '解析', icon: '🔍' },
  { key: ProcessingStage.CHUNKING, label: '分块', icon: '✂️' },
  { key: ProcessingStage.EMBEDDING, label: '嵌入', icon: '🧠' },
  { key: ProcessingStage.INDEXING, label: '索引', icon: '💾' },
  { key: ProcessingStage.COMPLETED, label: '完成', icon: '✅' },
];

const getStageIndex = (stage: ProcessingStage): number => {
  return STAGES.findIndex(s => s.key === stage);
};

export const ProcessingTimeline: React.FC<ProcessingTimelineProps> = ({ fileStatus }) => {
  const currentStageIndex = getStageIndex(fileStatus.stage);
  const isError = fileStatus.stage === ProcessingStage.ERROR;
  const errorStageIndex = isError ? currentStageIndex : -1;

  return (
    <div className="processing-timeline">
      <div className="timeline-steps">
        {STAGES.map((stage, index) => {
          const isCompleted = currentStageIndex > index;
          const isActive = currentStageIndex === index && !isError;
          const isErrorStage = isError && index === errorStageIndex;
          
          return (
            <div
              key={stage.key}
              className={`timeline-item ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''} ${isErrorStage ? 'error' : ''}`}
            >
              <div className="timeline-icon">
                {isCompleted ? '✓' : isErrorStage ? '✕' : stage.icon}
              </div>
              <div className="timeline-content">
                <div className="timeline-label">{stage.label}</div>
                {isActive && (
                  <div className="timeline-details">
                    <div className="timeline-progress-bar">
                      <div
                        className="timeline-progress-fill"
                        style={{ width: `${fileStatus.progress}%` }}
                      />
                    </div>
                    <span className="timeline-progress-text">{fileStatus.progress}%</span>
                  </div>
                )}
                {isActive && fileStatus.message && (
                  <div className="timeline-details" style={{ marginTop: '4px', fontSize: '12px' }}>
                    {fileStatus.message}
                  </div>
                )}
                {isCompleted && index < STAGES.length - 1 && (
                  <div className="timeline-details" style={{ color: 'var(--success)', fontSize: '12px' }}>
                    完成
                  </div>
                )}
                {isErrorStage && (
                  <div className="timeline-details error-text">
                    {fileStatus.error || fileStatus.message}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      
      {(fileStatus.chunksCreated || fileStatus.chunksIndexed || fileStatus.charCount) && (
        <div className="timeline-stats">
          {fileStatus.charCount && (
            <div className="timeline-stat-item">
              <div className="timeline-stat-value">{fileStatus.charCount.toLocaleString()}</div>
              <div className="timeline-stat-label">字符数</div>
            </div>
          )}
          {fileStatus.chunksCreated && (
            <div className="timeline-stat-item">
              <div className="timeline-stat-value">{fileStatus.chunksCreated}</div>
              <div className="timeline-stat-label">Chunks</div>
            </div>
          )}
          {fileStatus.chunksIndexed && (
            <div className="timeline-stat-item">
              <div className="timeline-stat-value">{fileStatus.chunksIndexed}</div>
              <div className="timeline-stat-label">已索引</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
