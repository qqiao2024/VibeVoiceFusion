'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import type { TrainingJob, CreateTrainingRequest } from '@/types/training';
import { TrainingStatus } from '@/types/training';

interface TrainingContextType {
  // State
  jobs: TrainingJob[];
  currentJob: TrainingJob | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchJobs: () => Promise<void>;
  fetchCurrentJob: () => Promise<void>;
  startTraining: (request: CreateTrainingRequest) => Promise<TrainingJob>;
  deleteJob: (jobId: string) => Promise<void>;
  cancelJob: (jobId: string) => Promise<void>;
  refreshAll: () => Promise<void>;
}

const TrainingContext = createContext<TrainingContextType | undefined>(undefined);

interface TrainingProviderProps {
  children: React.ReactNode;
  projectId: string;
}

export function TrainingProvider({ children, projectId }: TrainingProviderProps) {
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [currentJob, setCurrentJob] = useState<TrainingJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track previous status to detect transitions
  const previousStatusRef = useRef<TrainingStatus | null>(null);
  // Track the job_id of the training being polled
  const activeJobIdRef = useRef<string | null>(null);

  // Fetch all training jobs for the project
  const fetchJobs = useCallback(async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);

      // TODO: Replace with actual API call when backend is ready
      // const response = await api.listTrainingJobs(projectId);
      // Mock data for now
      const mockJobs: TrainingJob[] = [];

      // Sort by created_at in descending order (newest first)
      const sortedJobs = mockJobs.sort((a, b) => {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
      setJobs(sortedJobs);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch training jobs';
      setError(errorMessage);
      console.error('Error fetching training jobs:', err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  // Fetch current training job status
  const fetchCurrentJob = useCallback(async () => {
    try {
      // TODO: Replace with actual API call when backend is ready
      // const response = await api.getCurrentTrainingJob();
      // Mock data for now - using type assertion to preserve TrainingJob | null type
      const newCurrentJob = null as TrainingJob | null;

      // Check if we had an active job that just completed (became null)
      const hadActiveJob = previousStatusRef.current !== null && activeJobIdRef.current !== null;
      const jobNowNull = newCurrentJob === null;

      // If we had an active job and now it's null, it completed!
      if (hadActiveJob && jobNowNull) {
        const completedJobId = activeJobIdRef.current;

        // Do final poll to get the completed state
        if (projectId && completedJobId) {
          try {
            // TODO: Replace with actual API call
            // const finalResponse = await api.getTrainingJob(projectId, completedJobId);
            // const finalJob = finalResponse.job;

            // Update the job in the list
            // setJobs(prevJobs => {
            //   const index = prevJobs.findIndex(j => j.job_id === completedJobId);
            //   if (index !== -1) {
            //     const updated = [...prevJobs];
            //     updated[index] = finalJob;
            //     return updated;
            //   }
            //   return [finalJob, ...prevJobs];
            // });

            // Refresh full history
            await fetchJobs();
          } catch (err) {
            console.error('Error in final poll:', err);
            await fetchJobs();
          }
        }

        // Clear tracking refs
        previousStatusRef.current = null;
        activeJobIdRef.current = null;
      }

      setCurrentJob(newCurrentJob);

      // If there's a current job, update it in the jobs list without re-fetching
      if (newCurrentJob) {
        // Track the status for transition detection
        previousStatusRef.current = newCurrentJob.status;
        activeJobIdRef.current = newCurrentJob.job_id;

        setJobs(prevJobs => {
          const index = prevJobs.findIndex(j => j.job_id === newCurrentJob.job_id);
          if (index !== -1) {
            // Update existing job in the list
            const updated = [...prevJobs];
            updated[index] = newCurrentJob;
            return updated;
          }
          // If not found in list, add it at the beginning (newest first)
          return [newCurrentJob, ...prevJobs];
        });
      }
    } catch (err) {
      console.error('Error fetching current training job:', err);
      setCurrentJob(null);
    }
  }, [projectId, fetchJobs]);

  // Start a new training job
  const startTraining = useCallback(async (request: CreateTrainingRequest): Promise<TrainingJob> => {
    if (!projectId) {
      throw new Error('No project selected');
    }

    try {
      setLoading(true);
      setError(null);

      // TODO: Replace with actual API call when backend is ready
      // const response = await api.createTrainingJob(projectId, request);

      // Mock response for now
      const mockJob: TrainingJob = {
        job_id: `job_${Date.now()}`,
        job_name: request.job_name,
        status: TrainingStatus.PENDING,
        config: {
          lora_name: request.config.lora_name || 'vibevoice_lora',
          epochs: request.config.epochs || 10,
          batch_size: request.config.batch_size || 1,
          learning_rate: request.config.learning_rate || 1e-4,
          dataset_path: request.config.dataset_path || null,
          output_dir: request.config.output_dir || './lora_output',
          multiplier: request.config.multiplier || 1.0,
          lora_dim: request.config.lora_dim || 4,
          lora_alpha: request.config.lora_alpha || null,
          lora_dropout: request.config.lora_dropout || null,
          model_path: request.config.model_path || null,
          number_of_layers: request.config.number_of_layers || 0,
          dtype: request.config.dtype || 'bfloat16',
          model_config_path: request.config.model_config_path || null,
          optimizer_type: request.config.optimizer_type || 'AdamW8bit',
          optimizer_args: request.config.optimizer_args || null,
          seeds: request.config.seeds || 42,
          dataset_repeats: request.config.dataset_repeats || 1,
          speech_compress_ratio: request.config.speech_compress_ratio || 3200,
          semantic_dim: request.config.semantic_dim || 128,
          diffusion_loss_weight: request.config.diffusion_loss_weight || 10.4,
          ce_loss_weight: request.config.ce_loss_weight || 0.004,
          device: request.config.device || 'cuda',
          gradient_accumulation_steps: request.config.gradient_accumulation_steps || 16,
          dataload_workers: request.config.dataload_workers || 2,
          save_model_per_num_epoch: request.config.save_model_per_num_epoch || 10,
        },
        created_at: new Date().toISOString(),
        started_at: null,
        completed_at: null,
        metrics: null,
        final_loss: null,
        final_ce_loss: null,
        final_diffusion_loss: null,
        total_steps: null,
        total_epochs: null,
        total_training_time: null,
        saved_lora_files: [],
        error_message: null,
        project_id: projectId,
      };

      // Update current job immediately
      setCurrentJob(mockJob);

      // Refresh jobs list
      await fetchJobs();

      // Immediately fetch current job to ensure global state is updated
      await fetchCurrentJob();

      return mockJob;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start training';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, fetchJobs, fetchCurrentJob]);

  // Delete a training job
  const deleteJob = useCallback(async (jobId: string): Promise<void> => {
    if (!projectId) {
      throw new Error('No project selected');
    }

    // Optimistic update - remove from local state immediately
    const previousJobs = jobs;
    setJobs(prevJobs => prevJobs.filter(j => j.job_id !== jobId));

    try {
      setError(null);
      // TODO: Replace with actual API call when backend is ready
      // await api.deleteTrainingJob(projectId, jobId);
      // Success - the item is already removed from UI
    } catch (err) {
      // Rollback on error - restore the previous state
      setJobs(previousJobs);
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete training job';
      setError(errorMessage);
      throw err;
    }
  }, [projectId, jobs]);

  // Cancel a running training job
  const cancelJob = useCallback(async (jobId: string): Promise<void> => {
    if (!projectId) {
      throw new Error('No project selected');
    }

    try {
      setError(null);
      // TODO: Replace with actual API call when backend is ready
      // await api.cancelTrainingJob(projectId, jobId);

      // Refresh to get updated status
      await refreshAll();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to cancel training job';
      setError(errorMessage);
      throw err;
    }
  }, [projectId]);

  // Refresh both current and all jobs
  const refreshAll = useCallback(async () => {
    await Promise.all([
      fetchJobs(),
      fetchCurrentJob()
    ]);
  }, [fetchJobs, fetchCurrentJob]);

  // Initial load
  useEffect(() => {
    if (projectId) {
      refreshAll();
    }
  }, [projectId, refreshAll]);

  // Poll for current job updates (every 2 seconds when there's an active job)
  useEffect(() => {
    // Only poll if there's an active job
    if (!currentJob) {
      return;
    }

    const currentStatus = currentJob.status;
    const isActive = [
      TrainingStatus.PENDING,
      TrainingStatus.INITIALIZING,
      TrainingStatus.TRAINING,
      TrainingStatus.SAVING
    ].includes(currentStatus);

    if (!isActive) {
      return;
    }

    // Active job - set up polling interval
    const interval = setInterval(() => {
      fetchCurrentJob();
    }, 2000);

    return () => clearInterval(interval);
  }, [currentJob, fetchCurrentJob]);

  const value: TrainingContextType = {
    jobs,
    currentJob,
    loading,
    error,
    fetchJobs,
    fetchCurrentJob,
    startTraining,
    deleteJob,
    cancelJob,
    refreshAll
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
