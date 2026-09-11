import React, { useEffect, useRef } from 'react';

/**
 * Syntax-highlighted code block using Prism.js (loaded dynamically).
 * Falls back to plain <pre><code> if Prism fails to load.
 *
 * Props:
 *   code       - source code string
 *   language   - language alias (python, javascript, java, cpp, etc.)
 *   className  - extra classes for the container
 */
export default function CodeBlock({ code, language = 'python', className = '' }) {
  const preRef = useRef(null);
  const [highlighted, setHighlighted] = React.useState(false);

  // Map our language names to Prism aliases
  const prismLanguageMap = {
    python: 'python',
    javascript: 'javascript',
    js: 'javascript',
    typescript: 'typescript',
    ts: 'typescript',
    java: 'java',
    cpp: 'cpp',
    'c++': 'cpp',
    c: 'c',
    go: 'go',
    rust: 'rust',
    sql: 'sql',
  };

  const prismLang = prismLanguageMap[language.toLowerCase()] || 'python';

  // Load Prism and highlight on mount
  useEffect(() => {
    const pre = preRef.current;
    if (!pre) return;

    const codeElem = pre.querySelector('code');
    if (!codeElem) return;

    // Set the language class for Prism
    codeElem.className = `language-${prismLang}`;

    // Try to load Prism dynamically (only once)
    const loadPrism = async () => {
      try {
        // Try CDN first
        const [prismCore, prismTheme] = await Promise.all([
          import('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js'),
          import('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/line-numbers/prism-line-numbers.min.js'),
        ]);
        // Load language components dynamically
        await import(`https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-${prismLang}.min.js`);

        // Apply highlighting
        if (window.Prism) {
          window.Prism.highlightElement(codeElem);
          setHighlighted(true);
        }
      } catch (e) {
        // Prism failed to load — leave as plain code
        console.debug('Prism not available, using fallback:', e);
      }
    };

    loadPrism();
  }, [code, prismLang]);

  // Escape HTML for safe rendering in <code>
  const escapedCode = code
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>')
    .replace(/"/g, '"')
    .replace(/'/g, '&#039;');

  return (
    <div className={`bg-slate-950 border border-slate-800 rounded-xl overflow-hidden ${className}`}>
      <div className="flex items-center justify-between p-2 bg-slate-900/80 border-b border-slate-800">
        <span className="text-xs text-slate-400 uppercase tracking-wider font-mono">
          {language}
        </span>
        <button
          onClick={() => {
            navigator.clipboard.writeText(code).catch(() => {});
          }}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          title="Copy code"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
          </svg>
        </button>
      </div>
      <pre
        ref={preRef}
        className={`p-4 overflow-x-auto ${highlighted ? 'line-numbers' : ''}`}
        style={{ maxHeight: '500px' }}
      >
        <code
          className={`font-mono text-sm text-slate-100 leading-relaxed ${highlighted ? `language-${prismLang}` : ''}`}
          dangerouslySetInnerHTML={{ __html: escapedCode }}
        />
      </pre>
    </div>
  );
}