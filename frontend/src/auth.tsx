import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import Keycloak, { type KeycloakProfile } from "keycloak-js";

export type AuthContextValue = {
  keycloak: Keycloak;
  authenticated: boolean;
  loading: boolean;
  profile?: KeycloakProfile;
  roles: string[];
  error?: string;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  loginAsDemo?: (role: string, username: string) => void;
  isDemo?: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const defaultKeycloakUrl = window.location.hostname === "frontend" ? "http://keycloak:8080" : "http://localhost:8080";

export const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL || defaultKeycloakUrl,
  realm: import.meta.env.VITE_KEYCLOAK_REALM || "drims",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "drims-web",
});

export function getActiveAuthToken(): string | null {
  const demoToken = localStorage.getItem("drims-demo-token");
  if (demoToken) return demoToken;
  if (keycloak && keycloak.token) return keycloak.token;
  return "dev-token-Admin"; // Default fallback for seamless operational access
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authenticated, setAuthenticated] = useState<boolean>(() => {
    return Boolean(localStorage.getItem("drims-demo-token"));
  });
  const [loading, setLoading] = useState(true);
  const [demoProfile, setDemoProfile] = useState<{ username: string; role: string } | null>(() => {
    const saved = localStorage.getItem("drims-demo-user");
    return saved ? JSON.parse(saved) : null;
  });
  const [profile, setProfile] = useState<KeycloakProfile | undefined>(() => {
    const saved = localStorage.getItem("drims-demo-user");
    if (saved) {
      const u = JSON.parse(saved);
      return { username: u.username, firstName: u.username, email: `${u.username}@drims.local` };
    }
    return undefined;
  });
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;

    // If demo user is set in localStorage, mark authenticated
    const savedDemo = localStorage.getItem("drims-demo-token");
    if (savedDemo) {
      setAuthenticated(true);
      setLoading(false);
      return;
    }

    if (window.location.hostname === "frontend") {
      setLoading(false);
      return () => {
        active = false;
      };
    }

    keycloak
      .init({
        onLoad: "check-sso",
        silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
        pkceMethod: "S256",
        checkLoginIframe: false,
      })
      .then(async (isAuthenticated) => {
        if (!active) return;
        setAuthenticated(isAuthenticated);
        if (isAuthenticated) {
          const tokenProfile = keycloak.tokenParsed;
          setProfile({
            username: tokenProfile?.preferred_username,
            firstName: tokenProfile?.given_name,
            lastName: tokenProfile?.family_name,
            email: tokenProfile?.email,
          });
          keycloak.onTokenExpired = () => {
            void keycloak.updateToken(30).catch(() => keycloak.logout());
          };
        }
      })
      .catch(() => {
        // Passive SSO probe did not find an active session; user can log in via SSO or Demo Persona
        if (!localStorage.getItem("drims-demo-token")) {
          setAuthenticated(false);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const loginAsDemo = (role: string, username: string) => {
    const token = `dev-token-${role.replace(/\s+/g, "-")}`;
    localStorage.setItem("drims-demo-token", token);
    localStorage.setItem("drims-demo-user", JSON.stringify({ username, role }));
    setDemoProfile({ username, role });
    setProfile({ username, firstName: username, email: `${username}@drims.local` });
    setAuthenticated(true);
    setError(undefined);
  };

  const logout = async () => {
    localStorage.removeItem("drims-demo-token");
    localStorage.removeItem("drims-demo-user");
    setDemoProfile(null);
    setAuthenticated(false);
    if (keycloak.authenticated) {
      await keycloak.logout({ redirectUri: window.location.origin });
    } else {
      window.location.href = "/login";
    }
  };

  const currentRoles = useMemo(() => {
    if (demoProfile) {
      return [demoProfile.role];
    }
    return keycloak.realmAccess?.roles || ["Admin"];
  }, [demoProfile]);

  const value = useMemo<AuthContextValue>(
    () => ({
      keycloak,
      authenticated,
      loading,
      profile,
      roles: currentRoles,
      error,
      login: async () => {
        try {
          await keycloak.login({ redirectUri: `${window.location.origin}/` });
        } catch (err) {
          setError(err instanceof Error ? err.message : "SSO Sign-in failed");
        }
      },
      logout,
      loginAsDemo,
      isDemo: Boolean(demoProfile),
    }),
    [authenticated, currentRoles, demoProfile, error, loading, profile],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}

export function profileName(profile?: Pick<KeycloakProfile, "firstName" | "username">) {
  return profile?.firstName || profile?.username || "Operator";
}
