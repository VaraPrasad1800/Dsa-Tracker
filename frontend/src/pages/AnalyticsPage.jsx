import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { BarChart3, RefreshCw, Sparkles } from 'lucide-react';
import { analyticsApi } from '../api/client';
import ActivityHeatmap from '../components/analytics/ActivityHeatmap';
import TopicStrengthChart from '../components/analytics/TopicStrengthChart';
import DifficultyPieChart from '../components/analytics/DifficultyPieChart';
import StreakCounter from '../components/analytics/StreakCounter';
import ActivityTimeline from '../components/analytics/ActivityTimeline';
import WeakTopicsAlert from '../components/analytics/WeakTopicsAlert';
import MasteryAndRevision from '../components/analytics/MasteryAndRevision';
import { ChartSkeleton } from '../components/common/SkeletonCard';

export default function AnalyticsPage({ onSelectFilterTopic, onSelectProblem }) {
  const [year, setYear] = useState(new Date().getFullYear());

  const { data: heatmapData, isLoading: loadingHeatmap } = useQuery({
    queryKey: ['analytics-heatmap', year],
    queryFn: async () => {
      const res = await analyticsApi.getHeatmap(year);
      return res.data;
    },
  });

  const { data: topicData, isLoading: loadingTopics } = useQuery({
    queryKey: ['analytics-topic-breakdown'],
    queryFn: async () => {
      const res = await analyticsApi.getTopicBreakdown();
      return res.data;
    },
  });

  const { data: streakData, isLoading: loadingStreaks } = useQuery({
    queryKey: ['analytics-streaks'],
    queryFn: async () => {
      const res = await analyticsApi.getStreaks();
      return res.data;
    },
  });

  const { data: difficultyData, isLoading: loadingDifficulty } = useQuery({
    queryKey: ['analytics-difficulty-breakdown'],
    queryFn: async () => {
      const res = await analyticsApi.getDifficultyBreakdown();
      return res.data;
    },
  });

  const { data: timelineData, isLoading: loadingTimeline } = useQuery({
    queryKey: ['analytics-timeline'],
    queryFn: async () => {
      const res = await analyticsApi.getTimeline(90);
      return res.data;
    },
  });

  return (
    <div className="space-y-6 w-full py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-2">
            <Sparkles className="h-3.5 w-3.5" />
            <span>SaaS Performance & Mastery Intelligence</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <BarChart3 className="h-7 w-7 text-indigo-400" />
            <span>Interview Preparation Analytics</span>
          </h1>

          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Retention decay curves, daily solving velocity, and algorithmic pattern readiness
          </p>
        </div>
      </div>

      {/* Streaks row */}
      {loadingStreaks ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="glass-card rounded-2xl p-5 h-28 skeleton" />
          ))}
        </div>
      ) : (
        <StreakCounter streaks={streakData} />
      )}

      {/* Weak Topics Alert */}
      <WeakTopicsAlert topicData={topicData} onSelectTopic={onSelectFilterTopic} />

      {/* Heatmap */}
      {loadingHeatmap ? (
        <div className="glass-card rounded-2xl p-6 h-56 skeleton" />
      ) : (
        <ActivityHeatmap
          heatmapData={heatmapData}
          currentYear={year}
          onYearChange={(newYear) => setYear(newYear)}
        />
      )}

      {/* Two Column Section: Difficulty & Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          {loadingDifficulty ? (
            <div className="glass-card rounded-2xl p-6 h-80 skeleton" />
          ) : (
            <DifficultyPieChart difficultyData={difficultyData} />
          )}
        </div>

        <div className="lg:col-span-2">
          {loadingTimeline ? (
            <div className="glass-card rounded-2xl p-6 h-80 skeleton" />
          ) : (
            <ActivityTimeline timelineData={timelineData} />
          )}
        </div>
      </div>

      {/* Topic Mastery Levels & Priority Revision Queue */}
      <MasteryAndRevision onSelectTopic={onSelectFilterTopic} onSelectProblem={onSelectProblem} />

      {/* Topic Strength Chart */}
      {loadingTopics ? (
        <div className="glass-card rounded-2xl p-6 h-80 skeleton" />
      ) : (
        <TopicStrengthChart topicData={topicData} onTopicClick={onSelectFilterTopic} />
      )}
    </div>
  );
}
