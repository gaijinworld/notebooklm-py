import React, { useState } from 'react';
import { useAuth } from './AuthContext';
import { Shield, CheckCircle2, Eye, EyeOff } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { signInWithGoogle, signInWithGoogleRedirect, signInWithEmail, register, resetPassword, error, setError, notice, setNotice } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleGoogle = async () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await signInWithGoogle();
    } catch {
      // Handled in AuthContext
    } finally {
      setBusy(false);
    }
  };

  const handleGoogleRedirect = async () => {
    setBusy(true);
    setError(null);
    try {
      await signInWithGoogleRedirect();
    } catch {
      // Handled in AuthContext
    } finally {
      setBusy(false);
    }
  };

  const handleEmailSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter both email and password.');
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await signInWithEmail(email, password);
    } catch {
      // Handled in AuthContext
    } finally {
      setBusy(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter an email and password to create an account.');
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await register(email, password);
      setNotice('Account created successfully!');
    } catch {
      // Handled in AuthContext
    } finally {
      setBusy(false);
    }
  };

  const handleReset = async () => {
    if (!email) {
      setError('Enter your email first to send a password reset.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await resetPassword(email);
    } catch {
      // Handled in AuthContext
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page-container">
      <div className="login-header-box">
        <h1 className="login-title">Sign in to NotebookLM-py</h1>
        <p className="login-subtitle">
          Record speech or create synchronized English dubbing from subtitle files.
        </p>
      </div>

      <div className="login-card-box">
        {notice && <div className="login-notice-banner" role="status">{notice}</div>}
        {error && <div className="login-error-banner" role="alert">{error}</div>}

        <button
          className="login-google-btn"
          onClick={handleGoogle}
          disabled={busy}
        >
          <svg className="google-icon-svg" viewBox="0 0 24 24" width="20" height="20">
            <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"/>
            <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.29v3.15C3.26 21.3 7.31 24 12 24z"/>
            <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.29C.47 8.2.0 10.05.0 12s.47 3.8 1.29 5.42l3.99-3.15z"/>
            <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.58l3.99 3.15c.95-2.83 3.6-4.98 6.72-4.98z"/>
          </svg>
          Continue with Google
        </button>

        <div className="login-divider-text">
          <span>or sign in with email</span>
        </div>

        <form onSubmit={handleEmailSignIn}>
          <div className="form-field-group">
            <label htmlFor="loginEmail">Email</label>
            <input
              id="loginEmail"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={busy}
              required
            />
          </div>

          <div className="form-field-group">
            <label htmlFor="loginPassword">Password</label>
            <div className="password-input-wrap">
              <input
                id="loginPassword"
                type={showPassword ? 'text' : 'password'}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={busy}
                required
              />
              <button
                type="button"
                className="pwd-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                aria-label="Toggle password visibility"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <button type="submit" className="login-btn-primary" disabled={busy}>
            Sign in
          </button>
          <button type="button" className="login-btn-secondary" onClick={handleRegister} disabled={busy}>
            Create account
          </button>
          <button type="button" className="forgot-pwd-link" onClick={handleReset} disabled={busy}>
            Forgot password?
          </button>
        </form>
      </div>

      <div className="info-cards-container">
        <div className="info-card-item">
          <div className="info-card-icon">
            <CheckCircle2 size={20} />
          </div>
          <div className="info-card-text">
            <div>System status: <span className="avail-highlight">Available</span></div>
            <div className="info-card-sub">All systems operational.</div>
          </div>
        </div>

        <div className="info-card-item">
          <div className="info-card-icon">
            <Shield size={20} />
          </div>
          <div className="info-card-text">
            <div><strong>Your jobs and downloads stay private to your account.</strong></div>
            <div className="info-card-sub">We never share your files or data.</div>
          </div>
        </div>
      </div>
    </div>
  );
};
