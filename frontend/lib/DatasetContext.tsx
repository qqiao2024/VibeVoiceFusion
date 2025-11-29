"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api, Dataset } from "@/lib/api";

interface DatasetContextType {
  datasets: Dataset[];
  loading: boolean;
  error: string | null;
  refreshDatasets: () => Promise<void>;
  createDataset: (name: string, description: string) => Promise<Dataset>;
  updateDataset: (datasetId: string, name: string, description: string) => Promise<Dataset>;
  deleteDataset: (datasetId: string) => Promise<void>;
  exportDataset: (datasetId: string, datasetName: string) => Promise<void>;
  importDataset: (file: File, name?: string) => Promise<Dataset>;
}

const DatasetContext = createContext<DatasetContextType | undefined>(undefined);

export function DatasetProvider({ children, projectId }: { children: React.ReactNode; projectId: string }) {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load datasets from backend
  const refreshDatasets = useCallback(async () => {
    if (!projectId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.listDatasets(projectId);
      setDatasets(response.datasets);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load datasets";
      setError(errorMessage);
      console.error("Error loading datasets:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  // Load datasets on mount and when projectId changes
  useEffect(() => {
    refreshDatasets();
  }, [refreshDatasets]);

  const createDataset = async (name: string, description: string): Promise<Dataset> => {
    setError(null);

    try {
      const dataset = await api.createDataset(projectId, { name, description });
      setDatasets([...datasets, dataset]);
      return dataset;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to create dataset";
      setError(errorMessage);
      throw err;
    }
  };

  const updateDataset = async (datasetId: string, name: string, description: string): Promise<Dataset> => {
    setError(null);

    try {
      const updatedDataset = await api.updateDataset(projectId, datasetId, { name, description });
      setDatasets(datasets.map(d => d.id === datasetId ? updatedDataset : d));
      return updatedDataset;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to update dataset";
      setError(errorMessage);
      throw err;
    }
  };

  const deleteDataset = async (datasetId: string): Promise<void> => {
    setError(null);

    try {
      await api.deleteDataset(projectId, datasetId);
      setDatasets(datasets.filter(d => d.id !== datasetId));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to delete dataset";
      setError(errorMessage);
      throw err;
    }
  };

  const exportDataset = async (datasetId: string, datasetName: string): Promise<void> => {
    setError(null);

    try {
      const url = api.getDatasetExportUrl(projectId, datasetId);

      // Download the file
      const a = document.createElement('a');
      a.href = url;
      a.download = `${datasetName}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to export dataset";
      setError(errorMessage);
      throw err;
    }
  };

  const importDataset = async (file: File, name?: string): Promise<Dataset> => {
    setError(null);
    setLoading(true);

    try {
      const dataset = await api.importDataset(projectId, { dataset_file: file, name });
      setDatasets([...datasets, dataset]);
      return dataset;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to import dataset";
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const value: DatasetContextType = {
    datasets,
    loading,
    error,
    refreshDatasets,
    createDataset,
    updateDataset,
    deleteDataset,
    exportDataset,
    importDataset,
  };

  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>;
}

export function useDataset(): DatasetContextType {
  const context = useContext(DatasetContext);
  if (!context) {
    throw new Error("useDataset must be used within a DatasetProvider");
  }
  return context;
}
