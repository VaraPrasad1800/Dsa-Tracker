import React, { Suspense, lazy } from 'react';
import Editor from '@monaco-editor/react';

const LANGUAGE_MAP = {
  python: 'python',
  c: 'c',
  cpp: 'cpp',
  java: 'java',
};

export default function MonacoCodeEditor({
  value,
  onChange,
  language = 'python',
  onRun,
  onSubmit,
  readOnly = false,
  height = '100%',
}) {
  const handleEditorDidMount = (editor, monaco) => {
    // Add command for Ctrl+Enter / Cmd+Enter to Run
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      if (onRun) onRun();
    });

    // Add command for Ctrl+Shift+Enter to Submit
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter, () => {
      if (onSubmit) onSubmit();
    });
  };

  return (
    <div className="w-full h-full min-h-[300px] overflow-hidden rounded-xl border border-white/10 bg-[#1e1e1e]">
      <Editor
        height={height}
        language={LANGUAGE_MAP[language] || 'python'}
        value={value}
        theme="vs-dark"
        onChange={(val) => onChange(val || '')}
        onMount={handleEditorDidMount}
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 4,
          wordWrap: 'on',
          padding: { top: 12, bottom: 12 },
          fontFamily: "'Fira Code', monospace, Consolas, 'Courier New'",
          fontLigatures: true,
        }}
        loading={
          <div className="flex items-center justify-center h-full text-slate-500 text-xs font-mono">
            Loading editor...
          </div>
        }
      />
    </div>
  );
}
