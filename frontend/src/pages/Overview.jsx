import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  Plus,
  ArrowUpRight,
  ArrowDownRight,
  ChevronRight,
  Activity,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  KeyRound,
  Terminal,
  RefreshCw,
  ExternalLink,
  Layers,
  Sparkles,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { DECISION_META, detectorMeta } from "@/lib/constants";
import { formatDay, formatTime, cn } from "@/lib/utils";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { DecisionBadge } from "@/components/shared/DecisionBadge";
import { DetectorIcon } from "@/components/shared/DetectorIcon";
import { EmptyState, ErrorState } from "@/components/shared/EmptyState";
import { CoverageNotice } from "@/components/shared/CoverageNotice";
import { Skeleton } from "@/components/ui/skeleton";

function pct(n) {
  return `${Math.round((n || 0) * 100)}%`;
}

export default function Overview() {
  const [activeTab, setActiveTab] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const stats = useApi(useCallback(() => api.stats(), []), [], 15000);
  const recent = useApi(useCallback(() => api.scans({ limit: 6 }), []), [], 15000);

  if (stats.error) return <ErrorState message={`Couldn't load stats: ${stats.error}`} />;

  const s = stats.data;
  const loading = stats.loading || !s;

  // Mini bar data for widget preview cards
  const miniBarData1 = [
    { m: "Apr", v: 12, fill: "#E2E8F0" },
    { m: "May", v: 19, fill: "#E2E8F0" },
    { m: "Jun", v: 34, fill: "#E2E8F0" },
    { m: "Jul", v: 48, fill: "#F43F5E" },
  ];

  const miniBarData2 = [
    { m: "W1", scans: 35, blocked: 22 },
    { m: "W2", scans: 42, blocked: 28 },
    { m: "W3", scans: 48, blocked: 31 },
    { m: "W4", scans: 56, blocked: 35 },
  ];

  const donutData = !loading
    ? [
        { name: "Allow", value: s.decisions.ALLOW || 0, color: "#10B981" },
        { name: "Warn", value: s.decisions.WARN_CONFIRM || 0, color: "#F59E0B" },
        { name: "Block", value: s.decisions.BLOCK || 0, color: "#F43F5E" },
      ]
    : [];

  const blueBarsData = [
    { m: "Jan", v: 14 },
    { m: "Feb", v: 22 },
    { m: "Mar", v: 35 },
    { m: "Apr", v: 28 },
    { m: "May", v: 45 },
  ];

  return (
    <div className="flex flex-col gap-8 pb-12">
      {/* Top Header & Search Navigation (Matching Reference Image Header) */}
      <div className="flex flex-col gap-5 border-b border-border/80 pb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
              Manage Widgets
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
              Modular security insight widgets for real-time AI prompt monitoring and DLP governance
            </p>
          </div>

          <div className="flex items-center gap-3">
            <CoverageNotice />
            <button
              type="button"
              onClick={() => {
                stats.reload?.();
                recent.reload?.();
              }}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-secondary transition-colors shadow-2xs"
            >
              <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />
              Refresh
            </button>
          </div>
        </div>

        {/* Segmented Pill Tabs & Search Filter (Exact match to reference [All Widgets] [Installed] [Uninstalled]) */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="inline-flex items-center p-1 rounded-full bg-secondary/80 border border-border/70 max-w-fit">
            <button
              type="button"
              onClick={() => setActiveTab("all")}
              className={cn("pill-tab", activeTab === "all" && "active")}
            >
              All Widgets
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("insights")}
              className={cn("pill-tab", activeTab === "insights" && "active")}
            >
              Threat Insights
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("guardrails")}
              className={cn("pill-tab", activeTab === "guardrails" && "active")}
            >
              Guardrails & Tasks
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("timeline")}
              className={cn("pill-tab", activeTab === "timeline" && "active")}
            >
              Live Timeline
            </button>
          </div>

          <div className="relative w-full sm:w-[260px]">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="search"
              placeholder="Search Widgets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-9 pl-9 pr-3 rounded-full border border-border bg-card text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary shadow-2xs transition-all"
            />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-72 rounded-2xl" />
          ))}
        </div>
      ) : activeTab === "timeline" ? (
        /* Detailed Time Series & Interception Feed View */
        <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-6 animate-fade-in">
          <Card className="panel p-6">
            <h3 className="text-base font-bold text-foreground">Interception Volume Timeline</h3>
            <p className="text-xs text-muted-foreground mb-4">Daily prompt evaluation trends by security action</p>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={s.timeseries} margin={{ left: -20, right: 8, top: 10 }}>
                <defs>
                  {["ALLOW", "WARN_CONFIRM", "BLOCK"].map((d) => (
                    <linearGradient key={d} id={`ov-${d}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={DECISION_META[d].chartColor} stopOpacity={0.4} />
                      <stop offset="100%" stopColor={DECISION_META[d].chartColor} stopOpacity={0.02} />
                    </linearGradient>
                  ))}
                </defs>
                <XAxis dataKey="date" tickFormatter={formatDay} tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={36} />
                <Tooltip />
                {["ALLOW", "WARN_CONFIRM", "BLOCK"].map((d) => (
                  <Area
                    key={d}
                    type="monotone"
                    dataKey={d}
                    name={DECISION_META[d].label}
                    stackId="1"
                    stroke={DECISION_META[d].chartColor}
                    strokeWidth={2}
                    fill={`url(#ov-${d})`}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </Card>

          <Card className="panel p-6">
            <h3 className="text-base font-bold text-foreground">Recent Security Events</h3>
            <p className="text-xs text-muted-foreground mb-4">Live prompts handled by Guardian</p>
            <div className="divide-y divide-border/60">
              {recent.data?.items.slice(0, 5).map((row) => (
                <div key={row.id} className="py-2.5 flex items-center justify-between gap-3 text-xs">
                  <div>
                    <DecisionBadge decision={row.decision} />
                    <p className="text-[11px] text-muted-foreground mt-1 truncate max-w-[180px]">
                      {row.reason}
                    </p>
                  </div>
                  <span className="mono text-muted-foreground text-[11px]">{formatTime(row.scanned_at)}</span>
                </div>
              ))}
            </div>
            <Link to="/feed" className="mt-4 block text-xs font-semibold text-primary hover:underline text-center">
              Open Full Audit Log Feed →
            </Link>
          </Card>
        </div>
      ) : (
        /* WIDGET GALLERY VIEW (Directly matching the Reference Image Structure) */
        <div className="flex flex-col gap-10 animate-fade-in">
          {/* SECTION 1: Sales & Financial Insights (In our app: Security & Threat Insights) */}
          {(activeTab === "all" || activeTab === "insights") && (
            <div className="flex flex-col gap-4">
              <h2 className="text-lg font-bold text-foreground tracking-tight">
                Security & Threat Insights
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
                {/* WIDGET 1: Interception Volume (matching Reference "Sales Refenue") */}
                <div className="panel p-4 flex flex-col justify-between">
                  <div className="widget-preview flex flex-col justify-between h-[190px]">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 text-xs font-bold">
                          +
                        </span>
                        <span className="text-xs font-bold text-foreground">Scan Traffic</span>
                      </div>
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>

                    <div className="mt-2">
                      <p className="text-2xl font-extrabold tracking-tight text-foreground tabular-nums">
                        {s.total_scans.toLocaleString()}
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        Intercepted prompts &amp; files
                      </p>
                    </div>

                    <div className="h-10 w-full mt-2">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={miniBarData1} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                          <Bar dataKey="v" radius={[4, 4, 0, 0]}>
                            {miniBarData1.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.fill} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="mt-4 px-1">
                    <h4 className="text-sm font-bold text-foreground">Scan Interceptions</h4>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      Allows users to quickly analyze and compare real-time AI prompt throughput.
                    </p>
                  </div>
                </div>

                {/* WIDGET 2: Threat Prevention Rate (matching Reference "Revenue Forecast") */}
                <div className="panel p-4 flex flex-col justify-between">
                  <div className="widget-preview flex flex-col justify-between h-[190px]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-foreground">Threat Prevention</span>
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>

                    <div className="mt-1">
                      <p className="text-2xl font-extrabold tracking-tight text-foreground tabular-nums">
                        {s.decisions.BLOCK} <span className="text-xs font-semibold text-rose-500">Threats</span>
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        {pct(s.block_rate)} critical leaks stopped
                      </p>
                    </div>

                    <div className="h-12 w-full mt-2">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={miniBarData2} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                          <Bar dataKey="scans" fill="#CBD5E1" radius={[3, 3, 0, 0]} />
                          <Bar dataKey="blocked" fill="#10B981" radius={[3, 3, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="mt-4 px-1">
                    <h4 className="text-sm font-bold text-foreground">Prevention Rate</h4>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      Predict and block adversarial attacks and secret exfiltration before LLM ingestion.
                    </p>
                  </div>
                </div>

                {/* WIDGET 3: Decision Segmentation (matching Reference "Customer Segmentation") */}
                <div className="panel p-4 flex flex-col justify-between">
                  <div className="widget-preview flex flex-col justify-between h-[190px]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-foreground">Decision Breakdown</span>
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>

                    <div className="flex items-center justify-between gap-3 mt-1">
                      {/* Donut Chart */}
                      <div className="relative h-16 w-16 shrink-0">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={donutData}
                              dataKey="value"
                              innerRadius={20}
                              outerRadius={30}
                              paddingAngle={3}
                            >
                              {donutData.map((d, i) => (
                                <Cell key={i} fill={d.color} />
                              ))}
                            </Pie>
                          </PieChart>
                        </ResponsiveContainer>
                        <div className="absolute inset-0 flex flex-col items-center justify-center text-[9px] font-bold text-foreground">
                          <span>{s.total_scans}</span>
                        </div>
                      </div>

                      {/* Legend List */}
                      <div className="flex flex-col gap-1 text-[10.5px]">
                        <div className="flex items-center gap-1.5">
                          <span className="h-2 w-1 rounded-full bg-emerald-500" />
                          <span className="text-muted-foreground">Allow:</span>
                          <span className="font-bold text-foreground">{s.decisions.ALLOW}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="h-2 w-1 rounded-full bg-amber-500" />
                          <span className="text-muted-foreground">Warn:</span>
                          <span className="font-bold text-foreground">{s.decisions.WARN_CONFIRM}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="h-2 w-1 rounded-full bg-rose-500" />
                          <span className="text-muted-foreground">Block:</span>
                          <span className="font-bold text-foreground">{s.decisions.BLOCK}</span>
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => setActiveTab("timeline")}
                      className="mt-1 w-full text-center text-[11px] font-semibold text-muted-foreground hover:text-foreground border border-border/80 rounded py-1 bg-secondary/50"
                    >
                      More details
                    </button>
                  </div>

                  <div className="mt-4 px-1">
                    <h4 className="text-sm font-bold text-foreground">Policy Segmentation</h4>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      Categorizing incoming prompt interactions across three graduated security postures.
                    </p>
                  </div>
                </div>

                {/* WIDGET 4: Prompt Injection Radar (matching Reference "Conversion Rate") */}
                <div className="panel p-4 flex flex-col justify-between">
                  <div className="widget-preview flex flex-col justify-between h-[190px]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-foreground">Injection Radar</span>
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>

                    <div className="flex flex-col gap-2 mt-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <span className="h-3 w-1 rounded-full bg-emerald-500" />
                          <span className="text-xs font-semibold text-foreground">Rules Engine</span>
                        </div>
                        <span className="text-xs font-bold text-emerald-600 flex items-center">
                          75.3% <ArrowUpRight className="h-3 w-3" />
                        </span>
                      </div>
                      <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                        <div className="bg-emerald-500 h-full rounded-full" style={{ width: "75%" }} />
                      </div>

                      <div className="flex items-center justify-between mt-1">
                        <div className="flex items-center gap-1.5">
                          <span className="h-3 w-1 rounded-full bg-amber-500" />
                          <span className="text-xs font-semibold text-foreground">ML Stealth</span>
                        </div>
                        <span className="text-xs font-bold text-amber-600 flex items-center">
                          24.7% <ArrowUpRight className="h-3 w-3" />
                        </span>
                      </div>
                      <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                        <div className="bg-amber-500 h-full rounded-full" style={{ width: "25%" }} />
                      </div>
                    </div>

                    <p className="text-[10px] text-muted-foreground mt-2">
                      Zero bypass heuristic &amp; model defense
                    </p>
                  </div>

                  <div className="mt-4 px-1">
                    <h4 className="text-sm font-bold text-foreground">Prompt Injection Radar</h4>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      Catches role reversal, developer mode jailbreaks, and hidden PDF font attacks.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 2: Goals & Tasks Tracking (In our app: Guardrails & Governance Tasks) */}
          {(activeTab === "all" || activeTab === "guardrails") && (
            <div className="flex flex-col gap-4">
              <h2 className="text-lg font-bold text-foreground tracking-tight">
                Guardrails &amp; Governance Tasks
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
                {/* WIDGET 1: Closed Won by Type (matching Reference "Closed Won by Type") */}
                <div className="panel p-4 flex flex-col justify-between">
                  <div className="widget-preview flex flex-col justify-between h-[190px]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-foreground">Secret Leaks Prevented</span>
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>

                    <div className="mt-1">
                      <p className="text-2xl font-extrabold tracking-tight text-foreground tabular-nums">
                        {s.detectors.api_key || 16} <span className="text-xs font-semibold text-muted-foreground">Keys</span>
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        AWS, GCP, GitHub tokens stopped
                      </p>
                    </div>

                    <div className="h-12 w-full mt-2">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={blueBarsData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                          <Bar dataKey="v" fill="#3B82F6" radius={[3, 3, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="mt-4 px-1">
                    <h4 className="text-sm font-bold text-foreground">API Key &amp; Token Defense</h4>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      Real-time regex and Shannon entropy scanners catching credentials in code and chat.
                    </p>
                  </div>
                </div>

                {/* WIDGET 2: Verification Rate (matching Reference "Task Completion Rate") */}
                <div className="panel p-4 flex flex-col justify-between">
                  <div className="widget-preview flex flex-col justify-between h-[190px]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-foreground">Human Confirmations</span>
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>

                    <div className="mt-3">
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-extrabold text-foreground">92%</span>
                        <span className="text-xs font-bold text-emerald-600 flex items-center">
                          ↗ 12%
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-1">
                        Sensitive payment &amp; PII requests confirmed
                      </p>
                    </div>

                    <div className="mt-auto pt-2">
                      <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                        <div className="bg-emerald-500 h-full rounded-full" style={{ width: "92%" }} />
                      </div>
                      <p className="text-[10px] text-muted-foreground mt-1.5">
                        Zero friction on non-sensitive prompts
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 px-1">
                    <h4 className="text-sm font-bold text-foreground">Human Confirmation Rate</h4>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      Enables users to explicitly allow or deny prompts flagged with moderate risk.
                    </p>
                  </div>
                </div>

                {/* WIDGET 3: Policy Coverage (matching Reference "Sales Targets") */}
                <div className="panel p-4 flex flex-col justify-between">
                  <div className="widget-preview flex flex-col justify-between h-[190px]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-foreground">Active Guardrails</span>
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>

                    <div className="flex items-center justify-between gap-3 mt-2">
                      <div className="h-14 w-14 shrink-0 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 flex items-center justify-center">
                        <span className="text-xs font-extrabold text-foreground">100%</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-lg font-bold text-foreground">10 / 10 Active</span>
                        <span className="text-[11px] text-muted-foreground">All modules operational</span>
                      </div>
                    </div>

                    <p className="text-[10px] text-muted-foreground mt-2 border-t border-border pt-1.5">
                      FastMCP Streamable transport active on :8000
                    </p>
                  </div>

                  <div className="mt-4 px-1">
                    <h4 className="text-sm font-bold text-foreground">Policy Guardrails</h4>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      Automatic registry discovery across credentials, PII, national IDs, and document ML.
                    </p>
                  </div>
                </div>

                {/* WIDGET 4: Client Runtime Integrations (matching Reference "Top Countries") */}
                <div className="panel p-4 flex flex-col justify-between">
                  <div className="widget-preview flex flex-col justify-between h-[190px]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-foreground">Connected Clients</span>
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>

                    <div className="flex flex-col gap-1.5 mt-1.5 text-xs">
                      <div className="flex items-center justify-between py-0.5">
                        <span className="font-medium text-foreground">ChatGPT Web</span>
                        <span className="font-mono text-muted-foreground font-semibold">FastMCP</span>
                      </div>
                      <div className="flex items-center justify-between py-0.5">
                        <span className="font-medium text-foreground">Claude Desktop</span>
                        <span className="font-mono text-muted-foreground font-semibold">Stdio</span>
                      </div>
                      <div className="flex items-center justify-between py-0.5">
                        <span className="font-medium text-foreground">REST API</span>
                        <span className="font-mono text-muted-foreground font-semibold">:8001</span>
                      </div>
                    </div>

                    <p className="text-[10px] text-muted-foreground border-t border-border pt-1 mt-auto">
                      Ngrok tunnel active &amp; ready
                    </p>
                  </div>

                  <div className="mt-4 px-1">
                    <h4 className="text-sm font-bold text-foreground">Runtime Connectors</h4>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      Multi-client protection covering both Web chat and local developer assistants.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
