import React from "react";
import { AppstoreOutlined, AuditOutlined, BellOutlined, DashboardOutlined, DatabaseOutlined, FileTextOutlined, HeatMapOutlined, SettingOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { Button, Card, Result, Tag, Typography } from "antd";

export type PageProps = { title: string; description: string; icon: React.ReactNode };

export function PagePlaceholder({ title, description, icon }: PageProps) {
  return <Card className="page-card"><div className="page-placeholder"><div className="placeholder-icon">{icon}</div><Typography.Title level={2}>{title}</Typography.Title><Typography.Paragraph type="secondary">{description}</Typography.Paragraph><Tag color="cyan">Gate 2 feature surface</Tag></div></Card>;
}

export function Dashboard() {
  return <PagePlaceholder title="Operations dashboard" description="Inventory accuracy, coverage, open cases, and mission activity will appear here." icon={<DashboardOutlined />} />;
}

export function Missions() {
  return <PagePlaceholder title="Missions" description="Review mission status and processing progress." icon={<ThunderboltOutlined />} />;
}

export function Discrepancies() {
  return <PagePlaceholder title="Discrepancies" description="Review and resolve inventory discrepancies." icon={<FileTextOutlined />} />;
}

export function WarehouseMap() {
  return <PagePlaceholder title="Warehouse map" description="Explore bin-level inventory by aisle and rack." icon={<HeatMapOutlined />} />;
}

export function Reports() {
  return <PagePlaceholder title="Reports" description="Generate and download operational reports." icon={<FileTextOutlined />} />;
}

export function MasterData() {
  return <PagePlaceholder title="Master data" description="Manage warehouse layout and SKU master data." icon={<DatabaseOutlined />} />;
}

export function Administration() {
  return <PagePlaceholder title="Administration" description="Manage users, settings, integrations, and ingestion." icon={<SettingOutlined />} />;
}

export function AuditLog() {
  return <PagePlaceholder title="Audit log" description="Search immutable changes and export audit records." icon={<AuditOutlined />} />;
}

export function Notifications() {
  return <PagePlaceholder title="Notifications" description="Review system and inventory notifications." icon={<BellOutlined />} />;
}

export function Help() {
  return <PagePlaceholder title="Help & About" description="DRIMS version, API information, and support." icon={<AppstoreOutlined />} />;
}

export function ErrorPage({ code, title, subTitle }: { code: "403" | "404"; title: string; subTitle: string }) {
  return <Result status={code} title={code} subTitle={subTitle} extra={<Button type="primary" href="/">{title}</Button>} />;
}
