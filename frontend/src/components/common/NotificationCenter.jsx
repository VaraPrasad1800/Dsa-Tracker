import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, CheckCheck, ExternalLink, X } from 'lucide-react';
import { notificationsApi } from '../../api/client';

export default function NotificationCenter({ onNavigateTab }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const queryClient = useQueryClient();

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

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

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
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        title="Notifications"
        className="relative p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.06] transition flex items-center justify-center"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 h-4 min-w-4 px-1 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center leading-none shadow-sm animate-pulse">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-slate-900/95 backdrop-blur-xl border border-white/10 shadow-2xl z-50 overflow-hidden">
          <div className="p-4 border-b border-white/[0.08] flex items-center justify-between">
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
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-[380px] overflow-y-auto divide-y divide-white/[0.04]">
            {notifications.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs">
                No notifications right now
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => handleNotificationClick(n)}
                  className={`p-3.5 text-left cursor-pointer transition flex items-start gap-3 hover:bg-white/[0.03] ${
                    !n.is_read ? 'bg-indigo-500/[0.04]' : ''
                  }`}
                >
                  <div
                    className={`h-2 w-2 rounded-full mt-1.5 shrink-0 ${
                      !n.is_read ? 'bg-indigo-400' : 'bg-transparent'
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-slate-200 truncate">{n.title}</div>
                    {n.body && (
                      <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">{n.body}</div>
                    )}
                    <div className="text-[10px] text-slate-500 mt-1">
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
        </div>
      )}
    </div>
  );
}
