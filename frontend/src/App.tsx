import React, { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Navigate, Outlet, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Breadcrumb,
  Button,
  Card,
  Dropdown,
  Layout,
  Menu,
  Result,
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
  const { login, loading, error } = useAuth();
  const { t } = useTranslation();
  return (
    <main className="auth-page">
      <section className="login-card">
        <div className="brand-mark large">D</div>
        <Typography.Title>DRIMS</Typography.Title>
        <Typography.Text type="secondary">{t("appSubtitle")}</Typography.Text>
        <Typography.Paragraph className="login-copy">
          Verified inventory counts, reconciliation, and discrepancy review in one operations workspace.
        </Typography.Paragraph>
        <Button type="primary" size="large" block onClick={() => void login()} loading={loading}>
          {t("signIn")}
        </Button>
        {error && <Typography.Text type="danger">{error}</Typography.Text>}
        <Typography.Text className="login-footnote">Secure sign-in provided by your organization</Typography.Text>
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
  const { profile, roles, logout } = useAuth();
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
  const systemOk = health.data?.status === "ready";

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
            <Badge dot={!systemOk} status={systemOk ? "success" : "error"}><Button type="text" aria-label={t("notifications")} icon={<BellOutlined />} onClick={() => navigate("/notifications")} /></Badge>
            <Switch checked={dark} onChange={setDark} checkedChildren="Dark" unCheckedChildren="Light" aria-label={dark ? t("lightTheme") : t("darkTheme")} />
            <Dropdown menu={{ items: [{ key: "profile", icon: <UserOutlined />, label: displayName }, { type: "divider" }, { key: "logout", icon: <LogoutOutlined />, label: t("signOut"), onClick: () => void logout() }] }}>
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
