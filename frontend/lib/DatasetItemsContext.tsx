"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api, DatasetItem } from "@/lib/api";

const ITEMS_PER_PAGE_KEY_PREFIX = "vibevoice-dataset-items-per-page-";
const DEFAULT_ITEMS_PER_PAGE = 20;

const MIN_ITEMS_PER_PAGE = 1;
const MAX_ITEMS_PER_PAGE = 500;

// Get saved items per page from localStorage for a specific dataset
function getSavedItemsPerPage(datasetId: string): number {
  if (typeof window === "undefined") return DEFAULT_ITEMS_PER_PAGE;
  const saved = localStorage.getItem(ITEMS_PER_PAGE_KEY_PREFIX + datasetId);
  if (saved) {
    const parsed = parseInt(saved, 10);
    if (!isNaN(parsed) && parsed >= MIN_ITEMS_PER_PAGE && parsed <= MAX_ITEMS_PER_PAGE) {
      return parsed;
    }
  }
  return DEFAULT_ITEMS_PER_PAGE;
}

// Save items per page to localStorage for a specific dataset
function saveItemsPerPage(datasetId: string, count: number): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ITEMS_PER_PAGE_KEY_PREFIX + datasetId, count.toString());
}

interface DatasetItemsContextType {
  items: DatasetItem[];
  totalCount: number;
  loading: boolean;
  error: string | null;
  // Pagination
  currentPage: number;
  itemsPerPage: number;
  totalPages: number;
  setCurrentPage: (page: number) => void;
  setItemsPerPage: (count: number) => void;
  // Actions
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

  // Pagination state - initialize from localStorage per dataset
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(() => getSavedItemsPerPage(datasetId));

  const totalPages = Math.max(1, Math.ceil(totalCount / itemsPerPage));

  // Load items for current page
  const loadCurrentPage = useCallback(async () => {
    if (!projectId || !datasetId) return;

    setLoading(true);
    setError(null);

    try {
      const offset = (currentPage - 1) * itemsPerPage;
      const response = await api.listDatasetItems(projectId, datasetId, {
        offset,
        limit: itemsPerPage,
      });

      setItems(response.items);
      setTotalCount(response.total);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load items";
      setError(errorMessage);
      console.error("Error loading items:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId, datasetId, currentPage, itemsPerPage]);

  // Load items when page or pageSize changes
  useEffect(() => {
    loadCurrentPage();
  }, [loadCurrentPage]);

  // Refresh items (reload current page)
  const refreshItems = useCallback(async () => {
    await loadCurrentPage();
  }, [loadCurrentPage]);

  // Handle page change with bounds checking
  const handleSetCurrentPage = useCallback((page: number) => {
    const validPage = Math.max(1, Math.min(page, totalPages));
    setCurrentPage(validPage);
  }, [totalPages]);

  // Handle items per page change - save to localStorage per dataset
  const handleSetItemsPerPage = useCallback((count: number) => {
    setItemsPerPage(count);
    setCurrentPage(1); // Reset to first page when changing page size
    saveItemsPerPage(datasetId, count); // Persist to localStorage
  }, [datasetId]);

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

      // Refresh to get updated list
      await loadCurrentPage();

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

      // Update item in local state
      setItems((prevItems) => {
        const localIndex = index - (currentPage - 1) * itemsPerPage;
        if (localIndex >= 0 && localIndex < prevItems.length) {
          const newItems = [...prevItems];
          newItems[localIndex] = updatedItem;
          return newItems;
        }
        return prevItems;
      });

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

      // Refresh to get updated list with correct indices
      await loadCurrentPage();
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
    currentPage,
    itemsPerPage,
    totalPages,
    setCurrentPage: handleSetCurrentPage,
    setItemsPerPage: handleSetItemsPerPage,
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
