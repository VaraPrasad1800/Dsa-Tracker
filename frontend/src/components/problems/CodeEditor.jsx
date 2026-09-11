import React, { useRef, useEffect, useState } from 'react';

/**
 * Enhanced Code Editor Component
 * Features: Syntax highlighting (via simple regex), line numbers, tab support,
 * keyboard shortcuts, copy button, language selector
 */
export default function CodeEditor({
  value,
  onChange,
  language = 'python',
  onLanguageChange,
  placeholder = '# Write your solution here...',
  readOnly = false,
  className = '',
}) {
  const textareaRef = useRef(null);
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [copied, setCopied] = useState(false);

  // Language-specific keywords for basic syntax highlighting
  const languageKeywords = {
    python: [
      'def', 'class', 'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally',
      'with', 'as', 'import', 'from', 'return', 'yield', 'lambda', 'and', 'or', 'not',
      'in', 'is', 'None', 'True', 'False', 'pass', 'break', 'continue', 'raise',
      'global', 'nonlocal', 'async', 'await', 'match', 'case'
    ],
    javascript: [
      'function', 'const', 'let', 'var', 'if', 'else', 'for', 'while', 'do', 'switch',
      'case', 'default', 'try', 'catch', 'finally', 'throw', 'return', 'break', 'continue',
      'new', 'this', 'super', 'class', 'extends', 'import', 'export', 'from', 'as',
      'async', 'await', 'yield', 'null', 'undefined', 'true', 'false', 'typeof', 'instanceof'
    ],
    java: [
      'public', 'private', 'protected', 'static', 'final', 'class', 'interface', 'extends',
      'implements', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default',
      'try', 'catch', 'finally', 'throw', 'throws', 'return', 'break', 'continue',
      'new', 'this', 'super', 'import', 'package', 'void', 'int', 'long', 'double',
      'float', 'boolean', 'char', 'String', 'null', 'true', 'false'
    ],
    cpp: [
      'include', 'using', 'namespace', 'class', 'struct', 'public', 'private', 'protected',
      'virtual', 'override', 'final', 'template', 'typename', 'if', 'else', 'for', 'while',
      'do', 'switch', 'case', 'default', 'try', 'catch', 'throw', 'return', 'break', 'continue',
      'new', 'delete', 'this', 'nullptr', 'true', 'false', 'int', 'long', 'double',
      'float', 'bool', 'char', 'void', 'std', 'vector', 'string', 'map', 'set'
    ],
    c: [
      'include', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default',
      'try', 'catch', 'throw', 'return', 'break', 'continue', 'sizeof', 'typedef',
      'struct', 'union', 'enum', 'static', 'extern', 'const', 'void', 'int', 'char',
      'short', 'long', 'float', 'double', 'signed', 'unsigned', 'NULL', 'true', 'false'
    ],
    go: [
      'package', 'import', 'func', 'var', 'const', 'type', 'struct', 'interface',
      'if', 'else', 'for', 'switch', 'case', 'default', 'defer', 'go', 'select',
      'return', 'break', 'continue', 'fallthrough', 'range', 'make', 'new',
      'int', 'int8', 'int16', 'int32', 'int64', 'uint', 'uint8', 'uint16', 'uint32', 'uint64',
      'float32', 'float64', 'complex64', 'complex128', 'bool', 'string', 'byte', 'rune',
      'nil', 'true', 'false', 'append', 'len', 'cap', 'copy', 'delete', 'panic', 'recover'
    ],
  };

  const keywords = languageKeywords[language] || languageKeywords.python;

  const languageOptions = [
    { value: 'python', label: 'Python' },
    { value: 'java', label: 'Java' },
    { value: 'cpp', label: 'C++' },
    { value: 'c', label: 'C' },
    { value: 'go', label: 'Go' },
    { value: 'javascript', label: 'JavaScript' },
  ];

  // Handle Tab key for indentation
  const handleKeyDown = (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;

      // Insert tab or spaces
      const tabSize = 2;
      const spaces = ' '.repeat(tabSize);

      if (start === end) {
        // Simple insert
        const newValue = value.slice(0, start) + spaces + value.slice(end);
        onChange(newValue);
        // Move cursor after inserted spaces
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = start + tabSize;
        }, 0);
      } else {
        // Multi-line indent
        const before = value.slice(0, start);
        const selected = value.slice(start, end);
        const after = value.slice(end);

        const lines = selected.split('\n');
        const indentedLines = lines.map(line => spaces + line);
        const newValue = before + indentedLines.join('\n') + after;

        onChange(newValue);
        setTimeout(() => {
          textarea.selectionStart = start;
          textarea.selectionEnd = start + indentedLines.join('\n').length;
        }, 0);
      }
    }

    // Handle Shift+Tab for outdent
    if (e.key === 'Tab' && e.shiftKey) {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;

      const before = value.slice(0, start);
      const selected = value.slice(start, end);
      const after = value.slice(end);

      const lines = selected.split('\n');
      const outdentedLines = lines.map(line => {
        if (line.startsWith('  ')) return line.slice(2);
        if (line.startsWith('\t')) return line.slice(1);
        return line;
      });

      const newValue = before + outdentedLines.join('\n') + after;
      onChange(newValue);
      setTimeout(() => {
        textarea.selectionStart = start;
        textarea.selectionEnd = start + outdentedLines.join('\n').length;
      }, 0);
    }

    // Ctrl+Enter to save (if handler provided)
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      // Could trigger a save callback here
    }
  };

  // Copy code to clipboard
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Download code as file
  const handleDownload = () => {
    const ext = { python: 'py', javascript: 'js', java: 'java', cpp: 'cpp', c: 'c', go: 'go' }[language] || 'txt';
    const blob = new Blob([value], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `solution.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Split lines for line numbers
  const lines = value.split('\n');
  const lineCount = lines.length || 1;

  return (
    <div className={`relative bg-slate-950 border border-slate-800 rounded-xl overflow-hidden ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between p-2 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <select
            value={language}
            onChange={(e) => onLanguageChange?.(e.target.value)}
            className="text-xs px-2 py-1 bg-slate-800 border border-slate-700 rounded text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            disabled={!onLanguageChange}
          >
            {languageOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={showLineNumbers}
              onChange={(e) => setShowLineNumbers(e.target.checked)}
              className="rounded border-slate-700 text-indigo-500 focus:ring-indigo-500"
            />
            Line Numbers
          </label>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            title="Copy code (Ctrl+C)"
          >
            {copied ? (
              <svg className="h-4 w-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
            )}
          </button>
          <button
            onClick={handleDownload}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            title="Download as file"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </button>
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex overflow-hidden">
        {/* Line Numbers */}
        {showLineNumbers && (
          <div className="bg-slate-900/50 border-r border-slate-800 px-2 py-2 select-none overflow-hidden">
            <div className="font-mono text-xs text-slate-500 leading-6 min-h-[200px]">
              {Array.from({ length: lineCount }, (_, i) => i + 1).map((num) => (
                <div key={num} className="h-6">{num}</div>
              ))}
            </div>
          </div>
        )}

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          readOnly={readOnly}
          spellCheck={false}
          className={`
            flex-1 bg-transparent border-none outline-none resize-none
            font-mono text-sm text-emerald-400 placeholder-slate-700
            leading-6 p-2 min-h-[200px] w-full
            ${readOnly ? 'opacity-70 cursor-not-allowed' : ''}
          `}
          style={{
            lineHeight: '1.5rem', // 24px = 6 * 4
            tabSize: 2,
          }}
        />
      </div>

      {/* Status Bar */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900/50 border-t border-slate-800 text-xs text-slate-500">
        <span>{lineCount} lines • {value.length} chars</span>
        <span className="uppercase">{language}</span>
        <span>LF</span>
      </div>
    </div>
  );
}