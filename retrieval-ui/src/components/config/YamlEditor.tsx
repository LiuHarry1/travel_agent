import { memo } from 'react'
import './YamlEditor.css'

interface YamlEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
}

function YamlEditor({ value, onChange, placeholder = 'Enter YAML configuration...', disabled = false }: YamlEditorProps) {
  return (
    <textarea
      className="yaml-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      spellCheck={false}
      disabled={disabled}
      aria-label="YAML configuration editor"
    />
  )
}

export default memo(YamlEditor)

