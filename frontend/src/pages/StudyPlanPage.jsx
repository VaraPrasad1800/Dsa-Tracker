import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { CalendarCheck, Plus, Sparkles, ArrowLeft } from 'lucide-react';
import { studyPlanApi, progressApi } from '../api/client';
import PlanGeneratorForm from '../components/study_plan/PlanGeneratorForm';
import PlanProgressMetrics from '../components/study_plan/PlanProgressMetrics';
import PlanTimelineCalendar from '../components/study_plan/PlanTimelineCalendar';
import ProblemDetailModal from '../components/problems/ProblemDetailModal';
import { toast } from '../components/common/Toast';

export default function StudyPlanPage() {
  const queryClient = useQueryClient();
  const [showGenerator, setShowGenerator] = useState(false);
  const [selectedProblem, setSelectedProblem] = useState(null);

  const { data: activePlanData, isLoading } = useQuery({
    queryKey: ['active-study-plan'],
    queryFn: async () => {
      const res = await studyPlanApi.getActive();
      return res.data;
    },
  });

  const generateMutation = useMutation({
    mutationFn: async (payload) => {
      const res = await studyPlanApi.generate(payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['active-study-plan']);
      setShowGenerator(false);
      toast.success('Study plan generated successfully! 🎯');
    },
    onError: (err) => {
      toast.error(err?.response?.data?.detail || 'Failed to generate study plan');
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: async (planId) => {
      return await studyPlanApi.deactivate(planId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['active-study-plan']);
      toast('Study plan deactivated', { icon: '⏸️' });
    },
  });

  const updateProgressMutation = useMutation({
    mutationFn: async (payload) => {
      return await progressApi.saveProgress(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['active-study-plan']);
      queryClient.invalidateQueries(['problems']);
      queryClient.invalidateQueries(['due-today']);
      setSelectedProblem(null);
      toast.success('Progress saved');
    },
  });

  const activePlan = activePlanData?.active_plan;
  const progress = activePlanData?.progress;

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center text-slate-400">
        <div className="glass-card rounded-2xl p-12 max-w-md mx-auto space-y-4 skeleton">
          <div className="h-10 w-10 mx-auto rounded-full skeleton" />
          <div className="h-4 w-48 mx-auto rounded skeleton" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-6 space-y-8 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-2">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Deterministic Rule-Based Planner</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <CalendarCheck className="h-7 w-7 text-indigo-400" />
            Personalized Study Plan Engine
          </h1>

          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Automated preparation calendars calibrated to your target interview deadline and daily capacity
          </p>
        </div>
      </div>

      {activePlan && !showGenerator ? (
        <div className="space-y-6">
          <PlanProgressMetrics
            progress={progress}
            plan={activePlan}
            onDeactivate={() => deactivateMutation.mutate(activePlan.id)}
            onRegenerate={() => setShowGenerator(true)}
          />

          <PlanTimelineCalendar
            planDays={activePlan.days || []}
            onSelectProblem={(prob) => setSelectedProblem(prob)}
          />
        </div>
      ) : (
        <div>
          {activePlan && (
            <div className="max-w-2xl mx-auto mb-4">
              <button
                onClick={() => setShowGenerator(false)}
                className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
              >
                <ArrowLeft className="h-3.5 w-3.5" /> Back to active plan
              </button>
            </div>
          )}

          <PlanGeneratorForm
            onGenerate={(data) => generateMutation.mutate(data)}
            loading={generateMutation.isPending}
          />
        </div>
      )}

      {/* Problem Detail Modal */}
      {selectedProblem && (
        <ProblemDetailModal
          problem={selectedProblem}
          onClose={() => setSelectedProblem(null)}
          onSaveProgress={(data) => updateProgressMutation.mutate(data)}
        />
      )}
    </div>
  );
}
