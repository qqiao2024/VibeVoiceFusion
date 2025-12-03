'use client';

import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { api } from '@/lib/api';
import { useLanguage } from '@/lib/i18n/LanguageContext';
import type { TrainingMetrics, MetricDataPoint } from '@/types/training';

interface TrainingMetricsChartProps {
  projectId: string;
  jobId: string;
  autoRefresh?: boolean;
  refreshInterval?: number; // milliseconds
}

export default function TrainingMetricsChart({
  projectId,
  jobId,
  autoRefresh = true,
  refreshInterval = 5000,
}: TrainingMetricsChartProps) {
  const { t } = useLanguage();
  const [metrics, setMetrics] = useState<TrainingMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedChart, setSelectedChart] = useState<'loss' | 'learning_rate' | 'timing'>('loss');

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.getTrainingMetrics(projectId, jobId, {
        maxPoints: 500,
        metrics: 'all',
      });
      setMetrics(response.metrics);
    } catch (err) {
      console.error('Error fetching training metrics:', err);
      setError(err instanceof Error ? err.message : 'Failed to load metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();

    if (autoRefresh) {
      const interval = setInterval(fetchMetrics, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [projectId, jobId, autoRefresh, refreshInterval]);

  // Transform data for recharts
  const prepareLossData = () => {
    if (!metrics?.loss) return [];

    // Combine all step-based loss metrics
    const stepMap = new Map<number, any>();

    metrics.loss.train_loss.forEach(point => {
      stepMap.set(point.step, {
        step: point.step,
        total_loss: point.value,
      });
    });

    metrics.loss.train_diffusion_loss.forEach(point => {
      const existing = stepMap.get(point.step) || { step: point.step };
      existing.diffusion_loss = point.value;
      stepMap.set(point.step, existing);
    });

    metrics.loss.train_ce_loss.forEach(point => {
      const existing = stepMap.get(point.step) || { step: point.step };
      existing.ce_loss = point.value;
      stepMap.set(point.step, existing);
    });

    return Array.from(stepMap.values()).sort((a, b) => a.step - b.step);
  };

  const prepareLearningRateData = () => {
    if (!metrics?.learning_rate) return [];
    return metrics.learning_rate.map(point => ({
      step: point.step,
      learning_rate: point.value,
    }));
  };

  const prepareTimingData = () => {
    if (!metrics?.timing) return [];

    const stepMap = new Map<number, any>();

    metrics.timing.step_time.forEach(point => {
      stepMap.set(point.step, {
        step: point.step,
        step_time: point.value,
      });
    });

    metrics.timing.steps_per_second.forEach(point => {
      const existing = stepMap.get(point.step) || { step: point.step };
      existing.steps_per_sec = point.value;
      stepMap.set(point.step, existing);
    });

    return Array.from(stepMap.values()).sort((a, b) => a.step - b.step);
  };

  if (loading && !metrics) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800">
          {t('training.metricsNotAvailable')}: {error}
        </p>
      </div>
    );
  }

  if (!metrics) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Chart Type Selector */}
      <div className="flex gap-2">
        <button
          onClick={() => setSelectedChart('loss')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            selectedChart === 'loss'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          {t('training.lossMetrics')}
        </button>
        <button
          onClick={() => setSelectedChart('learning_rate')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            selectedChart === 'learning_rate'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          {t('training.learningRate')}
        </button>
        <button
          onClick={() => setSelectedChart('timing')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            selectedChart === 'timing'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          {t('training.timingInfo')}
        </button>
      </div>

      {/* Chart Display */}
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        {selectedChart === 'loss' && (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={prepareLossData()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="step"
                label={{ value: 'Step', position: 'insideBottom', offset: -5 }}
              />
              <YAxis label={{ value: 'Loss', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="total_loss"
                stroke="#8884d8"
                name="Total Loss"
                dot={false}
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="diffusion_loss"
                stroke="#82ca9d"
                name="Diffusion Loss"
                dot={false}
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="ce_loss"
                stroke="#ffc658"
                name="CE Loss"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        {selectedChart === 'learning_rate' && (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={prepareLearningRateData()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="step"
                label={{ value: 'Step', position: 'insideBottom', offset: -5 }}
              />
              <YAxis
                label={{ value: 'Learning Rate', angle: -90, position: 'insideLeft' }}
                tickFormatter={(value) => value.toExponential(2)}
              />
              <Tooltip formatter={(value: number) => value.toExponential(4)} />
              <Legend />
              <Line
                type="monotone"
                dataKey="learning_rate"
                stroke="#8884d8"
                name="Learning Rate"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        {selectedChart === 'timing' && (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={prepareTimingData()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="step"
                label={{ value: 'Step', position: 'insideBottom', offset: -5 }}
              />
              <YAxis label={{ value: 'Time (s)', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="step_time"
                stroke="#8884d8"
                name="Step Time (s)"
                dot={false}
                strokeWidth={2}
              />
              {prepareTimingData().some(d => 'steps_per_sec' in d) && (
                <Line
                  type="monotone"
                  dataKey="steps_per_sec"
                  stroke="#82ca9d"
                  name="Steps/Second"
                  dot={false}
                  strokeWidth={2}
                  yAxisId="right"
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Last Update Info */}
      {autoRefresh && (
        <div className="text-xs text-gray-500 text-center">
          {t('training.autoRefreshingEvery')} {refreshInterval / 1000}s
        </div>
      )}
    </div>
  );
}
