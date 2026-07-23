import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import {
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  sendPasswordResetEmail,
  type User,
} from 'firebase/auth';
import { doc, setDoc, serverTimestamp } from 'firebase/firestore';
import { auth, db, googleProvider } from '../firebase';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  error: string | null;
  notice: string | null;
  setError: (err: string | null) => void;
  setNotice: (notice: string | null) => void;
  signInWithGoogle: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  signOutUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function formatFirebaseError(err: unknown): string {
  const code = (err as { code?: string })?.code || '';
  const map: Record<string, string> = {
    'auth/invalid-email': 'Invalid email address.',
    'auth/user-disabled': 'This account has been disabled.',
    'auth/user-not-found': 'No account found with this email.',
    'auth/wrong-password': 'Incorrect password.',
    'auth/email-already-in-use': 'An account with this email already exists.',
    'auth/weak-password': 'Password should be at least 6 characters.',
    'auth/popup-blocked': 'Popup was blocked by browser. Redirecting to Google sign-in...',
    'auth/cancelled-popup-request': 'Sign-in was cancelled.',
    'auth/operation-not-supported-in-this-environment': 'Popup not supported. Redirecting...',
    'auth/network-request-failed': 'Network error. Check connection and try again.',
    'auth/too-many-requests': 'Too many attempts. Try again later.',
  };
  return map[code] || (err as { message?: string })?.message || 'Authentication error occurred.';
}

async function syncFirestoreArtifact(user: User): Promise<void> {
  try {
    const artifactRef = doc(db, 'artifacts', 'notebooklm-py');
    await setDoc(artifactRef, {
      name: 'notebooklm-py',
      title: 'NotebookLM Py',
      description: 'Google Gemini NotebookLM Py Integration Artifact for Gamified Network Engineer App',
      url: 'http://gaijinworld-local.local/notebooklm-py/',
      status: 'active',
      projectId: 'gamified-network-engineer-app',
      projectNumber: '465331311664',
      parentOrg: 'gaijinworld.com',
      lastUser: user.email || user.uid,
      updatedAt: serverTimestamp()
    }, { merge: true });

    const userRef = doc(db, 'artifacts', 'notebooklm-py', 'users', user.uid);
    await setDoc(userRef, {
      uid: user.uid,
      email: user.email,
      displayName: user.displayName || user.email,
      photoURL: user.photoURL || null,
      signedInAt: serverTimestamp()
    }, { merge: true });
  } catch (err) {
    console.warn('Failed to sync Firestore artifact:', err);
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    getRedirectResult(auth).catch((err) => {
      setError(formatFirebaseError(err));
    });

    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser);
      setLoading(false);
      if (firebaseUser) {
        syncFirestoreArtifact(firebaseUser);
      }
    });

    return () => unsubscribe();
  }, []);

  const signInWithGoogle = useCallback(async () => {
    setError(null);
    setNotice(null);
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err) {
      const code = (err as { code?: string })?.code || '';
      if (['auth/popup-blocked', 'auth/operation-not-supported-in-this-environment', 'auth/cancelled-popup-request'].includes(code)) {
        setNotice('Continuing with Google in full-page sign-in mode...');
        await signInWithRedirect(auth, googleProvider);
        return;
      }
      const detail = formatFirebaseError(err);
      setError(detail);
      throw new Error(detail);
    }
  }, []);

  const signInWithEmail = useCallback(async (email: string, password: string) => {
    setError(null);
    setNotice(null);
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (err) {
      const detail = formatFirebaseError(err);
      setError(detail);
      throw new Error(detail);
    }
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    setError(null);
    setNotice(null);
    try {
      await createUserWithEmailAndPassword(auth, email, password);
    } catch (err) {
      const detail = formatFirebaseError(err);
      setError(detail);
      throw new Error(detail);
    }
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    setError(null);
    setNotice(null);
    try {
      await sendPasswordResetEmail(auth, email);
      setNotice(`Password reset email sent to ${email}`);
    } catch (err) {
      const detail = formatFirebaseError(err);
      setError(detail);
      throw new Error(detail);
    }
  }, []);

  const signOutUser = useCallback(async () => {
    setError(null);
    setNotice(null);
    await signOut(auth);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        notice,
        setError,
        setNotice,
        signInWithGoogle,
        signInWithEmail,
        register,
        resetPassword,
        signOutUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
