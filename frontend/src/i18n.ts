import i18n from "i18next";
import { initReactI18next } from "react-i18next";

void i18n.use(initReactI18next).init({
  lng: "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
  resources: {
    en: {
      translation: {
        appName: "DRIMS",
        appSubtitle: "Drone inventory operations",
        dashboard: "Dashboard",
        missions: "Missions",
        discrepancies: "Discrepancies",
        warehouseMap: "Warehouse map",
        reports: "Reports",
        masterData: "Master data",
        administration: "Administration",
        auditLog: "Audit log",
        notifications: "Notifications",
        help: "Help & About",
        signIn: "Sign in",
        signOut: "Sign out",
        accessDenied: "Access denied",
        pageNotFound: "Page not found",
        retry: "Retry",
        systemOperational: "All systems operational",
        systemDegraded: "System status requires attention",
        selectSite: "Select site",
        lightTheme: "Light theme",
        darkTheme: "Dark theme",
      },
    },
  },
});

export default i18n;
