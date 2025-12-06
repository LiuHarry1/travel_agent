import React from 'react';
import { Upload, Search, Scissors, Brain, Database, Check, X } from 'lucide-react';
import { ProcessingStage, type FileProcessingStatus } from '../types/processing';
import './ProcessingTimeline.css';

interface ProcessingTimelineProps {
  fileStatus: FileProcessingStatus;
}

const STAGES = [
  { key: ProcessingStage.UPLOADING, label: 'Upload', icon: Upload },
  { key: ProcessingStage.PARSING, label: 'Parse', icon: Search },
  { key: ProcessingStage.CHUNKING, label: 'Chunk', icon: Scissors },
  { key: ProcessingStage.EMBEDDING, label: 'Embed', icon: Brain },
  { key: ProcessingStage.INDEXING, label: 'Index', icon: Database },
  { key: ProcessingStage.COMPLETED, label: 'Complete', icon: Check },
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
                {isCompleted ? (
                  <Check size={16} />
                ) : isErrorStage ? (
                  <X size={16} />
                ) : (
                  React.createElement(stage.icon, { size: 16 })
                )}
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
                    <div className="timeline-progress-text">{fileStatus.progress}%</div>
                  </div>
                )}
                {isActive && fileStatus.message && (
                  <div className="timeline-details" style={{ marginTop: '2px', fontSize: '11px' }}>
                    {fileStatus.message}
                  </div>
                )}
                {isCompleted && index < STAGES.length - 1 && (
                  <div className="timeline-details" style={{ color: 'var(--success)', fontSize: '11px' }}>
                    Complete
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
          {(() => {
            const stats: Array<{ key: string; value: string | number; label: string }> = [];
            
            if (fileStatus.charCount) {
              stats.push({
                key: 'charCount',
                value: fileStatus.charCount.toLocaleString(),
                label: 'Characters'
              });
            }
            
            if (fileStatus.chunksCreated) {
              stats.push({
                key: 'chunksCreated',
                value: fileStatus.chunksCreated,
                label: 'Chunks'
              });
            }
            
            if (fileStatus.chunksIndexed) {
              stats.push({
                key: 'chunksIndexed',
                value: fileStatus.chunksIndexed,
                label: 'Indexed'
              });
            }
            
            return stats.map((stat) => (
              <div key={stat.key} className="timeline-stat-item">
                <div className="timeline-stat-value">{stat.value}</div>
                <div className="timeline-stat-label">{stat.label}</div>
              </div>
            ));
          })()}
        </div>
      )}
    </div>
  );
};
