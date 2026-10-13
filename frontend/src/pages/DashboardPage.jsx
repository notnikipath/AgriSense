import React, { useEffect, useMemo, useState } from "react";

import { KpiCard } from "../components/KpiCard";
import { TaskBoard } from "../components/TaskBoard";

const gatewayUrl = import.meta.env.VITE_API_GATEWAY_URL || "http://localhost:8580";

const emptyDashboard = {
  field: { field_id: "FIELD-DEMO-1", name: "Demo field", crop_type: "wheat", area_ha: 0 },
  iot_snapshot: {
    sensor_count: 0,
    stats: { avg_moisture_pct: 0, avg_temperature_c: 0, avg_light_lux: 0 },
    latest_weather: null,
    latest_drone_scan: null,
  },
  iot_alerts: { items: [], count: 0 },
  analysis_stats: { avg_moisture_pct: 0, avg_temperature_c: 0, avg_light_lux: 0 },
  analysis_kpi: { yield_mape_pct: 0, target_yield_mape_pct: 12 },
  tasks: { items: [] },
  workload: { assignees: {}, machinery: {} },
  analytics_kpi: {
    yield_mape_pct: 0,
    target_yield_mape_pct: 12,
    avg_sensor_latency_seconds: 0,
    target_sensor_latency_seconds: 10,
    sensor_capacity_target: 10000,
  },
  yearly_yield: { items: [] },
  economics: { total_revenue_rub: 0, total_cost_rub: 0, margin_pct: 0 },
  weather: null,
  integrations: { items: [] },
  notifications: { items: [] },
};

async function loadDashboard(fieldId) {
  const response = await fetch(`${gatewayUrl}/dashboard/${fieldId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch dashboard: ${response.status}`);
  }
  return response.json();
}

export function DashboardPage() {
  const [fieldId, setFieldId] = useState("FIELD-DEMO-1");
  const [theme, setTheme] = useState("light");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);
  const [dashboard, setDashboard] = useState(emptyDashboard);

  useEffect(() => {
    let active = true;

    loadDashboard(fieldId)
      .then((payload) => {
        if (!active) {
          return;
        }
        setDashboard({ ...emptyDashboard, ...payload });
        setStatus("succeeded");
        setError(null);
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        setStatus("failed");
        setError(err.message);
      });

    return () => {
      active = false;
    };
  }, [fieldId]);

  const statusLabel = useMemo(() => {
    if (status === "loading") {
      return "loading";
    }
    if (status === "failed") {
      return "Service unavailable";
    }
    return "live";
  }, [status]);

  const refresh = async () => {
    try {
      setStatus("loading");
      const payload = await loadDashboard(fieldId);
      setDashboard({ ...emptyDashboard, ...payload });
      setStatus("succeeded");
      setError(null);
    } catch (err) {
      setStatus("failed");
      setError(err.message);
    }
  };

  const tasks = dashboard.tasks?.items || [];
  const latestWeather = dashboard.weather || dashboard.iot_snapshot?.latest_weather;

  return (
    <div className={`app theme-${theme}`}>
      <div className="background-orb orb-a" />
      <div className="background-orb orb-b" />

      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">AgriSense Control Center</p>
          <h1>Field operations</h1>
          <p className="sub">
            AgriSense connects IoT sensors, field maps, analytics, and operational planning to keep crop decisions data-driven.
          </p>
          <div className="hero-badges">
            <span>Auto irrigation</span>
            <span>Crop rotation optimization</span>
            <span>Weather integration</span>
            <span>Offline mobile maps</span>
            <span>Realtime telemetry scaling</span>
            <span>Map cache</span>
          </div>
        </div>

        <div className="hero-panel">
          <label>
            Field ID
            <input value={fieldId} onChange={(event) => setFieldId(event.target.value)} placeholder="FIELD-DEMO-1" />
          </label>
          <div className="hero-actions">
            <button onClick={refresh} disabled={status === "loading"}>Refresh dashboard</button>
            <button className="ghost" onClick={() => setTheme((current) => (current === "light" ? "dark" : "light"))}>
              Theme
            </button>
          </div>
          <p className="status-line" role="status" aria-live="polite">Status: {statusLabel}</p>
        </div>
      </header>

      <section className="kpi-grid">
        <KpiCard
          title="Yield MAPE"
          value={`${Number(dashboard.analytics_kpi?.yield_mape_pct || 0).toFixed(1)}%`}
          target={`Target < ${dashboard.analytics_kpi?.target_yield_mape_pct || 12}%`}
          ok={Number(dashboard.analytics_kpi?.yield_mape_pct || 100) <= Number(dashboard.analytics_kpi?.target_yield_mape_pct || 12)}
        />
        <KpiCard
          title="Sensor Latency"
          value={`${Number(dashboard.analytics_kpi?.avg_sensor_latency_seconds || 0).toFixed(2)} sec`}
          target={`Target < ${dashboard.analytics_kpi?.target_sensor_latency_seconds || 10} sec`}
          ok={Number(dashboard.analytics_kpi?.avg_sensor_latency_seconds || 100) <= Number(dashboard.analytics_kpi?.target_sensor_latency_seconds || 10)}
        />
        <KpiCard
          title="Sensor Capacity"
          value={`${dashboard.analytics_kpi?.sensor_capacity_target || 10000}`}
          target="Platform objective"
          ok={Number(dashboard.analytics_kpi?.sensor_capacity_target || 0) >= 10000}
        />
        <KpiCard
          title="Margin"
          value={`${Number(dashboard.economics?.margin_pct || 0).toFixed(1)}%`}
          target="Economic efficiency"
          ok={Number(dashboard.economics?.margin_pct || 0) > 0}
        />
      </section>

      {error ? <div className="error-banner" role="alert">{error}</div> : null}

      <section className="content-grid">
        <article className="panel panel-featured">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Field Profile</p>
              <h2>
                {dashboard.field?.name} ({dashboard.field?.field_id})
              </h2>
            </div>
            <span className="pill">{dashboard.field?.crop_type}</span>
          </div>
          <p className="panel-copy">
            Region: {dashboard.field?.region}. Area: {dashboard.field?.area_ha} ha. Planned operations are synced with agronomic recommendations.
          </p>
          <div className="metrics-row">
            <div>
              <strong>{Number(dashboard.analysis_stats?.avg_moisture_pct || 0).toFixed(1)}</strong>
              <span>soil moisture %</span>
            </div>
            <div>
              <strong>{Number(dashboard.analysis_stats?.avg_temperature_c || 0).toFixed(1)}</strong>
              <span>temperature C</span>
            </div>
            <div>
              <strong>{Math.round(Number(dashboard.analysis_stats?.avg_light_lux || 0))}</strong>
              <span>light lux</span>
            </div>
            <div>
              <strong>{tasks.length}</strong>
              <span>planned tasks</span>
            </div>
          </div>
          <TaskBoard tasks={tasks} />
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Sensor Pulse</p>
              <h2>Field telemetry</h2>
            </div>
            <span className="pill accent">{dashboard.iot_snapshot?.sensor_count || 0} sensors</span>
          </div>
          <div className="signal-grid">
            <div className="signal-card">
              <span>Alerts</span>
              <strong>{dashboard.iot_alerts?.count || 0}</strong>
            </div>
            <div className="signal-card">
              <span>Weather</span>
              <strong>{latestWeather ? `${latestWeather.temperature_c} C` : "N/A"}</strong>
            </div>
            <div className="signal-card">
              <span>Rainfall</span>
              <strong>{latestWeather ? `${latestWeather.rainfall_mm} mm` : "N/A"}</strong>
            </div>
            <div className="signal-card">
              <span>Humidity</span>
              <strong>{latestWeather ? `${latestWeather.humidity_pct}%` : "N/A"}</strong>
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Annual Yield</p>
              <h2>Comparison by years</h2>
            </div>
            <span className="pill">{dashboard.yearly_yield?.items?.length || 0} years</span>
          </div>
          <div className="stack-list">
            {(dashboard.yearly_yield?.items || []).map((item) => (
              <div className="stack-item" key={item.year}>
                <div>
                  <p className="stack-title">{item.year}</p>
                  <p className="stack-sub">Predicted {item.predicted_t_ha} / Actual {item.actual_t_ha} t/ha</p>
                </div>
                <span>{item.delta_t_ha} t/ha</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel panel-analytics">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Operations and Integrations</p>
              <h2>External sync and notifications</h2>
            </div>
            <span className="pill accent">{dashboard.integrations?.count || 0} syncs</span>
          </div>
          <div className="analytics-grid">
            <div>
              <strong>{Number(dashboard.economics?.total_revenue_rub || 0).toLocaleString()}</strong>
              <span>revenue RUB</span>
            </div>
            <div>
              <strong>{Number(dashboard.economics?.total_cost_rub || 0).toLocaleString()}</strong>
              <span>cost RUB</span>
            </div>
            <div>
              <strong>{dashboard.notifications?.count || 0}</strong>
              <span>queued notifications</span>
            </div>
            <div>
              <strong>{Object.keys(dashboard.workload?.machinery || {}).length}</strong>
              <span>active machinery</span>
            </div>
          </div>
        </article>
      </section>
    </div>
  );
}
