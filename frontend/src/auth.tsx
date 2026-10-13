import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import Keycloak, { KeycloakInstance, KeycloakProfile } from "keycloak-js";

type AuthContextValue = {
  keycloak: KeycloakInstance;
  authenticated: boolean;
  loading: boolean;
  profile?: KeycloakProfile;
  roles: string[];
  error?: string;
  login: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const defaultKeycloakUrl = window.location.hostname === "frontend" ? "http://keycloak:8080" : "http://localhost:8080";
const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL || defaultKeycloakUrl,
  realm: import.meta.env.VITE_KEYCLOAK_REALM || "drims",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "drims-web",
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<KeycloakProfile>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;
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
      .catch((reason: unknown) => {
        setAuthenticated(false);
        setError(reason instanceof Error ? reason.message : "Authentication could not be initialized");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      keycloak,
      authenticated,
      loading,
      profile,
      roles: keycloak.realmAccess?.roles || [],
      error,
      login: () => keycloak.login({ redirectUri: `${window.location.origin}/` }),
      logout: () => keycloak.logout({ redirectUri: window.location.origin }),
    }),
    [authenticated, error, loading, profile],
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
