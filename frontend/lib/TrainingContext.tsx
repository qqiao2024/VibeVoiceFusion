'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import type { TrainingState, CreateTrainingRequest } from '@/types/training';
import { api } from '@/lib/api';

interface TrainingContextType {
  // State
  states: TrainingState[];
  currentState: TrainingState | null;
  loading: boolean;
  error: string | null;
  stateRefreshInterval: number; // in seconds

  // Actions
  fetchStates: () => Promise<void>;
  fetchCurrentState: () => Promise<void>;
  startTraining: (request: CreateTrainingRequest) => Promise<TrainingState>;
  deleteJob: (jobId: string) => Promise<void>;
  batchDeleteJobs: (jobIds: string[]) => Promise<{ deletedCount: number; failedCount: number }>;
  cancelJob: (jobId: string) => Promise<void>;
  refreshAll: () => Promise<void>;
  clearCurrentState: () => void;
  setStateRefreshInterval: (interval: number) => void;
}

const TrainingContext = createContext<TrainingContextType | undefined>(undefined);

interface TrainingProviderProps {
  children: React.ReactNode;
  projectId: string;
}

export function TrainingProvider({ children, projectId }: TrainingProviderProps) {
  const [states, setStates] = useState<TrainingState[]>([]);
  const [currentState, setCurrentState] = useState<TrainingState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stateRefreshInterval, setStateRefreshInterval] = useState(5); // Default 5 seconds

  // Track previous status to detect transitions
  const previousStatusRef = useRef<string | null>(null);
  // Track the task_id of the training being polled
  const activeTaskIdRef = useRef<string | null>(null);

  // Fetch all training states for the project
  const fetchStates = useCallback(async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);

      const response = await api.listTrainingStates(projectId);

      // Sort by created_at in descending order (newest first)
      const sortedStates = response.states.sort((a, b) => {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
      setStates(sortedStates);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch training states';
      setError(errorMessage);
      console.error('Error fetching training states:', err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  // Fetch current training state
  const fetchCurrentState = useCallback(async () => {
    try {
      const response = await api.getCurrentTrainingState(projectId);
      const newCurrentState = response.state;

      // Check if we had an active job that just completed
      const hadActiveJob = previousStatusRef.current !== null && activeTaskIdRef.current !== null;
      const wasActive = previousStatusRef.current && ['Prepare', 'Training'].includes(previousStatusRef.current);
      const jobNowNull = newCurrentState === null;
      const jobNowCompleted = newCurrentState && ['Completed', 'Failed'].includes(newCurrentState.status);

      // Detect completion: either job became null OR status changed from active to completed/failed
      const justCompleted = hadActiveJob && wasActive && (jobNowNull || jobNowCompleted);

      if (justCompleted) {
        const completedTaskId = activeTaskIdRef.current;

        // Fetch the final state and refresh full history
        if (projectId && completedTaskId) {
          try {
            const finalResponse = await api.getTrainingState(projectId, completedTaskId);
            const finalState = finalResponse.state;

            // Update the state in the list
            setStates(prevStates => {
              const index = prevStates.findIndex(s => s.task_id === completedTaskId);
              if (index !== -1) {
                const updated = [...prevStates];
                updated[index] = finalState;
                return updated;
              }
              return [finalState, ...prevStates];
            });

            // Refresh full history to ensure consistency
            await fetchStates();
          } catch (err) {
            console.error('Error in final poll:', err);
            await fetchStates();
          }
        }

        // Update tracking refs even if job is completed (not null)
        if (jobNowCompleted) {
          previousStatusRef.current = newCurrentState!.status;
          activeTaskIdRef.current = newCurrentState!.task_id;
        } else {
          // Job is null
          previousStatusRef.current = null;
          activeTaskIdRef.current = null;
        }
      }

      setCurrentState(newCurrentState);

      // If there's a current state, update it in the states list without re-fetching
      // (unless we just did a completion refresh above)
      if (newCurrentState && !justCompleted) {
        // Track the status for transition detection
        previousStatusRef.current = newCurrentState.status;
        activeTaskIdRef.current = newCurrentState.task_id;

        setStates(prevStates => {
          const index = prevStates.findIndex(s => s.task_id === newCurrentState.task_id);
          if (index !== -1) {
            // Update existing state in the list
            const updated = [...prevStates];
            updated[index] = newCurrentState;
            return updated;
          }
          // If not found in list, add it at the beginning (newest first)
          return [newCurrentState, ...prevStates];
        });
      }
    } catch (err) {
      console.error('Error fetching current training state:', err);
      setCurrentState(null);
    }
  }, [projectId, fetchStates]);

  // Start a new training job
  const startTraining = useCallback(async (request: CreateTrainingRequest): Promise<TrainingState> => {
    if (!projectId) {
      throw new Error('No project selected');
    }

    try {
      setLoading(true);
      setError(null);

      const response = await api.createTrainingJob(projectId, request);
      const newState = response.state;

      // Update current state immediately
      setCurrentState(newState);

      // Refresh states list
      await fetchStates();

      // Immediately fetch current state to ensure global state is updated
      await fetchCurrentState();

      return newState;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start training';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, fetchStates, fetchCurrentState]);

  // Refresh both current and all states
  const refreshAll = useCallback(async () => {
    await Promise.all([
      fetchStates(),
      fetchCurrentState()
    ]);
  }, [fetchStates, fetchCurrentState]);

  // Delete a training job
  const deleteJob = useCallback(async (jobId: string): Promise<void> => {
    if (!projectId) {
      throw new Error('No project selected');
    }

    try {
      setError(null);
      // Delete from backend first (no optimistic update for batch operations)
      await api.deleteTrainingJob(projectId, jobId);
      // On success, remove from local state
      setStates(prevStates => prevStates.filter(s => s.task_id !== jobId));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete training job';
      setError(errorMessage);
      throw err;
    }
  }, [projectId]);

  // Batch delete training jobs
  const batchDeleteJobs = useCallback(async (jobIds: string[]): Promise<{ deletedCount: number; failedCount: number }> => {
    if (!projectId) {
      throw new Error('No project selected');
    }

    try {
      setError(null);
      // Call backend batch delete API
      const response = await api.batchDeleteTrainingJobs(projectId, jobIds);

      // Remove successfully deleted jobs from local state
      if (response.deleted_ids && response.deleted_ids.length > 0) {
        setStates(prevStates =>
          prevStates.filter(s => !response.deleted_ids.includes(s.task_id))
        );
      }

      return {
        deletedCount: response.deleted_count,
        failedCount: response.failed_count
      };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to batch delete training jobs';
      setError(errorMessage);
      throw err;
    }
  }, [projectId]);

  // Cancel a running training job
  const cancelJob = useCallback(async (jobId: string): Promise<void> => {
    if (!projectId) {
      throw new Error('No project selected');
    }

    try {
      setError(null);
      // TODO: Replace with actual API call when backend is ready
      // await api.cancelTrainingJob(projectId, jobId);
      console.log('Cancel training job:', jobId); // Placeholder until API is implemented

      // Refresh to get updated status
      await refreshAll();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to cancel training job';
      setError(errorMessage);
      throw err;
    }
  }, [projectId, refreshAll]);

  // Clear current state (for dismissing completed/failed training)
  const clearCurrentState = useCallback(() => {
    setCurrentState(null);
    previousStatusRef.current = null;
    activeTaskIdRef.current = null;
  }, []);

  // Initial load
  useEffect(() => {
    if (projectId) {
      refreshAll();
    }
  }, [projectId, refreshAll]);

  // Poll for current state updates (configurable interval when there's an active job)
  // Continue polling for 5 seconds after completion to ensure frontend catches the final state
  useEffect(() => {
    // Only poll if there's an active state
    if (!currentState) {
      return;
    }

    const currentStatus = currentState.status;
    const isActive = ['Prepare', 'Training'].includes(currentStatus);
    const isRecentlyCompleted = ['Completed', 'Failed'].includes(currentStatus);

    // Poll during active training OR for 5 seconds after completion (to catch fast FAKE_MODEL runs)
    if (!isActive && !isRecentlyCompleted) {
      return;
    }

    // Active job - set up polling interval (convert seconds to milliseconds)
    const interval = setInterval(() => {
      fetchCurrentState();
    }, stateRefreshInterval * 1000);

    // If completed/failed, stop polling after 5 seconds
    let completionTimeout: NodeJS.Timeout | null = null;
    if (isRecentlyCompleted) {
      completionTimeout = setTimeout(() => {
        clearInterval(interval);
      }, 5000);
    }

    return () => {
      clearInterval(interval);
      if (completionTimeout) {
        clearTimeout(completionTimeout);
      }
    };
  }, [currentState, fetchCurrentState, stateRefreshInterval]);

  const value: TrainingContextType = {
    states,
    currentState,
    loading,
    error,
    stateRefreshInterval,
    fetchStates,
    fetchCurrentState,
    startTraining,
    deleteJob,
    batchDeleteJobs,
    cancelJob,
    refreshAll,
    clearCurrentState,
    setStateRefreshInterval
  };

  return (
    <TrainingContext.Provider value={value}>
      {children}
    </TrainingContext.Provider>
  );
}

export function useTraining() {
  const context = useContext(TrainingContext);
  if (context === undefined) {
    throw new Error('useTraining must be used within a TrainingProvider');
  }
  return context;
}
