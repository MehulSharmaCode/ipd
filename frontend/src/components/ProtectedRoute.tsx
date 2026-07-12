import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import api from '@/lib/api';
import { Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireProfile?: boolean;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requireProfile = true }) => {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [profileComplete, setProfileComplete] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setAuthenticated(false);
        setLoading(false);
        return;
      }

      try {
        const res = await api.get('/farmers/me');
        setAuthenticated(true);
        
        // Profile is considered complete if they finished the wizard
        // Fallback for legacy profiles: check explicit verification flags
        const isComplete = res.data.profile_wizard_complete === true || 
                          (res.data.is_aadhar_verified && res.data.is_pan_verified);
        
        setProfileComplete(isComplete);
      } catch (err) {
        console.error("Auth check failed:", err);
        setAuthenticated(false);
        localStorage.removeItem('access_token');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [location.pathname]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  if (!authenticated) {
    return <Navigate to="/auth" state={{ from: location }} replace />;
  }

  // If we are on /profile-setup and profile is already complete, go to dashboard
  if (location.pathname === '/profile-setup' && profileComplete) {
    return <Navigate to="/dashboard" replace />;
  }

  // If we require a profile but it's not complete, go to setup
  if (requireProfile && !profileComplete && location.pathname !== '/profile-setup') {
    return <Navigate to="/profile-setup" replace />;
  }

  return <>{children}</>;
};
