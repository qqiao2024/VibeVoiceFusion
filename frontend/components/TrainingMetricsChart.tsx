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

  // State for toggling loss lines visibility
  const [visibleLossLines, setVisibleLossLines] = useState({
    total_loss: true,
    diffusion_loss: true,
    ce_loss: true,
  });

  // State for toggling timing lines visibility
  const [visibleTimingLines, setVisibleTimingLines] = useState({
    step_time: true,
    steps_per_sec: true,
  });

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

  // Handler for legend click to toggle line visibility
  const handleLegendClick = (e: any) => {
    const dataKey = e.dataKey;
    if (!dataKey || typeof dataKey !== 'string') return;

    if (selectedChart === 'loss') {
      setVisibleLossLines(prev => ({
        ...prev,
        [dataKey]: !prev[dataKey as keyof typeof visibleLossLines],
      }));
    } else if (selectedChart === 'timing') {
      setVisibleTimingLines(prev => ({
        ...prev,
        [dataKey]: !prev[dataKey as keyof typeof visibleTimingLines],
      }));
    }
  };

  // Custom legend formatter to show active/inactive state
  const renderLegend = (props: any) => {
    const { payload } = props;
    if (!payload) return null;

    const visibleLines = selectedChart === 'loss' ? visibleLossLines :
                        selectedChart === 'timing' ? visibleTimingLines : null;

    return (
      <ul className="flex justify-center gap-4 flex-wrap" style={{ listStyle: 'none', padding: 0 }}>
        {payload.map((entry: any, index: number) => {
          const isVisible = visibleLines ? visibleLines[entry.dataKey as keyof typeof visibleLines] : true;
          return (
            <li
              key={`item-${index}`}
              onClick={() => handleLegendClick(entry)}
              style={{
                cursor: 'pointer',
                opacity: isVisible ? 1 : 0.4,
                textDecoration: isVisible ? 'none' : 'line-through',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span
                style={{
                  display: 'inline-block',
                  width: '12px',
                  height: '12px',
                  backgroundColor: entry.color,
                  opacity: isVisible ? 1 : 0.3,
                }}
              />
              <span style={{ fontSize: '14px' }}>{entry.value}</span>
            </li>
          );
        })}
      </ul>
    );
  };

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
          <>
            <div className="mb-3 text-xs text-gray-500 italic">
              {t('training.clickLegendToToggle')}
            </div>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={prepareLossData()} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="step"
                  label={{ value: 'Step', position: 'insideBottomRight', offset: 0 }}
                />
                <YAxis label={{ value: 'Loss', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend content={renderLegend} />
                <Line
                  type="monotone"
                  dataKey="total_loss"
                  stroke="#8884d8"
                  name="Total Loss"
                  dot={false}
                  strokeWidth={2}
                  hide={!visibleLossLines.total_loss}
                />
                <Line
                  type="monotone"
                  dataKey="diffusion_loss"
                  stroke="#82ca9d"
                  name="Diffusion Loss"
                  dot={false}
                  strokeWidth={2}
                  hide={!visibleLossLines.diffusion_loss}
                />
                <Line
                  type="monotone"
                  dataKey="ce_loss"
                  stroke="#ffc658"
                  name="CE Loss"
                  dot={false}
                  strokeWidth={2}
                  hide={!visibleLossLines.ce_loss}
                />
              </LineChart>
            </ResponsiveContainer>
          </>
        )}

        {selectedChart === 'learning_rate' && (
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={prepareLearningRateData()} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="step"
                label={{ value: 'Step', position: 'insideBottomRight', offset: 0 }}
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
          <>
            <div className="mb-3 text-xs text-gray-500 italic">
              {t('training.clickLegendToToggle')}
            </div>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={prepareTimingData()} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="step"
                  label={{ value: 'Step', position: 'insideBottomRight', offset: 0 }}
                />
                <YAxis label={{ value: 'Time (s)', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend content={renderLegend} />
                <Line
                  type="monotone"
                  dataKey="step_time"
                  stroke="#8884d8"
                  name="Step Time (s)"
                  dot={false}
                  strokeWidth={2}
                  hide={!visibleTimingLines.step_time}
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
                    hide={!visibleTimingLines.steps_per_sec}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </>
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
