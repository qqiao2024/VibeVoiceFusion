"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { DialogSession, DialogLine, SessionMode } from "@/types/dialog";
import { useProject } from "@/lib/ProjectContext";
import { api } from "@/lib/api";
import type { DialogSession as ApiDialogSession } from "@/lib/api";

interface CreateSessionOptions {
  name: string;
  description: string;
  mode?: SessionMode;
  narratorSpeakerId?: string;
}

interface SessionContextType {
  sessions: DialogSession[];
  currentSession: DialogSession | null;
  selectSession: (sessionId: string) => Promise<void>;
  createSession: (options: CreateSessionOptions) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  updateSession: (sessionId: string, updates: Partial<DialogSession>) => Promise<void>;
  updateSessionDialogs: (sessionId: string, dialogLines: DialogLine[]) => Promise<void>;
  loading: boolean;
  error: string | null;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const { currentProject } = useProject();
  const [sessions, setSessions] = useState<DialogSession[]>([]);
  const [currentSession, setCurrentSession] = useState<DialogSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Helper: Convert backend dialog text to DialogLine array
  const parseDialogText = (
    dialogText: string,
    mode: SessionMode = 'dialogue',
    narratorSpeakerId?: string | null
  ): DialogLine[] => {
    const lines: DialogLine[] = [];
    if (!dialogText.trim()) return lines;

    const textLines = dialogText.trim().split('\n\n');

    if (mode === 'narration' && narratorSpeakerId) {
      // Narration mode: plain text paragraphs, use narrator from metadata
      textLines.forEach((line, index) => {
        const content = line.trim();
        if (content) {
          lines.push({
            id: `line-${Date.now()}-${index}`,
            speakerId: narratorSpeakerId,
            content,
          });
        }
      });
    } else {
      // Dialogue mode: "Speaker N: content" format
      textLines.forEach((line, index) => {
        const match = line.match(/^(Speaker \d+):\s*(.*)$/);
        if (match) {
          lines.push({
            id: `line-${Date.now()}-${index}`,
            speakerId: match[1],
            content: match[2],
          });
        }
      });
    }

    return lines;
  };

  // Helper: Convert DialogLine array to backend dialog text
  const formatDialogText = (dialogLines: DialogLine[], mode: SessionMode = 'dialogue'): string => {
    if (mode === 'narration') {
      // Narration mode: save plain text only, no speaker prefix
      return dialogLines
        .map(line => line.content)
        .join('\n\n');
    }
    // Dialogue mode: "Speaker N: content" format
    return dialogLines
      .map(line => `${line.speakerId}: ${line.content}`)
      .join('\n\n');
  };

  // Helper: Convert backend session to frontend session (without loading text)
  const backendToFrontendMetadata = (apiSession: ApiDialogSession): DialogSession => {
    return {
      id: apiSession.session_id,
      sessionId: apiSession.session_id,
      name: apiSession.name,
      description: apiSession.description,
      textFilename: apiSession.text_filename,
      dialogLines: [], // Empty - will be loaded on demand
      createdAt: new Date(apiSession.created_at),
      updatedAt: new Date(apiSession.updated_at),
      mode: (apiSession.mode || 'dialogue') as SessionMode,
      narratorSpeakerId: apiSession.narrator_speaker_id || null,
    };
  };

  // Helper: Load session text content on demand
  const loadSessionText = async (session: DialogSession, projectId: string): Promise<DialogSession> => {
    // If already loaded (has dialogLines), return as-is
    if (session.dialogLines.length > 0) {
      return session;
    }

    // If no text file, return as-is
    if (!session.textFilename) {
      return session;
    }

    try {
      const textResponse = await api.getSessionText(projectId, session.sessionId);
      // Pass mode and narratorSpeakerId to correctly parse narration vs dialogue
      const dialogLines = parseDialogText(
        textResponse.dialog_text,
        session.mode,
        session.narratorSpeakerId
      );
      return { ...session, dialogLines };
    } catch (err) {
      console.error('Failed to load dialog text:', err);
      return session;
    }
  };

  // Load sessions from backend when project changes
  useEffect(() => {
    const loadSessions = async () => {
      if (!currentProject) {
        setSessions([]);
        setCurrentSession(null);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response = await api.listSessions(currentProject.id);

        // Convert all sessions from backend format (metadata only, no text loading)
        const frontendSessions = response.sessions.map(s => backendToFrontendMetadata(s));

        setSessions(frontendSessions);

        // Restore current session from localStorage or use first session
        const savedCurrentSessionId = localStorage.getItem(`vibevoice_current_session_${currentProject.id}`);
        let selectedSession: DialogSession | null = null;

        if (savedCurrentSessionId) {
          selectedSession = frontendSessions.find((s: DialogSession) => s.id === savedCurrentSessionId) || frontendSessions[0] || null;
        } else {
          selectedSession = frontendSessions[0] || null;
        }

        // Load text content only for the selected session
        if (selectedSession) {
          const sessionWithText = await loadSessionText(selectedSession, currentProject.id);
          // Update the session in the list with loaded text
          setSessions(prev => prev.map(s => s.id === sessionWithText.id ? sessionWithText : s));
          setCurrentSession(sessionWithText);
        } else {
          setCurrentSession(null);
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to load sessions";
        setError(errorMessage);
        console.error("Error loading sessions:", err);
      } finally {
        setLoading(false);
      }
    };

    loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProject]);

  // Save current session ID to localStorage
  useEffect(() => {
    if (currentProject && currentSession) {
      localStorage.setItem(`vibevoice_current_session_${currentProject.id}`, currentSession.id);
    }
  }, [currentSession, currentProject]);

  const selectSession = async (sessionId: string): Promise<void> => {
    if (!currentProject) return;

    setError(null);
    const session = sessions.find((s) => s.id === sessionId);
    if (session) {
      // Load text content if not already loaded
      const sessionWithText = await loadSessionText(session, currentProject.id);

      // Update the session in the list with loaded text (cache it)
      if (sessionWithText.dialogLines.length > 0 && session.dialogLines.length === 0) {
        setSessions(prev => prev.map(s => s.id === sessionWithText.id ? sessionWithText : s));
      }

      setCurrentSession(sessionWithText);
    }
  };

  const createSession = async (options: CreateSessionOptions): Promise<void> => {
    if (!currentProject) {
      throw new Error("No project selected");
    }

    const { name, description, mode = 'dialogue', narratorSpeakerId } = options;

    setLoading(true);
    setError(null);

    try {
      // Create session on backend with empty dialog text
      const newApiSession = await api.createSession(currentProject.id, {
        name,
        description,
        dialog_text: "", // Empty initially
        mode,
        narrator_speaker_id: narratorSpeakerId,
      });

      // Convert to frontend format (no text to load for new empty session)
      const newSession = backendToFrontendMetadata(newApiSession);

      setSessions([...sessions, newSession]);
      setCurrentSession(newSession);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to create session";
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const deleteSession = async (sessionId: string): Promise<void> => {
    if (!currentProject) {
      throw new Error("No project selected");
    }

    if (sessions.length <= 1) {
      throw new Error("Cannot delete the last session");
    }

    setLoading(true);
    setError(null);

    try {
      await api.deleteSession(currentProject.id, sessionId);

      const newSessions = sessions.filter((s) => s.id !== sessionId);
      setSessions(newSessions);

      if (currentSession?.id === sessionId) {
        setCurrentSession(newSessions[0] || null);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to delete session";
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const updateSession = async (sessionId: string, updates: Partial<DialogSession>): Promise<void> => {
    if (!currentProject) {
      throw new Error("No project selected");
    }

    setError(null);

    // Find the existing session to preserve its dialogLines
    const existingSession = sessions.find(s => s.id === sessionId);

    // Update local state immediately for better UX
    const updatedSessions = sessions.map((s) =>
      s.id === sessionId
        ? { ...s, ...updates, updatedAt: new Date() }
        : s
    );
    setSessions(updatedSessions);

    if (currentSession?.id === sessionId) {
      setCurrentSession({ ...currentSession, ...updates, updatedAt: new Date() });
    }

    // Sync name/description/mode/narrator to backend (not dialogLines)
    const hasMetadataUpdates = updates.name !== undefined ||
      updates.description !== undefined ||
      updates.mode !== undefined ||
      updates.narratorSpeakerId !== undefined;

    if (hasMetadataUpdates) {
      try {
        const updateData: {
          name?: string;
          description?: string;
          mode?: SessionMode;
          narrator_speaker_id?: string;
        } = {};
        if (updates.name !== undefined) updateData.name = updates.name;
        if (updates.description !== undefined) updateData.description = updates.description;
        if (updates.mode !== undefined) updateData.mode = updates.mode;
        if (updates.narratorSpeakerId !== undefined) updateData.narrator_speaker_id = updates.narratorSpeakerId ?? undefined;

        const updatedApiSession = await api.updateSession(currentProject.id, sessionId, updateData);

        // Update with backend response metadata, but preserve existing dialogLines
        const updatedMetadata = backendToFrontendMetadata(updatedApiSession);
        const updatedSession: DialogSession = {
          ...updatedMetadata,
          dialogLines: existingSession?.dialogLines || [],
        };

        setSessions(sessions.map(s => s.id === sessionId ? updatedSession : s));
        if (currentSession?.id === sessionId) {
          setCurrentSession(updatedSession);
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to update session";
        setError(errorMessage);
        throw err;
      }
    }
  };

  const updateSessionDialogs = async (sessionId: string, dialogLines: DialogLine[]): Promise<void> => {
    if (!currentProject) {
      throw new Error("No project selected");
    }

    setLoading(true);
    setError(null);

    try {
      // Find session to get its mode
      const session = sessions.find(s => s.id === sessionId);
      const mode = session?.mode || 'dialogue';

      // Convert dialog lines to backend text format (plain text for narration, with speaker prefix for dialogue)
      const dialogText = formatDialogText(dialogLines, mode);

      // Update on backend
      const updatedApiSession = await api.updateSession(currentProject.id, sessionId, {
        dialog_text: dialogText,
      });

      // Update local state with metadata from backend and the dialogLines we just saved
      const updatedMetadata = backendToFrontendMetadata(updatedApiSession);
      const updatedSession: DialogSession = {
        ...updatedMetadata,
        dialogLines, // Use the dialogLines we just saved, no need to re-fetch
      };

      setSessions(sessions.map(s => s.id === sessionId ? updatedSession : s));

      if (currentSession?.id === sessionId) {
        setCurrentSession(updatedSession);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to update dialog";
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return (
    <SessionContext.Provider
      value={{
        sessions,
        currentSession,
        selectSession,
        createSession,
        deleteSession,
        updateSession,
        updateSessionDialogs,
        loading,
        error,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
}

export type { CreateSessionOptions };
