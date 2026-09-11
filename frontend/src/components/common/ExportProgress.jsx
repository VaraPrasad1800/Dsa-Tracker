import React, { useState } from 'react';
import { Download, ChevronDown, FileJson, FileSpreadsheet, FileText } from 'lucide-react';
import { exportApi } from '../../api/client';
import { toast } from './Toast';

export default function ExportProgress({ className = '', sidebarMode = false, collapsed = false }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async (format) => {
    setIsExporting(true);
    try {
      const response = await exportApi.getExportProgress(format);
      const blob = new Blob([response.data]);
      const url = URL.createObjectURL(blob);
      const ext = { json: 'json', csv: 'csv', markdown: 'md' }[format] || 'txt';
      const a = document.createElement('a');
      a.href = url;
      a.download = `dsa_tracker_export_${new Date().toISOString().split('T')[0]}.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success(`Exported as ${format.toUpperCase()}! 📁`);
    } catch (err) {
      console.error('Export failed:', err);
      toast.error('Export failed. Please try again.');
    } finally {
      setIsExporting(false);
      setIsOpen(false);
    }
  };

  if (sidebarMode) {
    return (
      <div className="relative w-full">
        <button
          onClick={() => setIsOpen(!isOpen)}
          disabled={isExporting}
          title={collapsed ? 'Export progress data' : undefined}
          className={`w-full flex items-center gap-3 transition-colors ${
            collapsed ? 'justify-center' : ''
          }`}
        >
          <Download className="h-4 w-4 shrink-0 text-slate-400" style={{ width: 16, height: 16 }} />
          {!collapsed && (
            <span className="text-sm whitespace-nowrap flex-1 text-left">
              {isExporting ? 'Exporting...' : 'Export Data'}
            </span>
          )}
          {!collapsed && <ChevronDown className="h-3.5 w-3.5 text-slate-500" />}
        </button>

        {isOpen && (
          <div className="absolute left-full bottom-0 ml-2 w-48 glass-modal border border-white/[0.08] rounded-xl shadow-2xl py-1 z-50">
            <button
              onClick={() => handleExport('json')}
              className="w-full text-left px-3.5 py-2 text-xs text-slate-200 hover:bg-white/[0.05] transition flex items-center gap-2"
            >
              <FileJson className="h-3.5 w-3.5 text-indigo-400" /> JSON Format
            </button>
            <button
              onClick={() => handleExport('csv')}
              className="w-full text-left px-3.5 py-2 text-xs text-slate-200 hover:bg-white/[0.05] transition flex items-center gap-2"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" /> CSV Spreadsheet
            </button>
            <button
              onClick={() => handleExport('markdown')}
              className="w-full text-left px-3.5 py-2 text-xs text-slate-200 hover:bg-white/[0.05] transition flex items-center gap-2"
            >
              <FileText className="h-3.5 w-3.5 text-amber-400" /> Markdown Notes
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExporting}
        className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-2"
      >
        <Download className="h-3.5 w-3.5" />
        <span>{isExporting ? 'Exporting...' : 'Export'}</span>
        <ChevronDown className="h-3.5 w-3.5" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 glass-modal border border-white/[0.08] rounded-xl shadow-2xl py-1 z-50">
          <button
            onClick={() => handleExport('json')}
            className="w-full text-left px-4 py-2 text-xs text-slate-200 hover:bg-white/[0.05] transition flex items-center gap-2"
          >
            <FileJson className="h-3.5 w-3.5 text-indigo-400" /> JSON Format
          </button>
          <button
            onClick={() => handleExport('csv')}
            className="w-full text-left px-4 py-2 text-xs text-slate-200 hover:bg-white/[0.05] transition flex items-center gap-2"
          >
            <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" /> CSV Spreadsheet
          </button>
          <button
            onClick={() => handleExport('markdown')}
            className="w-full text-left px-4 py-2 text-xs text-slate-200 hover:bg-white/[0.05] transition flex items-center gap-2"
          >
            <FileText className="h-3.5 w-3.5 text-amber-400" /> Markdown Notes
          </button>
        </div>
      )}
    </div>
  );
}