import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, CheckCheck, ExternalLink, X } from 'lucide-react';
import { notificationsApi } from '../../api/client';

export default function NotificationCenter({ onNavigateTab }) {
  const [isOpen, setIsOpen] = useState(false);
  const buttonRef = useRef(null);
  const panelRef = useRef(null);
  const queryClient = useQueryClient();

  const [panelStyle, setPanelStyle] = useState({
    position: 'fixed',
    top: 0,
    left: 0,
    width: 384,
    maxHeight: 520,
    zIndex: 9999,
  });

  // Calculate clamped viewport-safe coordinates
  const updatePosition = useCallback(() => {
    if (!buttonRef.current) return;
    const rect = buttonRef.current.getBoundingClientRect();
    const PADDING = 16;
    const TARGET_WIDTH = 384;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Constrain width to available viewport
    const width = Math.min(TARGET_WIDTH, viewportWidth - PADDING * 2);

    // Horizontal placement:
    // Try anchoring to the button's left edge (into the main screen area).
    // If that would overflow the right viewport edge, anchor to the right.
    let left = rect.left;
    if (left + width > viewportWidth - PADDING) {
      left = rect.right - width;
    }
    // Strictly clamp within viewport boundaries
    left = Math.max(PADDING, Math.min(left, viewportWidth - width - PADDING));

    // Vertical placement:
    let top = rect.bottom + 8;
    let maxHeight = Math.min(540, viewportHeight - top - PADDING);

    // If constrained below but has more room above:
    if (maxHeight < 220 && rect.top > viewportHeight - rect.bottom) {
      const spaceAbove = rect.top - PADDING - 8;
      maxHeight = Math.min(540, spaceAbove);
      top = rect.top - maxHeight - 8;
    }

    setPanelStyle({
      position: 'fixed',
      top: Math.round(top),
      left: Math.round(left),
      width: Math.round(width),
      maxHeight: Math.round(maxHeight),
      zIndex: 9999,
    });
  }, []);

  // Update position on open, resize, and scroll
  useEffect(() => {
    if (!isOpen) return;

    updatePosition();

    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, true);

    return () => {
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition, true);
    };
  }, [isOpen, updatePosition]);

  // Close dropdown on outside click and Escape key
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event) {
      if (
        buttonRef.current && !buttonRef.current.contains(event.target) &&
        panelRef.current && !panelRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setIsOpen(false);
        buttonRef.current?.focus();
      }
    }

    document.addEventListener('mousedown', handleClickOutside, true);
    document.addEventListener('touchstart', handleClickOutside, true);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside, true);
      document.removeEventListener('touchstart', handleClickOutside, true);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  // Poll notifications every 60 seconds
  const { data } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => {
      const res = await notificationsApi.getNotifications();
      return res.data;
    },
    refetchInterval: 60000,
  });

  const notifications = data?.notifications || [];
  const unreadCount = data?.unread_count || 0;

  const markReadMutation = useMutation({
    mutationFn: (id) => notificationsApi.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const handleNotificationClick = (notif) => {
    if (!notif.is_read) {
      markReadMutation.mutate(notif.id);
    }
    if (notif.action_url && onNavigateTab) {
      onNavigateTab(notif.action_url);
      setIsOpen(false);
    }
  };

  return (
    <div className="relative inline-flex items-center">
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        title="Notifications"
        aria-label="Notifications"
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        className="relative p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.06] transition flex items-center justify-center cursor-pointer"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 h-4 min-w-4 px-1 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center leading-none shadow-sm animate-pulse">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && typeof document !== 'undefined' &&
        createPortal(
          <div
            ref={panelRef}
            role="dialog"
            aria-label="Notifications Panel"
            style={{
              position: panelStyle.position,
              top: `${panelStyle.top}px`,
              left: `${panelStyle.left}px`,
              width: `${panelStyle.width}px`,
              maxHeight: `${panelStyle.maxHeight}px`,
              zIndex: panelStyle.zIndex,
            }}
            className="flex flex-col rounded-2xl bg-slate-900/95 backdrop-blur-2xl border border-white/10 shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150"
          >
            <div className="p-3.5 sm:p-4 border-b border-white/[0.08] flex items-center justify-between shrink-0 bg-slate-950/40">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-white">Notifications</span>
                {unreadCount > 0 && (
                  <span className="px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 text-xs font-medium border border-indigo-500/30">
                    {unreadCount} new
                  </span>
                )}
              </div>
              {unreadCount > 0 && (
                <button
                  onClick={() => markAllReadMutation.mutate()}
                  className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition cursor-pointer"
                >
                  <CheckCheck className="h-3.5 w-3.5" />
                  Mark all read
                </button>
              )}
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-white/[0.04]">
              {notifications.length === 0 ? (
                <div className="py-10 text-center text-slate-500 text-xs">
                  No notifications right now
                </div>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={`p-3.5 text-left cursor-pointer transition flex items-start gap-3 hover:bg-white/[0.04] ${
                      !n.is_read ? 'bg-indigo-500/[0.06]' : ''
                    }`}
                  >
                    <div
                      className={`h-2 w-2 rounded-full mt-1.5 shrink-0 ${
                        !n.is_read ? 'bg-indigo-400' : 'bg-transparent'
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-semibold text-slate-200 truncate">{n.title}</div>
                      {n.body && (
                        <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">{n.body}</div>
                      )}
                      <div className="text-[10px] text-slate-500 mt-1 font-mono">
                        {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                    {n.action_url && (
                      <ExternalLink className="h-3.5 w-3.5 text-slate-500 mt-1 shrink-0" />
                    )}
                  </div>
                ))
              )}
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}
