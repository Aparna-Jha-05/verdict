"use client";

import { useAuth } from "../../context/AuthContext";
import AuthLanding from "../auth/AuthLanding";
import AppShell from "./AppShell";

export default function AppFrame({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center">
        <span className="h-6 w-6 animate-spin rounded-full border-2 border-violet/30 border-t-gold" />
      </div>
    );
  }
  if (!user) return <AuthLanding />;
  return <AppShell>{children}</AppShell>;
}
