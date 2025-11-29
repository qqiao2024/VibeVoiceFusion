"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api, DatasetItem } from "@/lib/api";

interface DatasetItemsContextType {
  items: DatasetItem[];
  loading: boolean;
  error: string | null;
  refreshItems: () => Promise<void>;
  createItem: (text: string, audioFile: File, voicePromptFiles: File[]) => Promise<DatasetItem>;
  updateItem: (index: number, text?: string, audioFile?: File, voicePromptFiles?: File[]) => Promise<DatasetItem>;
  deleteItem: (index: number) => Promise<void>;
}

const DatasetItemsContext = createContext<DatasetItemsContextType | undefined>(undefined);

export function DatasetItemsProvider({
  children,
  projectId,
  datasetId,
}: {
  children: React.ReactNode;
  projectId: string;
  datasetId: string;
}) {
  const [items, setItems] = useState<DatasetItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load items from backend
  const refreshItems = useCallback(async () => {
    if (!projectId || !datasetId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.listDatasetItems(projectId, datasetId);
      setItems(response.items);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load items";
      setError(errorMessage);
      console.error("Error loading items:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId, datasetId]);

  // Load items on mount and when projectId/datasetId changes
  useEffect(() => {
    refreshItems();
  }, [refreshItems]);

  const createItem = async (
    text: string,
    audioFile: File,
    voicePromptFiles: File[]
  ): Promise<DatasetItem> => {
    setError(null);

    try {
      const item = await api.createDatasetItem(projectId, datasetId, {
        text,
        audio_file: audioFile,
        voice_prompt_files: voicePromptFiles,
      });
      setItems([...items, item]);
      return item;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to create item";
      setError(errorMessage);
      throw err;
    }
  };

  const updateItem = async (
    index: number,
    text?: string,
    audioFile?: File,
    voicePromptFiles?: File[]
  ): Promise<DatasetItem> => {
    setError(null);

    try {
      const updatedItem = await api.updateDatasetItem(projectId, datasetId, index, {
        text,
        audio_file: audioFile,
        voice_prompt_files: voicePromptFiles,
      });
      setItems(items.map((item, i) => (i === index ? updatedItem : item)));
      return updatedItem;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to update item";
      setError(errorMessage);
      throw err;
    }
  };

  const deleteItem = async (index: number): Promise<void> => {
    setError(null);

    try {
      await api.deleteDatasetItem(projectId, datasetId, index);
      setItems(items.filter((_, i) => i !== index));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to delete item";
      setError(errorMessage);
      throw err;
    }
  };

  const value: DatasetItemsContextType = {
    items,
    loading,
    error,
    refreshItems,
    createItem,
    updateItem,
    deleteItem,
  };

  return <DatasetItemsContext.Provider value={value}>{children}</DatasetItemsContext.Provider>;
}

export function useDatasetItems(): DatasetItemsContextType {
  const context = useContext(DatasetItemsContext);
  if (!context) {
    throw new Error("useDatasetItems must be used within a DatasetItemsProvider");
  }
  return context;
}
