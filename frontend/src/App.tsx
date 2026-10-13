import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Navigate, Outlet, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Breadcrumb,
  Button,
  Dropdown,
  Layout,
  Menu,
  Select,
  Space,
  Spin,
  Switch,
  Tag,
  Typography,
} from "antd";
import {
  AuditOutlined,
  BellOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  HeatMapOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { getHealth } from "./api";
import { useAuth } from "./auth";
import { canAccess } from "./permissions";
const Dashboard = lazy(() => import("./pages").then((module) => ({ default: module.Dashboard })));
const Missions = lazy(() => import("./pages").then((module) => ({ default: module.Missions })));
const Discrepancies = lazy(() => import("./pages").then((module) => ({ default: module.Discrepancies })));
const WarehouseMap = lazy(() => import("./pages").then((module) => ({ default: module.WarehouseMap })));
const Reports = lazy(() => import("./pages").then((module) => ({ default: module.Reports })));
const MasterData = lazy(() => import("./pages").then((module) => ({ default: module.MasterData })));
const Administration = lazy(() => import("./pages").then((module) => ({ default: module.Administration })));
const AuditLog = lazy(() => import("./pages").then((module) => ({ default: module.AuditLog })));
const Notifications = lazy(() => import("./pages").then((module) => ({ default: module.Notifications })));
const Help = lazy(() => import("./pages").then((module) => ({ default: module.Help })));
const ErrorPage = lazy(() => import("./pages").then((module) => ({ default: module.ErrorPage })));

const { Header, Sider, Content } = Layout;
const roleNames = ["Admin", "Inventory Controller", "Warehouse Supervisor", "Viewer"];

function LoginPage() {
  const { login, loginAsDemo, loading, error } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleDemoLogin = (role: string, username: string) => {
    if (loginAsDemo) {
      loginAsDemo(role, username);
      navigate("/");
    }
  };

  return (
    <main className="auth-page">
      <section className="login-card" style={{ maxWidth: 460 }}>
        <div className="brand-mark large">D</div>
        <Typography.Title level={2} style={{ marginBottom: 4 }}>DRIMS</Typography.Title>
        <Typography.Text type="secondary" style={{ fontSize: 15 }}>
          Drone-based Inventory Management System
        </Typography.Text>
        <Typography.Paragraph className="login-copy" style={{ marginTop: 12 }}>
          Autonomous drone cycle counting, barcode scanning, computer vision bounding, and automated ERP reconciliation.
        </Typography.Paragraph>

        <Space direction="vertical" style={{ width: "100%", gap: 12 }}>
          <Button type="primary" size="large" block onClick={() => void login()} loading={loading}>
            {t("signIn")} (Keycloak SSO)
          </Button>

          <div style={{ textAlign: "center", margin: "8px 0", color: "#64748b" }}>
            <span style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>— Or Instant Demo Persona —</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <Button
              onClick={() => handleDemoLogin("Admin", "admin_ops")}
              style={{ background: "rgba(14, 165, 233, 0.12)", borderColor: "#0ea5e9", color: "#38bdf8" }}
            >
              👑 Admin
            </Button>
            <Button
              onClick={() => handleDemoLogin("Inventory Controller", "controller_jane")}
              style={{ background: "rgba(16, 185, 129, 0.12)", borderColor: "#10b981", color: "#34d399" }}
            >
              📦 Controller
            </Button>
            <Button
              onClick={() => handleDemoLogin("Warehouse Supervisor", "sup_marcus")}
              style={{ background: "rgba(245, 158, 11, 0.12)", borderColor: "#f59e0b", color: "#fbbf24" }}
            >
              🏭 Supervisor
            </Button>
            <Button
              onClick={() => handleDemoLogin("Viewer", "auditor_claire")}
              style={{ background: "rgba(148, 163, 184, 0.12)", borderColor: "#64748b", color: "#cbd5e1" }}
            >
              👁️ Viewer / Audit
            </Button>
          </div>
        </Space>

        {error && <Typography.Text type="danger" style={{ display: "block", marginTop: 12 }}>{error}</Typography.Text>}
        <Typography.Text className="login-footnote" style={{ display: "block", marginTop: 16 }}>
          Site WH01 · Autonomous Cycle Count Flight Control
        </Typography.Text>
      </section>
    </main>
  );
}

function ProtectedRoute() {
  const { authenticated, loading } = useAuth();
  if (loading) return <div className="centered"><Spin size="large" /></div>;
  return authenticated ? <Outlet /> : <Navigate to="/login" replace />;
}

function RoleRoute({ allowed }: { allowed: string[] }) {
  const { roles } = useAuth();
  return canAccess(roles, allowed) ? <Outlet /> : <Navigate to="/403" replace />;
}

function Shell() {
  const { t } = useTranslation();
  const { profile, roles, logout, loginAsDemo } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [dark, setDark] = useState(() => localStorage.getItem("drims-theme") !== "light");
  const [site, setSite] = useState("WH01");
  const health = useQuery({ queryKey: ["health"], queryFn: getHealth, refetchInterval: 30_000 });

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("drims-theme", dark ? "dark" : "light");
  }, [dark]);

  const menuItems = useMemo(
    () => [
      { key: "/", icon: <DashboardOutlined />, label: t("dashboard") },
      { key: "/missions", icon: <ThunderboltOutlined />, label: t("missions") },
      { key: "/discrepancies", icon: <FileTextOutlined />, label: t("discrepancies") },
      { key: "/warehouse-map", icon: <HeatMapOutlined />, label: t("warehouseMap") },
      { type: "divider" as const },
      { key: "/reports", icon: <FileTextOutlined />, label: t("reports") },
      { key: "/master-data", icon: <DatabaseOutlined />, label: t("masterData") },
      { key: "/administration", icon: <SettingOutlined />, label: t("administration") },
      { key: "/audit-log", icon: <AuditOutlined />, label: t("auditLog") },
    ],
    [t],
  );
  const selectedKey = menuItems.find((item) => "key" in item && typeof item.key === "string" && item.key !== "/" && location.pathname.startsWith(item.key))?.key
    || (location.pathname === "/" ? "/" : undefined);
  const displayName = profile?.firstName || profile?.username || "Operator";
  const currentRole = roles[0] || "Admin";
  const systemOk = health.data?.status === "ready";

  const userMenuItems = [
    { key: "profile", icon: <UserOutlined />, label: `${displayName} (${currentRole})` },
    { type: "divider" as const },
    {
      key: "personas",
      label: "Switch Operational Role",
      children: [
        { key: "p-admin", label: "👑 Admin", onClick: () => loginAsDemo?.("Admin", "admin_ops") },
        { key: "p-ic", label: "📦 Inventory Controller", onClick: () => loginAsDemo?.("Inventory Controller", "controller_jane") },
        { key: "p-ws", label: "🏭 Warehouse Supervisor", onClick: () => loginAsDemo?.("Warehouse Supervisor", "sup_marcus") },
        { key: "p-vw", label: "👁️ Viewer / Auditor", onClick: () => loginAsDemo?.("Viewer", "auditor_claire") },
      ],
    },
    { type: "divider" as const },
    { key: "logout", icon: <LogoutOutlined />, label: t("signOut"), onClick: () => void logout() },
  ];

  return (
    <Layout className="app-layout">
      <Sider collapsible collapsed={collapsed} trigger={null} breakpoint="lg" className="app-sider">
        <div className="sider-brand" onClick={() => navigate("/")}>
          <div className="brand-mark">D</div>
          {!collapsed && <div><strong>DRIMS</strong><small>Operations</small></div>}
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={selectedKey ? [selectedKey] : []} items={menuItems} onClick={({ key }) => navigate(key)} />
        {!collapsed && <div className="sider-footer"><Badge status="success" text="Environment: local" /></div>}
      </Sider>
      <Layout>
        <Header className="app-header">
          <Space size="middle">
            <Button type="text" aria-label={collapsed ? "Expand navigation" : "Collapse navigation"} icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed(!collapsed)} />
            <Breadcrumb items={[{ title: "DRIMS" }, { title: menuItems.find((item) => "key" in item && item.key === selectedKey)?.label || "Workspace" }]} />
          </Space>
          <Space size="middle">
            <Select aria-label={t("selectSite")} value={site} onChange={setSite} options={[{ value: "WH01", label: "WH01 · Main warehouse" }]} />
            <Tag color={currentRole === "Admin" ? "purple" : currentRole === "Inventory Controller" ? "cyan" : "orange"} style={{ marginRight: 0 }}>
              {currentRole}
            </Tag>
            <Badge dot={!systemOk} status={systemOk ? "success" : "error"}><Button type="text" aria-label={t("notifications")} icon={<BellOutlined />} onClick={() => navigate("/notifications")} /></Badge>
            <Switch checked={dark} onChange={setDark} checkedChildren="Dark" unCheckedChildren="Light" aria-label={dark ? t("lightTheme") : t("darkTheme")} />
            <Dropdown menu={{ items: userMenuItems }}>
              <Button type="text"><Avatar size="small" icon={<UserOutlined />} /> <span className="profile-name">{displayName}</span></Button>
            </Dropdown>
          </Space>
        </Header>
        {!systemOk && <div className="status-banner"><Badge status="error" /> {t("systemDegraded")}. {health.error instanceof Error ? health.error.message : "Dependency checks are failing."}<Button type="link" onClick={() => void health.refetch()}>{t("retry")}</Button></div>}
        <Content className="app-content"><Outlet /></Content>
        <footer className="app-footer">DRIMS · {roles.length ? roles.join(" · ") : roleNames[3]} · Site {site}</footer>
      </Layout>
    </Layout>
  );
}

export default function App() {
  const { t } = useTranslation();
  return (
    <Suspense fallback={<div className="centered"><Spin size="large" /></div>}><Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Shell />}>
          <Route index element={<Dashboard />} />
          <Route path="/missions" element={<Missions />} />
          <Route path="/discrepancies" element={<Discrepancies />} />
          <Route path="/warehouse-map" element={<WarehouseMap />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/master-data" element={<RoleRoute allowed={["Admin"]} />}><Route index element={<MasterData />} /></Route>
          <Route path="/administration" element={<RoleRoute allowed={["Admin"]} />}><Route index element={<Administration />} /></Route>
          <Route path="/audit-log" element={<RoleRoute allowed={["Admin", "Viewer"]} />}><Route index element={<AuditLog />} /></Route>
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/help" element={<Help />} />
          <Route path="/403" element={<ErrorPage code="403" title="Return to dashboard" subTitle={t("accessDenied")} />} />
          <Route path="*" element={<ErrorPage code="404" title="Return to dashboard" subTitle={t("pageNotFound")} />} />
        </Route>
      </Route>
    </Routes></Suspense>
  );
}
