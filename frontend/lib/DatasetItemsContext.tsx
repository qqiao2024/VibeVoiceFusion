"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import { api, DatasetItem } from "@/lib/api";

interface DatasetItemsContextType {
  items: DatasetItem[];
  totalCount: number;
  loading: boolean;
  error: string | null;
  loadItems: (offset: number, limit: number) => Promise<void>;
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
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track loaded ranges to avoid duplicate fetches
  const loadedRangesRef = useRef<Map<string, DatasetItem[]>>(new Map());

  // Load items with pagination
  const loadItems = useCallback(async (offset: number, limit: number) => {
    if (!projectId || !datasetId) return;

    const rangeKey = `${offset}-${limit}`;

    // Check if this range is already loaded
    if (loadedRangesRef.current.has(rangeKey)) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.listDatasetItems(projectId, datasetId, {
        offset,
        limit,
      });

      // Cache the loaded range
      loadedRangesRef.current.set(rangeKey, response.items);

      // Update items - merge with existing items
      setItems((prevItems) => {
        const newItems = [...prevItems];
        response.items.forEach((item, idx) => {
          newItems[offset + idx] = item;
        });
        return newItems;
      });

      setTotalCount(response.total);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load items";
      setError(errorMessage);
      console.error("Error loading items:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId, datasetId]);

  // Refresh all items (clear cache and reload)
  const refreshItems = useCallback(async () => {
    if (!projectId || !datasetId) return;

    // Clear cache
    loadedRangesRef.current.clear();

    setLoading(true);
    setError(null);

    try {
      // Load all items to get accurate count
      const response = await api.listDatasetItems(projectId, datasetId);
      setItems(response.items);
      setTotalCount(response.total);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load items";
      setError(errorMessage);
      console.error("Error loading items:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId, datasetId]);

  // Load initial items on mount
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

      // Clear cache and refresh to get updated list with correct indices
      loadedRangesRef.current.clear();
      await refreshItems();

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

      // Update item in place
      setItems((prevItems) => {
        const newItems = [...prevItems];
        newItems[index] = updatedItem;
        return newItems;
      });

      // Clear cache for affected ranges
      loadedRangesRef.current.clear();

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

      // Clear cache and refresh to get updated list with correct indices
      loadedRangesRef.current.clear();
      await refreshItems();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to delete item";
      setError(errorMessage);
      throw err;
    }
  };

  const value: DatasetItemsContextType = {
    items,
    totalCount,
    loading,
    error,
    loadItems,
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
