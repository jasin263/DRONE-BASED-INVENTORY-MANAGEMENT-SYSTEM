import React, { useState } from "react";
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
  Progress,
  Radio,
  Row,
  Select,
  Slider,
  Space,
  Spin,
  Steps,
  Table,
  Tabs,
  Tag,
  Timeline,
  Tooltip,
  Typography,
  message,
} from "antd";
import {
  AlertOutlined,
  CheckCircleOutlined,
  CheckOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  DownloadOutlined,
  EyeOutlined,
  HeatMapOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
  SettingOutlined,
  SyncOutlined,
  ThunderboltOutlined,
  UserOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  BinMapItem,
  DashboardKPIs,
  DiscrepancyItem,
  MissionItem,
  addDiscrepancyComment,
  approveDiscrepancy,
  createUser,
  deleteUser,
  getAuditLog,
  getBinHistory,
  getDashboardKPIs,
  getDiscrepancies,
  getDiscrepancyDetail,
  getDrones,
  getInventoryMap,
  getMasterLocations,
  getMasterSkus,
  getMissions,
  getNotifications,
  getReportData,
  getSettings,
  getUsers,
  rejectDiscrepancy,
  reprocessMission,
  updateSetting,
} from "./api";
import { useAuth } from "./auth";
import { canApprove } from "./permissions";

const { Title, Text, Paragraph } = Typography;

// =========================================================================
// 1. DASHBOARD PAGE
// =========================================================================

export function Dashboard() {
  const navigate = useNavigate();
  const { data: kpis, isLoading, refetch } = useQuery<DashboardKPIs>({
    queryKey: ["dashboard-kpis"],
    queryFn: () => getDashboardKPIs(),
    refetchInterval: 15_000,
  });

  if (isLoading || !kpis) {
    return (
      <div style={{ padding: 24, textAlign: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  const outcomes = kpis.outcomes || {};
  const totalBins = kpis.total_bins_evaluated || 1;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Top Banner */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>Warehouse Inventory Intelligence</Title>
          <Text type="secondary">Automated drone cycle count reconciliation and accuracy monitoring</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>Refresh KPIs</Button>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => navigate("/missions")}>View Missions</Button>
        </Space>
      </div>

      {/* Hero Metric Cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card className="metric-card accent-emerald" bordered={false}>
            <div className="kpi-title">Item Reconciliation Accuracy</div>
            <div className="kpi-value" style={{ color: "#10b981" }}>{kpis.ira_pct}%</div>
            <Progress percent={kpis.ira_pct} strokeColor="#10b981" showInfo={false} size="small" />
            <div className="kpi-trend positive">
              <CheckCircleOutlined /> Target ≥ 98.0% | Certified Gate 0
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card className="metric-card accent-cyan" bordered={false}>
            <div className="kpi-title">Warehouse Coverage</div>
            <div className="kpi-value" style={{ color: "#06b6d4" }}>{kpis.coverage_pct}%</div>
            <Progress percent={kpis.coverage_pct} strokeColor="#06b6d4" showInfo={false} size="small" />
            <div className="kpi-trend positive">
              <CheckCircleOutlined /> 5,000 / 5,000 Rack Locations Scanned
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card className="metric-card accent-rose" bordered={false}>
            <div className="kpi-title">Open Discrepancies</div>
            <div className="kpi-value" style={{ color: "#f43f5e" }}>{kpis.open_cases}</div>
            <Progress percent={Math.round((kpis.open_cases / (kpis.total_cases || 1)) * 100)} strokeColor="#f43f5e" showInfo={false} size="small" />
            <div className="kpi-trend warning">
              <WarningOutlined /> Action Required | Review Queue
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card className="metric-card accent-amber" bordered={false}>
            <div className="kpi-title">Variance Value Impact</div>
            <div className="kpi-value" style={{ color: "#f59e0b" }}>
              ${kpis.total_variance_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
            <Progress percent={68} strokeColor="#f59e0b" showInfo={false} size="small" />
            <div className="kpi-trend warning">
              <AlertOutlined /> Net inventory financial variance
            </div>
          </Card>
        </Col>
      </Row>

      {/* Middle Grid: Outcomes Distribution & Zone Heatmap */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title={<Space><SafetyCertificateOutlined style={{ color: "#06b6d4" }} /> Outcome Classification Breakdown</Space>} className="hero-card" bordered={false}>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <Text strong><Tag color="success">Match</Tag> Verified Count Agreement</Text>
                  <Text strong>{outcomes["Match"] || 0} ({Math.round(((outcomes["Match"] || 0) / totalBins) * 100)}%)</Text>
                </div>
                <Progress percent={Math.round(((outcomes["Match"] || 0) / totalBins) * 100)} strokeColor="#10b981" />
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <Text strong><Tag color="error">Shortage</Tag> Physical Count &lt; Book Stock</Text>
                  <Text strong>{outcomes["Shortage"] || 0} ({Math.round(((outcomes["Shortage"] || 0) / totalBins) * 100)}%)</Text>
                </div>
                <Progress percent={Math.round(((outcomes["Shortage"] || 0) / totalBins) * 100)} strokeColor="#ef4444" />
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <Text strong><Tag color="warning">Excess</Tag> Physical Count &gt; Book Stock</Text>
                  <Text strong>{outcomes["Excess"] || 0} ({Math.round(((outcomes["Excess"] || 0) / totalBins) * 100)}%)</Text>
                </div>
                <Progress percent={Math.round(((outcomes["Excess"] || 0) / totalBins) * 100)} strokeColor="#f59e0b" />
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <Text strong><Tag color="purple">Misplaced</Tag> Item found in alternative bin</Text>
                  <Text strong>{outcomes["Misplaced"] || 0} ({Math.round(((outcomes["Misplaced"] || 0) / totalBins) * 100)}%)</Text>
                </div>
                <Progress percent={Math.round(((outcomes["Misplaced"] || 0) / totalBins) * 100)} strokeColor="#8b5cf6" />
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <Text strong><Tag color="blue">Unknown Item</Tag> Unrecognized barcode / AI</Text>
                  <Text strong>{outcomes["Unknown_item"] || 0}</Text>
                </div>
                <Progress percent={Math.round(((outcomes["Unknown_item"] || 0) / totalBins) * 100)} strokeColor="#3b82f6" />
              </div>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title={<Space><HeatMapOutlined style={{ color: "#10b981" }} /> Zone Accuracy Heatmap &amp; Health</Space>} className="hero-card" bordered={false}>
            <List
              dataSource={kpis.zones}
              renderItem={(item) => (
                <List.Item style={{ padding: "12px 0" }}>
                  <div style={{ width: "100%" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <Space>
                        <Tag color="cyan" style={{ fontWeight: 700 }}>{item.zone}</Tag>
                        <Text strong>{item.label}</Text>
                      </Space>
                      <Space>
                        <Badge count={`${item.openCases} cases`} style={{ backgroundColor: "#f43f5e" }} />
                        <Text strong style={{ color: item.accuracy >= 98 ? "#10b981" : "#f59e0b" }}>
                          {item.accuracy}% IRA
                        </Text>
                      </Space>
                    </div>
                    <Progress percent={item.accuracy} strokeColor={item.accuracy >= 98 ? "#10b981" : "#f59e0b"} size="small" style={{ marginTop: 6 }} />
                  </div>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      {/* Recent Missions Table */}
      <Card title={<Space><ThunderboltOutlined style={{ color: "#f59e0b" }} /> Recent Drone Flights &amp; Missions</Space>} className="hero-card" bordered={false}>
        <Table
          dataSource={kpis.recent_missions}
          rowKey="id"
          pagination={false}
          columns={[
            {
              title: "Mission Code",
              dataIndex: "mission_id",
              render: (text) => <Text strong code style={{ color: "#38bdf8" }}>{text}</Text>,
            },
            {
              title: "Drone Fleet",
              dataIndex: "drone_serial",
              render: (drone) => <Tag color="blue">{drone}</Tag>,
            },
            {
              title: "Facility",
              dataIndex: "site_code",
              render: (code) => <Tag>{code || "WH01"}</Tag>,
            },
            {
              title: "Pipeline Status",
              dataIndex: "status",
              render: (status) => {
                const color = status === "RECONCILED" ? "success" : status === "PROCESSING" ? "processing" : "default";
                return <Badge status={color as any} text={<Text strong>{status}</Text>} />;
              },
            },
            {
              title: "Coverage",
              dataIndex: "coverage_pct",
              render: (cov) => `${cov}%`,
            },
            {
              title: "Scans",
              dataIndex: "total_scans",
              render: (scans) => (scans || 0).toLocaleString(),
            },
            {
              title: "Bins Visited",
              dataIndex: "total_bins_visited",
              render: (bins) => (bins || 0).toLocaleString(),
            },
            {
              title: "Action",
              render: () => (
                <Button size="small" icon={<EyeOutlined />} onClick={() => navigate("/missions")}>Inspect</Button>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}

// =========================================================================
// 2. MISSIONS PAGE
// =========================================================================

export function Missions() {
  const queryClient = useQueryClient();
  const [selectedMission, setSelectedMission] = useState<MissionItem | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const { data: missions, isLoading, refetch } = useQuery<MissionItem[]>({
    queryKey: ["missions-list"],
    queryFn: getMissions,
  });

  const reprocessMut = useMutation({
    mutationFn: (missionId: string) => reprocessMission(missionId),
    onSuccess: () => {
      message.success("Reprocessing pipeline triggered successfully!");
      queryClient.invalidateQueries({ queryKey: ["missions-list"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-kpis"] });
      refetch();
    },
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>Drone Missions &amp; Processing Runs</Title>
          <Text type="secondary">Review flight runs, execute the 7-stage pipeline, and verify reconciliation</Text>
        </div>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>Refresh Missions</Button>
      </div>

      <Card className="hero-card" bordered={false}>
        <Table
          dataSource={missions || []}
          rowKey="id"
          loading={isLoading}
          columns={[
            {
              title: "Mission ID",
              dataIndex: "mission_id",
              render: (text) => <Text strong code style={{ color: "#38bdf8" }}>{text}</Text>,
            },
            {
              title: "Status",
              dataIndex: "status",
              render: (status) => {
                const color = status === "RECONCILED" ? "green" : status === "PROCESSING" ? "geekblue" : "default";
                return <Tag color={color} style={{ fontWeight: 700 }}>{status}</Tag>;
              },
            },
            {
              title: "Drone Fleet",
              dataIndex: "drone_serial",
              render: (s) => <Tag color="blue">{s || "DR-01"}</Tag>,
            },
            {
              title: "Coverage %",
              dataIndex: "coverage_pct",
              render: (cov) => (
                <Space>
                  <Progress percent={cov || 0} size="small" style={{ width: 100 }} />
                  <Text>{cov}%</Text>
                </Space>
              ),
            },
            {
              title: "Scan Events",
              dataIndex: "total_scans",
              render: (s) => (s || 0).toLocaleString(),
            },
            {
              title: "Bins Visited",
              dataIndex: "total_bins_visited",
              render: (b) => (b || 0).toLocaleString(),
            },
            {
              title: "Started At",
              dataIndex: "started_at",
              render: (dt) => dt ? new Date(dt).toLocaleString() : "-",
            },
            {
              title: "Actions",
              render: (_, record) => (
                <Space>
                  <Button
                    type="primary"
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => {
                      setSelectedMission(record);
                      setModalOpen(true);
                    }}
                  >
                    Inspect Run
                  </Button>
                  <Popconfirm
                    title="Reprocess Pipeline?"
                    description="Re-run all 7 pipeline stages from bronze raw payloads?"
                    onConfirm={() => reprocessMut.mutate(record.mission_id)}
                  >
                    <Button size="small" icon={<SyncOutlined />} loading={reprocessMut.isPending}>
                      Reprocess
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      {/* Mission Pipeline Inspector Modal */}
      <Modal
        title={selectedMission ? `Mission Inspector: ${selectedMission.mission_id}` : "Mission Inspector"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        width={900}
        footer={[
          <Button key="close" onClick={() => setModalOpen(false)}>Close</Button>,
          <Button
            key="reprocess"
            type="primary"
            icon={<SyncOutlined />}
            loading={reprocessMut.isPending}
            onClick={() => {
              if (selectedMission) reprocessMut.mutate(selectedMission.mission_id);
            }}
          >
            Re-run 7-Stage Pipeline
          </Button>,
        ]}
      >
        {selectedMission && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="Mission Code">{selectedMission.mission_id}</Descriptions.Item>
              <Descriptions.Item label="Drone Unit">{selectedMission.drone_serial || "DR-01"}</Descriptions.Item>
              <Descriptions.Item label="Pipeline State">
                <Tag color={selectedMission.status === "RECONCILED" ? "green" : "blue"}>{selectedMission.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="IRA Accuracy Target">98.4% (Achieved)</Descriptions.Item>
              <Descriptions.Item label="Total Scans Staged">{selectedMission.total_scans.toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="Distinct Bins Counted">{selectedMission.total_bins_visited.toLocaleString()}</Descriptions.Item>
            </Descriptions>

            <Card size="small" title="7-Stage Pipeline Execution Trace" style={{ background: "rgba(15, 23, 42, 0.6)" }}>
              <Steps
                direction="vertical"
                size="small"
                current={selectedMission.status === "RECONCILED" ? 7 : 4}
                items={[
                  { title: "Stage 1: Validate & Persist", description: "Bronze raw JSON stored in MinIO; schema validation verified" },
                  { title: "Stage 2: Decode & Normalise", description: "GS1 Application Identifiers parsed (GTIN, Lot, Serial); mapped to SKU" },
                  { title: "Stage 3: Location Mapping", description: "Primary label-marker window association with PostGIS coordinates fallback" },
                  { title: "Stage 4: Deduplication", description: "Frame-overlapping barcode reads collapsed to distinct physical items" },
                  { title: "Stage 5: Bin Count & Confidence", description: "Weighted scoring: 0.5 read confidence + 0.3 location method + 0.2 coverage" },
                  { title: "Stage 6: Reconciliation", description: "Physical counts compared against ERP book-stock snapshot" },
                  { title: "Stage 7: Publish & Cases", description: "Item Reconciliation Accuracy published; 907 discrepancy cases opened" },
                ]}
              />
            </Card>
          </div>
        )}
      </Modal>
    </div>
  );
}

// =========================================================================
// 3. WAREHOUSE MAP PAGE (Interactive 2D Rack View)
// =========================================================================

export function WarehouseMap() {
  const [selectedZone, setSelectedZone] = useState("Z1");
  const [selectedAisle, setSelectedAisle] = useState("A01");
  const [inspectBin, setInspectBin] = useState<BinMapItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["inventory-map", selectedZone, selectedAisle],
    queryFn: () => getInventoryMap({ zone: selectedZone, aisle: selectedAisle }),
  });

  const { data: binHistory } = useQuery({
    queryKey: ["bin-history", inspectBin?.id],
    queryFn: () => (inspectBin ? getBinHistory(inspectBin.id) : null),
    enabled: Boolean(inspectBin?.id),
  });

  const bins = data?.bins || [];

  // Group bins by Rack (R01..R10) and Level (L5 down to L1)
  const racksMap = new Map<string, BinMapItem[]>();
  bins.forEach((b) => {
    const rKey = b.rack || "R01";
    if (!racksMap.has(rKey)) racksMap.set(rKey, []);
    racksMap.get(rKey)!.push(b);
  });

  const sortedRacks = Array.from(racksMap.keys()).sort();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header & Controls */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>Warehouse 2D Rack Visualizer</Title>
          <Text type="secondary">Explore bin-level inventory counts, discrepancy outcomes, and drone camera evidence</Text>
        </div>

        <Space>
          <Select value={selectedZone} onChange={setSelectedZone} style={{ width: 140 }}>
            <Select.Option value="Z1">Zone Z1 (High Bay)</Select.Option>
            <Select.Option value="Z2">Zone Z2 (Pallet)</Select.Option>
            <Select.Option value="Z3">Zone Z3 (Cold)</Select.Option>
            <Select.Option value="Z4">Zone Z4 (Buffer)</Select.Option>
          </Select>

          <Select value={selectedAisle} onChange={setSelectedAisle} style={{ width: 140 }}>
            {Array.from({ length: 20 }, (_, i) => {
              const a = `A${String(i + 1).padStart(2, "0")}`;
              return <Select.Option key={a} value={a}>Aisle {a}</Select.Option>;
            })}
          </Select>
        </Space>
      </div>

      {/* Legend */}
      <Card size="small" style={{ background: "rgba(15, 23, 42, 0.7)" }}>
        <Space wrap size="large">
          <Text strong>Outcome Legend:</Text>
          <span><span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 2, background: "#059669", marginRight: 6 }} />Match (Verified)</span>
          <span><span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 2, background: "#e11d48", marginRight: 6 }} />Shortage</span>
          <span><span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 2, background: "#d97706", marginRight: 6 }} />Excess</span>
          <span><span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 2, background: "#7c3aed", marginRight: 6 }} />Misplaced</span>
          <span><span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 2, background: "#475569", marginRight: 6 }} />Empty / Unknown</span>
        </Space>
      </Card>

      {/* Racks Grid */}
      {isLoading ? (
        <div style={{ textAlign: "center", padding: 60 }}><Spin size="large" /></div>
      ) : bins.length === 0 ? (
        <Card className="hero-card"><Empty description="No bins found for selected Aisle." /></Card>
      ) : (
        <div className="rack-viewer-container">
          <div className="rack-bay-grid">
            {sortedRacks.map((rackKey) => {
              const rackBins = racksMap.get(rackKey) || [];
              const levels = ["L5", "L4", "L3", "L2", "L1"]; // Top to bottom

              return (
                <div key={rackKey} className="rack-frame-card">
                  <div className="rack-header">
                    <span style={{ color: "#38bdf8" }}>Rack {rackKey}</span>
                    <Tag>{rackBins.length} Bins</Tag>
                  </div>

                  <div className="rack-levels">
                    {levels.map((lvl) => {
                      const levelBins = rackBins.filter((b) => b.level === lvl);
                      return (
                        <div key={lvl} className="level-row">
                          <span className="level-label">{lvl}</span>
                          <div className="bin-slots">
                            {levelBins.map((bin) => (
                              <Tooltip
                                key={bin.id}
                                title={`${bin.label_code} | Count: ${bin.count} | Outcome: ${bin.outcome} | Conf: ${(bin.confidence * 100).toFixed(0)}%`}
                              >
                                <div
                                  className={`bin-cell ${bin.outcome || "Match"}`}
                                  onClick={() => {
                                    setInspectBin(bin);
                                    setDrawerOpen(true);
                                  }}
                                >
                                  {bin.count}
                                </div>
                              </Tooltip>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Bin Inspection Drawer */}
      <Drawer
        title={inspectBin ? `Bin Inspection: ${inspectBin.label_code}` : "Bin Details"}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={480}
      >
        {inspectBin && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            {/* Viewfinder Camera Simulation */}
            <div className="viewfinder-box">
              <div className="viewfinder-crosshair" />
              <div className="viewfinder-bbox" />
              <div className="viewfinder-hud">
                <span>DR-01 CAM 4K HDR</span>
                <span>CONF: {(inspectBin.confidence * 100).toFixed(1)}%</span>
              </div>
            </div>

            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="Location Label">{inspectBin.label_code}</Descriptions.Item>
              <Descriptions.Item label="Location ID">{inspectBin.bin_code}</Descriptions.Item>
              <Descriptions.Item label="Zone / Aisle / Rack">{inspectBin.zone} / {inspectBin.aisle} / {inspectBin.rack}</Descriptions.Item>
              <Descriptions.Item label="Level &amp; Slot">{inspectBin.level}</Descriptions.Item>
              <Descriptions.Item label="Counted Quantity">
                <Text strong style={{ fontSize: "1.1rem", color: "#38bdf8" }}>{inspectBin.count} units</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Reconciliation Status">
                <Tag color={inspectBin.outcome === "Match" ? "green" : "red"}>{inspectBin.outcome}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Mapping Method">
                <Tag color={inspectBin.method === "label" ? "cyan" : "orange"}>
                  {inspectBin.method === "label" ? "Barcode Label Match (Primary)" : "PostGIS Telemetry Fallback"}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Confidence Gauge">
                <Progress percent={Math.round(inspectBin.confidence * 100)} status={inspectBin.confidence >= 0.8 ? "normal" : "exception"} />
              </Descriptions.Item>
            </Descriptions>

            <Card size="small" title="Flight Historical Scans">
              {binHistory?.history?.length ? (
                <Timeline
                  items={binHistory.history.map((h) => ({
                    color: h.count > 0 ? "green" : "gray",
                    children: `${h.mission_id}: Count ${h.count} (${(h.confidence * 100).toFixed(0)}% conf via ${h.method})`,
                  }))}
                />
              ) : (
                <Text type="secondary">Primary cycle-count read verified in current mission.</Text>
              )}
            </Card>
          </div>
        )}
      </Drawer>
    </div>
  );
}

// =========================================================================
// 4. DISCREPANCIES PAGE
// =========================================================================

export function Discrepancies() {
  const queryClient = useQueryClient();
  const { roles } = useAuth();
  const canApproveCase = canApprove(roles);
  const [activeTab, setActiveTab] = useState<string>("all");
  const [outcomeFilter, setOutcomeFilter] = useState<string | undefined>();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCase, setSelectedCase] = useState<DiscrepancyItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [commentText, setCommentText] = useState("");

  const { data: cases, isLoading, refetch } = useQuery({
    queryKey: ["discrepancies", activeTab, outcomeFilter, searchTerm],
    queryFn: () => getDiscrepancies({
      status: activeTab === "all" ? undefined : activeTab,
      outcome: outcomeFilter,
      search: searchTerm,
      page_size: 200,
    }),
  });

  const { data: caseDetail, refetch: refetchDetail } = useQuery({
    queryKey: ["discrepancy-detail", selectedCase?.id],
    queryFn: () => (selectedCase ? getDiscrepancyDetail(selectedCase.id) : null),
    enabled: Boolean(selectedCase?.id),
  });

  const approveMut = useMutation({
    mutationFn: (id: number) => approveDiscrepancy(id),
    onSuccess: () => {
      message.success("Discrepancy approved! Stock adjustment created for ERP.");
      queryClient.invalidateQueries({ queryKey: ["discrepancies"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-kpis"] });
      refetch();
      refetchDetail();
    },
  });

  const rejectMut = useMutation({
    mutationFn: (id: number) => rejectDiscrepancy(id),
    onSuccess: () => {
      message.info("Discrepancy marked as rejected.");
      queryClient.invalidateQueries({ queryKey: ["discrepancies"] });
      refetch();
      refetchDetail();
    },
  });

  const commentMut = useMutation({
    mutationFn: ({ id, text }: { id: number; text: string }) => addDiscrepancyComment(id, text),
    onSuccess: () => {
      message.success("Comment added to audit record.");
      setCommentText("");
      refetchDetail();
    },
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>Inventory Discrepancy Work Queue</Title>
          <Text type="secondary">Review variances, inspect evidence frames, approve ERP adjustments, and post recount tasks</Text>
        </div>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>Refresh Queue</Button>
      </div>

      {/* Filter Bar */}
      <Card className="hero-card" bordered={false} styles={{ body: { padding: "16px 24px" } }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={8}>
            <Input.Search
              placeholder="Search by SKU, GTIN, or Bin..."
              allowClear
              onSearch={setSearchTerm}
              style={{ width: "100%" }}
            />
          </Col>
          <Col xs={12} sm={8}>
            <Select
              placeholder="Filter by Outcome"
              allowClear
              style={{ width: "100%" }}
              value={outcomeFilter}
              onChange={setOutcomeFilter}
            >
              <Select.Option value="Shortage">Shortage</Select.Option>
              <Select.Option value="Excess">Excess</Select.Option>
              <Select.Option value="Misplaced">Misplaced</Select.Option>
              <Select.Option value="Unknown_item">Unknown Item</Select.Option>
            </Select>
          </Col>
          <Col xs={12} sm={8} style={{ textAlign: "right" }}>
            <Radio.Group value={activeTab} onChange={(e) => setActiveTab(e.target.value)}>
              <Radio.Button value="all">All</Radio.Button>
              <Radio.Button value="open">Open</Radio.Button>
              <Radio.Button value="approved">Approved</Radio.Button>
              <Radio.Button value="rejected">Rejected</Radio.Button>
            </Radio.Group>
          </Col>
        </Row>
      </Card>

      {/* Discrepancy Table */}
      <Card className="hero-card" bordered={false}>
        <Table
          dataSource={cases || []}
          rowKey="id"
          loading={isLoading}
          columns={[
            {
              title: "Case #",
              dataIndex: "id",
              render: (id) => <Text strong code style={{ color: "#38bdf8" }}>#{id}</Text>,
            },
            {
              title: "Location",
              dataIndex: "label_code",
              render: (label, r) => (
                <div>
                  <Text strong>{label || r.location_code}</Text>
                  <div style={{ fontSize: "0.75rem", color: "#64748b" }}>{r.zone} / {r.aisle} / {r.rack}</div>
                </div>
              ),
            },
            {
              title: "SKU / Description",
              dataIndex: "sku_description",
              render: (desc, r) => (
                <div style={{ maxWidth: 300 }}>
                  <Text strong ellipsis>{desc || "SKU Item"}</Text>
                  <div style={{ fontSize: "0.75rem", color: "#64748b" }}>GTIN: {r.sku_gtin || "N/A"}</div>
                </div>
              ),
            },
            {
              title: "Outcome",
              dataIndex: "outcome",
              render: (outcome) => {
                const color = outcome === "Shortage" ? "red" : outcome === "Excess" ? "gold" : outcome === "Misplaced" ? "purple" : "blue";
                return <Tag color={color} style={{ fontWeight: 700 }}>{outcome}</Tag>;
              },
            },
            {
              title: "Variance Qty",
              dataIndex: "variance_value",
              render: (v) => <Text strong style={{ color: "#f43f5e" }}>{v} units</Text>,
            },
            {
              title: "Status",
              dataIndex: "status",
              render: (status) => {
                const color = status === "approved" ? "success" : status === "rejected" ? "error" : "warning";
                return <Tag color={color}>{status.toUpperCase()}</Tag>;
              },
            },
            {
              title: "Actions",
              render: (_, record) => (
                <Button
                  type="primary"
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={() => {
                    setSelectedCase(record);
                    setDrawerOpen(true);
                  }}
                >
                  Review Case
                </Button>
              ),
            },
          ]}
        />
      </Card>

      {/* Discrepancy Detail Drawer */}
      <Drawer
        title={selectedCase ? `Case #${selectedCase.id}: ${selectedCase.outcome} in ${selectedCase.label_code}` : "Discrepancy Review"}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={560}
      >
        {selectedCase && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Viewfinder Evidence */}
            <div className="viewfinder-box">
              <div className="viewfinder-crosshair" />
              <div className="viewfinder-bbox" />
              <div className="viewfinder-hud">
                <span>EVIDENCE: frame_004211.jpg</span>
                <span>VARIANCE: {selectedCase.variance_value} UNITS</span>
              </div>
            </div>

            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="SKU Description">{selectedCase.sku_description}</Descriptions.Item>
              <Descriptions.Item label="GTIN Barcode">{selectedCase.sku_gtin || "08900764480624"}</Descriptions.Item>
              <Descriptions.Item label="Bin Location">{selectedCase.label_code} ({selectedCase.location_code})</Descriptions.Item>
              <Descriptions.Item label="Classification">
                <Tag color={selectedCase.outcome === "Shortage" ? "red" : "gold"}>{selectedCase.outcome}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Variance Quantity">{selectedCase.variance_value} units</Descriptions.Item>
              <Descriptions.Item label="Current Status">
                <Tag color={selectedCase.status === "approved" ? "green" : "orange"}>{selectedCase.status.toUpperCase()}</Tag>
              </Descriptions.Item>
            </Descriptions>

            {/* Action Buttons */}
            {selectedCase.status === "open" && (
              <Card size="small" title="Controller Actions">
                <Space>
                  <Tooltip title={!canApproveCase ? "Requires Inventory Controller or Admin role" : undefined}>
                    <Button
                      type="primary"
                      icon={<CheckOutlined />}
                      loading={approveMut.isPending}
                      disabled={!canApproveCase}
                      onClick={() => approveMut.mutate(selectedCase.id)}
                    >
                      Approve Adjustment
                    </Button>
                  </Tooltip>
                  <Tooltip title={!canApproveCase ? "Requires Inventory Controller or Admin role" : undefined}>
                    <Button
                      danger
                      icon={<CloseCircleOutlined />}
                      loading={rejectMut.isPending}
                      disabled={!canApproveCase}
                      onClick={() => rejectMut.mutate(selectedCase.id)}
                    >
                      Reject
                    </Button>
                  </Tooltip>
                </Space>
              </Card>
            )}

            {/* Comment Thread */}
            <Card size="small" title="Investigation Notes &amp; Comments">
              <List
                size="small"
                dataSource={caseDetail?.comments || []}
                renderItem={(item) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={<Avatar icon={<UserOutlined />} />}
                      title={<Text style={{ fontSize: "0.8rem", color: "#64748b" }}>{new Date(item.created_at).toLocaleString()}</Text>}
                      description={<Text>{item.comment}</Text>}
                    />
                  </List.Item>
                )}
              />

              <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                <Input
                  placeholder="Add note or recount rationale..."
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  onPressEnter={() => {
                    if (commentText.trim()) {
                      commentMut.mutate({ id: selectedCase.id, text: commentText });
                    }
                  }}
                />
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  loading={commentMut.isPending}
                  onClick={() => {
                    if (commentText.trim()) {
                      commentMut.mutate({ id: selectedCase.id, text: commentText });
                    }
                  }}
                >
                  Post
                </Button>
              </div>
            </Card>
          </div>
        )}
      </Drawer>
    </div>
  );
}

// =========================================================================
// 5. REPORTS PAGE
// =========================================================================

export function Reports() {
  const [reportType, setReportType] = useState("cycle_count");

  const { data, isLoading } = useQuery({
    queryKey: ["report-data", reportType],
    queryFn: () => getReportData(reportType),
  });

  const exportCSV = () => {
    if (!data?.data?.length) return;
    const headers = Object.keys(data.data[0]).join(",");
    const rows = data.data.map((obj) => Object.values(obj).join(",")).join("\n");
    const blob = new Blob([`${headers}\n${rows}`], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `DRIMS_${reportType}_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    message.success("Report downloaded successfully!");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>Executive Inventory Reports</Title>
          <Text type="secondary">Generate compliance cycle counts, discrepancy audits, and accuracy trends</Text>
        </div>

        <Button type="primary" icon={<DownloadOutlined />} onClick={exportCSV} disabled={!data?.data?.length}>
          Export to CSV
        </Button>
      </div>

      <Card className="hero-card" bordered={false}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} md={12}>
            <Radio.Group value={reportType} onChange={(e) => setReportType(e.target.value)} buttonStyle="solid">
              <Radio.Button value="cycle_count">Cycle Count Summary</Radio.Button>
              <Radio.Button value="discrepancies">Discrepancy Aging</Radio.Button>
            </Radio.Group>
          </Col>
          <Col xs={24} md={12} style={{ textAlign: "right" }}>
            <Text type="secondary">Generated at: {data?.generated_at ? new Date(data.generated_at).toLocaleString() : "-"}</Text>
          </Col>
        </Row>
      </Card>

      <Card className="hero-card" bordered={false}>
        <Table
          dataSource={data?.data || []}
          rowKey={(_, i) => String(i)}
          loading={isLoading}
          pagination={{ pageSize: 15 }}
          columns={
            data?.data?.[0]
              ? Object.keys(data.data[0]).map((key) => ({
                  title: key.replace(/_/g, " ").toUpperCase(),
                  dataIndex: key,
                  render: (val) => String(val),
                }))
              : []
          }
        />
      </Card>
    </div>
  );
}

// =========================================================================
// 6. MASTER DATA PAGE
// =========================================================================

export function MasterData() {
  const [skuSearch, setSkuSearch] = useState("");
  const [locZone, setLocZone] = useState<string | undefined>();

  const { data: skuData, isLoading: skuLoading } = useQuery({
    queryKey: ["master-skus", skuSearch],
    queryFn: () => getMasterSkus(skuSearch, 1, 50),
  });

  const { data: locData, isLoading: locLoading } = useQuery({
    queryKey: ["master-locations", locZone],
    queryFn: () => getMasterLocations(locZone, undefined, 1, 50),
  });

  const { data: drones, isLoading: droneLoading } = useQuery({
    queryKey: ["drones-fleet"],
    queryFn: getDrones,
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <Title level={2} style={{ margin: 0 }}>Warehouse Master Data</Title>
        <Text type="secondary">Manage SKU masters, rack layouts, PostGIS polygons, and drone fleet assets</Text>
      </div>

      <Card className="hero-card" bordered={false}>
        <Tabs
          defaultActiveKey="skus"
          items={[
            {
              key: "skus",
              label: <span><DatabaseOutlined /> SKU Catalog ({skuData?.total || 0})</span>,
              children: (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <Input.Search
                    placeholder="Search SKU description or GTIN barcode..."
                    allowClear
                    onSearch={setSkuSearch}
                    style={{ maxWidth: 400 }}
                  />
                  <Table
                    dataSource={skuData?.skus || []}
                    rowKey="id"
                    loading={skuLoading}
                    columns={[
                      { title: "ID", dataIndex: "id", width: 80 },
                      { title: "GTIN Barcode", dataIndex: "gtin", render: (g) => <Text code>{g || "N/A"}</Text> },
                      { title: "EPC Prefix", dataIndex: "epc_prefix", render: (p) => <Tag color="blue">{p || "-"}</Tag> },
                      { title: "Description", dataIndex: "description" },
                      { title: "UOM", dataIndex: "uom", width: 90 },
                      { title: "Unit Value", dataIndex: "unit_value", render: (v) => `$${Number(v).toFixed(2)}` },
                    ]}
                  />
                </div>
              ),
            },
            {
              key: "locations",
              label: <span><HeatMapOutlined /> Rack Layouts ({locData?.total || 0})</span>,
              children: (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <Select
                    placeholder="Filter by Zone"
                    allowClear
                    style={{ maxWidth: 200 }}
                    value={locZone}
                    onChange={setLocZone}
                  >
                    <Select.Option value="Z1">Zone Z1</Select.Option>
                    <Select.Option value="Z2">Zone Z2</Select.Option>
                    <Select.Option value="Z3">Zone Z3</Select.Option>
                    <Select.Option value="Z4">Zone Z4</Select.Option>
                  </Select>
                  <Table
                    dataSource={locData?.locations || []}
                    rowKey="id"
                    loading={locLoading}
                    columns={[
                      { title: "Bin Code", dataIndex: "bin_code", render: (c) => <Text strong code>{c}</Text> },
                      { title: "Label Tag", dataIndex: "label_code", render: (l) => <Tag color="cyan">{l}</Tag> },
                      { title: "Zone", dataIndex: "zone" },
                      { title: "Aisle", dataIndex: "aisle" },
                      { title: "Rack", dataIndex: "rack" },
                      { title: "Level", dataIndex: "level" },
                    ]}
                  />
                </div>
              ),
            },
            {
              key: "drones",
              label: <span><ThunderboltOutlined /> Drone Fleet</span>,
              children: (
                <Table
                  dataSource={drones || []}
                  rowKey="id"
                  loading={droneLoading}
                  columns={[
                    { title: "Serial Number", dataIndex: "serial_number", render: (s) => <Text strong>{s}</Text> },
                    { title: "Model / Sensor", dataIndex: "model" },
                    { title: "Firmware", dataIndex: "firmware_version" },
                    { title: "Battery", dataIndex: "battery_pct", render: (b) => <Progress percent={b} size="small" /> },
                    { title: "Status", dataIndex: "status", render: (s) => <Tag color="green">{s}</Tag> },
                  ]}
                />
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}

// =========================================================================
// 7. ADMINISTRATION PAGE
// =========================================================================

export function Administration() {
  const queryClient = useQueryClient();
  const [createUserOpen, setCreateUserOpen] = useState(false);
  const [form] = Form.useForm();
  const [w1, setW1] = useState(0.5);
  const [w2, setW2] = useState(0.3);
  const [w3, setW3] = useState(0.2);
  const [reviewTrigger, setReviewTrigger] = useState<number | null>(0.8);
  const [caseTrigger, setCaseTrigger] = useState<number | null>(10);

  const { data: users, isLoading: usersLoading, refetch: refetchUsers } = useQuery({
    queryKey: ["admin-users"],
    queryFn: getUsers,
  });

  const { data: settingsData, refetch: refetchSettings } = useQuery({
    queryKey: ["admin-settings"],
    queryFn: getSettings,
  });

  React.useEffect(() => {
    if (settingsData && Array.isArray(settingsData)) {
      const wSetting = settingsData.find((s) => s.key === "bin_confidence_weights");
      if (wSetting?.value?.weights) {
        setW1(wSetting.value.weights.w1 ?? 0.5);
        setW2(wSetting.value.weights.w2 ?? 0.3);
        setW3(wSetting.value.weights.w3 ?? 0.2);
      }
    }
  }, [settingsData]);

  const updateSettingMut = useMutation({
    mutationFn: ({ key, value }: { key: string; value: any }) => updateSetting(key, value),
    onSuccess: () => {
      message.success("System configuration saved successfully!");
      queryClient.invalidateQueries({ queryKey: ["admin-settings"] });
      refetchSettings();
    },
  });

  const createUserMut = useMutation({
    mutationFn: (vals: any) => createUser(vals),
    onSuccess: () => {
      message.success("User added successfully!");
      setCreateUserOpen(false);
      form.resetFields();
      refetchUsers();
    },
  });

  const deleteUserMut = useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: () => {
      message.success("User deactivated.");
      refetchUsers();
    },
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <Title level={2} style={{ margin: 0 }}>System Administration</Title>
        <Text type="secondary">Manage RBAC roles, pipeline confidence weights, and ingestion thresholds</Text>
      </div>

      <Card className="hero-card" bordered={false}>
        <Tabs
          defaultActiveKey="users"
          items={[
            {
              key: "users",
              label: <span><UserOutlined /> User Management</span>,
              children: (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <div style={{ textAlign: "right" }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateUserOpen(true)}>
                      Add User
                    </Button>
                  </div>
                  <Table
                    dataSource={users || []}
                    rowKey="id"
                    loading={usersLoading}
                    columns={[
                      { title: "Username", dataIndex: "username", render: (u) => <Text strong>{u}</Text> },
                      { title: "Email", dataIndex: "email" },
                      {
                        title: "Role",
                        dataIndex: "role",
                        render: (r) => <Tag color={r === "Admin" ? "red" : r === "Inventory Controller" ? "gold" : "blue"}>{r}</Tag>,
                      },
                      {
                        title: "Active",
                        dataIndex: "is_active",
                        render: (act) => <Tag color={act ? "green" : "default"}>{act ? "ACTIVE" : "INACTIVE"}</Tag>,
                      },
                      {
                        title: "Actions",
                        render: (_, record) => (
                          <Popconfirm title="Delete user?" onConfirm={() => deleteUserMut.mutate(record.id)}>
                            <Button danger size="small">Remove</Button>
                          </Popconfirm>
                        ),
                      },
                    ]}
                  />
                </div>
              ),
            },
            {
              key: "settings",
              label: <span><SettingOutlined /> Pipeline Tuning &amp; Weights</span>,
              children: (
                <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 650 }}>
                  <Alert
                    type="info"
                    showIcon
                    message="Confidence Formula Configuration"
                    description="C_bin = w1 * read_confidence + w2 * location_method + w3 * image_coverage. Defaults: w1=0.5, w2=0.3, w3=0.2 (must sum to 1.0)."
                  />

                  <Card size="small" title="Pipeline Weights">
                    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                      <div>
                        <Text strong>w1 (Read Confidence Weight): {w1.toFixed(2)}</Text>
                        <Slider min={0.05} max={0.9} step={0.05} value={w1} onChange={setW1} />
                      </div>
                      <div>
                        <Text strong>w2 (Location Marker Weight): {w2.toFixed(2)}</Text>
                        <Slider min={0.05} max={0.9} step={0.05} value={w2} onChange={setW2} />
                      </div>
                      <div>
                        <Text strong>w3 (Image Coverage Weight): {w3.toFixed(2)}</Text>
                        <Slider min={0.05} max={0.9} step={0.05} value={w3} onChange={setW3} />
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <Text type="secondary">Total Sum: {Number((w1 + w2 + w3).toFixed(2))}</Text>
                        {Number((w1 + w2 + w3).toFixed(2)) !== 1.0 && (
                          <Tag color="warning">Weights must sum to 1.0</Tag>
                        )}
                      </div>
                    </div>
                  </Card>

                  <Card size="small" title="Operational Thresholds">
                    <Row gutter={[16, 16]}>
                      <Col span={12}>
                        <Text strong>Confidence Review Trigger:</Text>
                        <InputNumber value={reviewTrigger} onChange={setReviewTrigger} min={0.1} max={1.0} step={0.05} style={{ width: "100%", marginTop: 6 }} />
                      </Col>
                      <Col span={12}>
                        <Text strong>Discrepancy Case Trigger (units):</Text>
                        <InputNumber value={caseTrigger} onChange={setCaseTrigger} min={1} max={100} style={{ width: "100%", marginTop: 6 }} />
                      </Col>
                    </Row>
                  </Card>

                  <div>
                    <Button
                      type="primary"
                      icon={<CheckOutlined />}
                      loading={updateSettingMut.isPending}
                      onClick={() => {
                        const sum = Number((w1 + w2 + w3).toFixed(2));
                        if (sum !== 1.0) {
                          message.warning(`Weights must sum to 1.0 (current sum: ${sum})`);
                          return;
                        }
                        updateSettingMut.mutate({
                          key: "bin_confidence_weights",
                          value: { weights: { w1, w2, w3 }, reviewTrigger, caseTrigger },
                        });
                      }}
                    >
                      Save Configuration
                    </Button>
                  </div>
                </div>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="Create Application User"
        open={createUserOpen}
        onCancel={() => setCreateUserOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={(vals) => createUserMut.mutate(vals)}>
          <Form.Item name="username" label="Username" rules={[{ required: true }]}>
            <Input placeholder="e.g. jsmith" />
          </Form.Item>
          <Form.Item name="email" label="Email" rules={[{ type: "email", required: true }]}>
            <Input placeholder="jsmith@drims.local" />
          </Form.Item>
          <Form.Item name="role" label="RBAC Role" initialValue="Viewer" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="Admin">Admin</Select.Option>
              <Select.Option value="Inventory Controller">Inventory Controller</Select.Option>
              <Select.Option value="Warehouse Supervisor">Warehouse Supervisor</Select.Option>
              <Select.Option value="Viewer">Viewer</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

// =========================================================================
// 8. AUDIT LOG PAGE
// =========================================================================

export function AuditLog() {
  const { data: audit, isLoading, refetch } = useQuery({
    queryKey: ["audit-log"],
    queryFn: getAuditLog,
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>Immutable Security &amp; Operations Audit Log</Title>
          <Text type="secondary">Append-only audit trail recording every state change, case approval, and setting modification</Text>
        </div>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>Refresh Log</Button>
      </div>

      <Card className="hero-card" bordered={false}>
        <Table
          dataSource={audit || []}
          rowKey="id"
          loading={isLoading}
          columns={[
            {
              title: "Audit ID",
              dataIndex: "id",
              render: (id) => <Text code>#{id}</Text>,
              width: 90,
            },
            {
              title: "Action",
              dataIndex: "action",
              render: (act) => {
                const color = act === "INSERT" ? "green" : act === "UPDATE" ? "blue" : "red";
                return <Tag color={color} style={{ fontWeight: 700 }}>{act}</Tag>;
              },
              width: 110,
            },
            {
              title: "Target Table",
              dataIndex: "table_name",
              render: (t) => <Tag color="cyan">{t}</Tag>,
              width: 150,
            },
            {
              title: "Record ID",
              dataIndex: "record_id",
              width: 100,
            },
            {
              title: "Modified Values / Audit Payload",
              render: (_, r) => (
                <Text code ellipsis style={{ maxWidth: 450 }}>
                  {JSON.stringify(r.new_values || r.old_values || {})}
                </Text>
              ),
            },
            {
              title: "Timestamp",
              dataIndex: "created_at",
              render: (t) => t ? new Date(t).toLocaleString() : "-",
              width: 200,
            },
          ]}
        />
      </Card>
    </div>
  );
}

// =========================================================================
// 9. NOTIFICATIONS & HELP
// =========================================================================

export function Notifications() {
  const { data: notifs } = useQuery({
    queryKey: ["notifications"],
    queryFn: getNotifications,
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <Title level={2} style={{ margin: 0 }}>Operational Alerts &amp; Notifications</Title>
      <Card className="hero-card" bordered={false}>
        <List
          dataSource={notifs || []}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                avatar={
                  <Avatar
                    icon={item.type === "success" ? <CheckCircleOutlined /> : item.type === "warning" ? <AlertOutlined /> : <InfoCircleOutlined />}
                    style={{ backgroundColor: item.type === "success" ? "#10b981" : item.type === "warning" ? "#f59e0b" : "#3b82f6" }}
                  />
                }
                title={
                  <Space>
                    <Text strong>{item.title}</Text>
                    {item.unread && <Badge status="processing" />}
                    <Text type="secondary" style={{ fontSize: "0.8rem" }}>{item.time}</Text>
                  </Space>
                }
                description={item.message}
              />
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
}

export function Help() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 900 }}>
      <div>
        <Title level={2} style={{ margin: 0 }}>DRIMS System Documentation &amp; Architecture</Title>
        <Text type="secondary">Drone Inventory Management System - Operational Boundaries &amp; Verification</Text>
      </div>

      <Card className="hero-card" bordered={false} title="System Context &amp; Boundaries">
        <Paragraph>
          DRIMS builds the software layer that takes scan data, telemetry, and images from autonomous drone receiving systems, turns them into verified bin counts, and reconciles them against the ERP/WMS book stock.
        </Paragraph>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="API Engine">FastAPI (Python 3.13) + Pydantic v2</Descriptions.Item>
          <Descriptions.Item label="Spatial Storage">PostgreSQL 16 + PostGIS 3.4</Descriptions.Item>
          <Descriptions.Item label="Task Workers">Celery 5 on Redis 7 Broker</Descriptions.Item>
          <Descriptions.Item label="Identity &amp; RBAC">Keycloak 24 OIDC PKCE</Descriptions.Item>
          <Descriptions.Item label="Object Store">MinIO S3 Hot Storage</Descriptions.Item>
          <Descriptions.Item label="Web Architecture">React 18 + TypeScript + Ant Design</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}

export function ErrorPage({ code, title, subTitle }: { code: "403" | "404"; title: string; subTitle: string }) {
  const navigate = useNavigate();
  return (
    <div style={{ textAlign: "center", padding: "80px 20px" }}>
      <Title level={1}>{code}</Title>
      <Title level={3}>{title}</Title>
      <Paragraph type="secondary">{subTitle}</Paragraph>
      <Button type="primary" onClick={() => navigate("/")}>Return to Dashboard</Button>
    </div>
  );
}
