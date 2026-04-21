import { Injectable, signal, computed } from '@angular/core';

// ============================================================================
// INTERFACES
// ============================================================================

export interface Annotation {
  id: number;
  startTime: number;
  endTime: number;
  label: string;
  aiModel: 'car_detector' | 'noisy_car_detector';
  note: string;
  dbPeak?: number;
  qualityScore?: number;
  validated?: boolean;
}

export interface AnnotationSession {
  id: string;
  fileName: string;
  fileSize: number;
  annotations: Annotation[];
  currentTime: number;
  currentAiModel: 'car_detector' | 'noisy_car_detector';
  savedAt: string;
  s3Key?: string;
  duration?: number;
}

// Command pattern for Undo/Redo
interface Command {
  type: 'add' | 'remove' | 'update';
  annotation: Annotation;
  index?: number;
  previousAnnotation?: Annotation;
  timestamp: number;
}

// ============================================================================
// INDEXEDDB CONFIGURATION
// ============================================================================

const DB_NAME = 'quantnuis_annotations';
const DB_VERSION = 1;
const STORE_SESSIONS = 'sessions';
const STORE_HISTORY = 'history';

// ============================================================================
// SERVICE
// ============================================================================

@Injectable({
  providedIn: 'root'
})
export class AnnotationPersistenceService {
  private db: IDBDatabase | null = null;
  private undoStack: Command[] = [];
  private redoStack: Command[] = [];
  private autoSaveInterval: ReturnType<typeof setInterval> | null = null;
  private currentSessionId: string | null = null;

  // Reactive signals for UI
  private _lastSaved = signal<Date | null>(null);
  private _isSaving = signal<boolean>(false);
  private _canUndo = signal<boolean>(false);
  private _canRedo = signal<boolean>(false);
  private _undoCount = signal<number>(0);
  private _redoCount = signal<number>(0);

  // Public readonly signals
  readonly lastSaved = this._lastSaved.asReadonly();
  readonly isSaving = this._isSaving.asReadonly();
  readonly canUndo = this._canUndo.asReadonly();
  readonly canRedo = this._canRedo.asReadonly();
  readonly undoCount = this._undoCount.asReadonly();
  readonly redoCount = this._redoCount.asReadonly();

  // Computed signal for "saved X seconds ago" display
  readonly timeSinceLastSave = computed(() => {
    const saved = this._lastSaved();
    if (!saved) return null;
    return Math.floor((Date.now() - saved.getTime()) / 1000);
  });

  constructor() {
    this.initDatabase();
  }

  // ============================================================================
  // DATABASE INITIALIZATION
  // ============================================================================

  private async initDatabase(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => {
        console.error('IndexedDB error:', request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // Sessions store
        if (!db.objectStoreNames.contains(STORE_SESSIONS)) {
          const sessionsStore = db.createObjectStore(STORE_SESSIONS, { keyPath: 'id' });
          sessionsStore.createIndex('fileName', 'fileName', { unique: false });
          sessionsStore.createIndex('savedAt', 'savedAt', { unique: false });
        }

        // History store (for undo/redo persistence across page reloads)
        if (!db.objectStoreNames.contains(STORE_HISTORY)) {
          const historyStore = db.createObjectStore(STORE_HISTORY, { keyPath: 'sessionId' });
          historyStore.createIndex('timestamp', 'timestamp', { unique: false });
        }
      };
    });
  }

  private async ensureDatabase(): Promise<IDBDatabase> {
    if (!this.db) {
      await this.initDatabase();
    }
    return this.db!;
  }

  // ============================================================================
  // SESSION MANAGEMENT
  // ============================================================================

  generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  startSession(fileName: string, fileSize: number, s3Key?: string): string {
    this.currentSessionId = this.generateSessionId();
    this.undoStack = [];
    this.redoStack = [];
    this.updateUndoRedoState();

    // Start auto-save every 30 seconds
    this.startAutoSave();

    return this.currentSessionId;
  }

  endSession(): void {
    this.stopAutoSave();
    this.currentSessionId = null;
    this.undoStack = [];
    this.redoStack = [];
    this.updateUndoRedoState();
    this._lastSaved.set(null);
  }

  // ============================================================================
  // AUTO-SAVE
  // ============================================================================

  private startAutoSave(): void {
    this.stopAutoSave();
    this.autoSaveInterval = setInterval(() => {
      // The component will call saveSession when this triggers
      // We just update the "last saved" indicator periodically
    }, 30000);
  }

  private stopAutoSave(): void {
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
      this.autoSaveInterval = null;
    }
  }

  // ============================================================================
  // SAVE / LOAD OPERATIONS
  // ============================================================================

  async saveSession(session: AnnotationSession): Promise<void> {
    if (!session.annotations.length && !session.s3Key) {
      return; // Don't save empty sessions without S3 key
    }

    this._isSaving.set(true);

    try {
      const db = await this.ensureDatabase();

      return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORE_SESSIONS], 'readwrite');
        const store = transaction.objectStore(STORE_SESSIONS);

        session.savedAt = new Date().toISOString();
        const request = store.put(session);

        request.onsuccess = () => {
          this._lastSaved.set(new Date());
          this._isSaving.set(false);

          // Also save to localStorage as backup
          try {
            localStorage.setItem('quantnuis_annotation_session', JSON.stringify(session));
          } catch (e) {
            console.warn('localStorage backup failed:', e);
          }

          resolve();
        };

        request.onerror = () => {
          this._isSaving.set(false);
          console.error('Save error:', request.error);

          // Fallback to localStorage
          try {
            localStorage.setItem('quantnuis_annotation_session', JSON.stringify(session));
            this._lastSaved.set(new Date());
          } catch (e) {
            console.error('localStorage fallback also failed:', e);
          }

          reject(request.error);
        };
      });
    } catch (error) {
      this._isSaving.set(false);
      // Fallback to localStorage
      try {
        localStorage.setItem('quantnuis_annotation_session', JSON.stringify(session));
        this._lastSaved.set(new Date());
      } catch (e) {
        console.error('All save methods failed:', e);
      }
      throw error;
    }
  }

  async loadLatestSession(): Promise<AnnotationSession | null> {
    try {
      const db = await this.ensureDatabase();

      return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORE_SESSIONS], 'readonly');
        const store = transaction.objectStore(STORE_SESSIONS);
        const index = store.index('savedAt');

        // Get the most recent session
        const request = index.openCursor(null, 'prev');

        request.onsuccess = () => {
          const cursor = request.result;
          if (cursor) {
            const session = cursor.value as AnnotationSession;
            // Only return if it has annotations
            if (session.annotations && session.annotations.length > 0) {
              resolve(session);
              return;
            }
          }

          // Fallback to localStorage
          const localSession = this.loadFromLocalStorage();
          resolve(localSession);
        };

        request.onerror = () => {
          console.error('Load error:', request.error);
          // Fallback to localStorage
          const localSession = this.loadFromLocalStorage();
          resolve(localSession);
        };
      });
    } catch (error) {
      console.error('Database error, falling back to localStorage:', error);
      return this.loadFromLocalStorage();
    }
  }

  private loadFromLocalStorage(): AnnotationSession | null {
    try {
      const saved = localStorage.getItem('quantnuis_annotation_session');
      if (saved) {
        const session = JSON.parse(saved) as AnnotationSession;
        if (session.annotations && session.annotations.length > 0) {
          return session;
        }
      }
    } catch (e) {
      console.error('localStorage load error:', e);
    }
    return null;
  }

  async clearSession(sessionId?: string): Promise<void> {
    try {
      const db = await this.ensureDatabase();

      return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORE_SESSIONS, STORE_HISTORY], 'readwrite');
        const sessionsStore = transaction.objectStore(STORE_SESSIONS);
        const historyStore = transaction.objectStore(STORE_HISTORY);

        if (sessionId) {
          sessionsStore.delete(sessionId);
          historyStore.delete(sessionId);
        } else {
          sessionsStore.clear();
          historyStore.clear();
        }

        transaction.oncomplete = () => {
          localStorage.removeItem('quantnuis_annotation_session');
          resolve();
        };

        transaction.onerror = () => {
          reject(transaction.error);
        };
      });
    } catch (error) {
      // Still clear localStorage
      localStorage.removeItem('quantnuis_annotation_session');
    }
  }

  // ============================================================================
  // UNDO / REDO SYSTEM
  // ============================================================================

  recordAdd(annotation: Annotation): void {
    const command: Command = {
      type: 'add',
      annotation: { ...annotation },
      timestamp: Date.now()
    };

    this.undoStack.push(command);
    this.redoStack = []; // Clear redo stack on new action
    this.trimUndoStack();
    this.updateUndoRedoState();
  }

  recordRemove(annotation: Annotation, index: number): void {
    const command: Command = {
      type: 'remove',
      annotation: { ...annotation },
      index,
      timestamp: Date.now()
    };

    this.undoStack.push(command);
    this.redoStack = [];
    this.trimUndoStack();
    this.updateUndoRedoState();
  }

  recordUpdate(oldAnnotation: Annotation, newAnnotation: Annotation): void {
    const command: Command = {
      type: 'update',
      annotation: { ...newAnnotation },
      previousAnnotation: { ...oldAnnotation },
      timestamp: Date.now()
    };

    this.undoStack.push(command);
    this.redoStack = [];
    this.trimUndoStack();
    this.updateUndoRedoState();
  }

  /**
   * Performs undo operation and returns the action to apply
   */
  undo(annotations: Annotation[]): { action: 'add' | 'remove' | 'update'; annotation: Annotation; index?: number; newAnnotations: Annotation[] } | null {
    const command = this.undoStack.pop();
    if (!command) return null;

    this.redoStack.push(command);
    this.updateUndoRedoState();

    let newAnnotations = [...annotations];
    let result: { action: 'add' | 'remove' | 'update'; annotation: Annotation; index?: number; newAnnotations: Annotation[] };

    switch (command.type) {
      case 'add':
        // Undo add = remove
        const addIndex = newAnnotations.findIndex(a => a.id === command.annotation.id);
        if (addIndex !== -1) {
          newAnnotations.splice(addIndex, 1);
        }
        result = { action: 'remove', annotation: command.annotation, index: addIndex, newAnnotations };
        break;

      case 'remove':
        // Undo remove = add back at original position
        if (command.index !== undefined && command.index <= newAnnotations.length) {
          newAnnotations.splice(command.index, 0, command.annotation);
        } else {
          newAnnotations.push(command.annotation);
        }
        newAnnotations.sort((a, b) => a.startTime - b.startTime);
        result = { action: 'add', annotation: command.annotation, newAnnotations };
        break;

      case 'update':
        // Undo update = restore previous
        const updateIndex = newAnnotations.findIndex(a => a.id === command.annotation.id);
        if (updateIndex !== -1 && command.previousAnnotation) {
          newAnnotations[updateIndex] = { ...command.previousAnnotation };
        }
        result = { action: 'update', annotation: command.previousAnnotation!, newAnnotations };
        break;

      default:
        return null;
    }

    return result;
  }

  /**
   * Performs redo operation and returns the action to apply
   */
  redo(annotations: Annotation[]): { action: 'add' | 'remove' | 'update'; annotation: Annotation; index?: number; newAnnotations: Annotation[] } | null {
    const command = this.redoStack.pop();
    if (!command) return null;

    this.undoStack.push(command);
    this.updateUndoRedoState();

    let newAnnotations = [...annotations];
    let result: { action: 'add' | 'remove' | 'update'; annotation: Annotation; index?: number; newAnnotations: Annotation[] };

    switch (command.type) {
      case 'add':
        // Redo add = add again
        newAnnotations.push(command.annotation);
        newAnnotations.sort((a, b) => a.startTime - b.startTime);
        result = { action: 'add', annotation: command.annotation, newAnnotations };
        break;

      case 'remove':
        // Redo remove = remove again
        const removeIndex = newAnnotations.findIndex(a => a.id === command.annotation.id);
        if (removeIndex !== -1) {
          newAnnotations.splice(removeIndex, 1);
        }
        result = { action: 'remove', annotation: command.annotation, index: removeIndex, newAnnotations };
        break;

      case 'update':
        // Redo update = apply new value
        const updateIndex = newAnnotations.findIndex(a => a.id === command.previousAnnotation?.id);
        if (updateIndex !== -1) {
          newAnnotations[updateIndex] = { ...command.annotation };
        }
        result = { action: 'update', annotation: command.annotation, newAnnotations };
        break;

      default:
        return null;
    }

    return result;
  }

  private trimUndoStack(): void {
    // Keep max 100 undo actions
    const MAX_UNDO = 100;
    if (this.undoStack.length > MAX_UNDO) {
      this.undoStack = this.undoStack.slice(-MAX_UNDO);
    }
  }

  private updateUndoRedoState(): void {
    this._canUndo.set(this.undoStack.length > 0);
    this._canRedo.set(this.redoStack.length > 0);
    this._undoCount.set(this.undoStack.length);
    this._redoCount.set(this.redoStack.length);
  }

  getUndoDescription(): string | null {
    const command = this.undoStack[this.undoStack.length - 1];
    if (!command) return null;

    switch (command.type) {
      case 'add':
        return `Annuler: Ajouter annotation "${this.getLabelText(command.annotation.label)}"`;
      case 'remove':
        return `Annuler: Supprimer annotation "${this.getLabelText(command.annotation.label)}"`;
      case 'update':
        return `Annuler: Modifier annotation`;
      default:
        return 'Annuler';
    }
  }

  getRedoDescription(): string | null {
    const command = this.redoStack[this.redoStack.length - 1];
    if (!command) return null;

    switch (command.type) {
      case 'add':
        return `Refaire: Ajouter annotation "${this.getLabelText(command.annotation.label)}"`;
      case 'remove':
        return `Refaire: Supprimer annotation "${this.getLabelText(command.annotation.label)}"`;
      case 'update':
        return `Refaire: Modifier annotation`;
      default:
        return 'Refaire';
    }
  }

  private getLabelText(label: string): string {
    const labels: Record<string, string> = {
      'car': 'Vehicule',
      'noisy_car': 'Vehicule bruyant',
      'noise': 'Bruit',
      'other': 'Autre'
    };
    return labels[label] || label;
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  formatTimeSinceLastSave(): string {
    const seconds = this.timeSinceLastSave();
    if (seconds === null) return '';

    if (seconds < 5) return 'Sauvegarde en cours...';
    if (seconds < 60) return `Sauvegarde il y a ${seconds}s`;
    if (seconds < 3600) return `Sauvegarde il y a ${Math.floor(seconds / 60)}min`;
    return `Sauvegarde il y a ${Math.floor(seconds / 3600)}h`;
  }

  /**
   * Force immediate save (for critical moments)
   */
  async forceSave(session: AnnotationSession): Promise<void> {
    return this.saveSession(session);
  }
}
