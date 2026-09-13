import React, { useEffect, useState } from "react";

export interface TelemetryData {
  network: {
    mode: string;
    mode_display: string;
    external_calls_attempted: number;
    external_calls_blocked: number;
    is_sovereign: boolean;
    verdict: string;
    uptime_seconds: number;
  };
  modules: Record<string, { status: string; [key: string]: any }>;
  hardware: {
    available_vram_gb: number;
    available_ram_gb: number;
    is_uma: boolean;
    status_label: string;
  };
}

export const SovereignSecurityDashboard: React.FC = () => {
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [modeSwitching, setModeSwitching] = useState(false);

  const fetchTelemetry = async () => {
    try {
      const res = await fetch("http://127.0.0.1:5174/api/sovereign/telemetry");
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
    } catch (err) {
      console.debug("Telemetry fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 1500);
    return () => clearInterval(interval);
  }, []);

  const switchMode = async (targetMode: string) => {
    setModeSwitching(true);
    try {
      await fetch("http://127.0.0.1:5174/api/sovereign/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: targetMode }),
      });
      await fetchTelemetry();
    } catch (e) {
      console.error(e);
    } finally {
      setModeSwitching(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "20px", color: "#00ced1", fontFamily: "monospace" }}>
        [INITIATING SECUREFORGE TELEMETRY RING...]
      </div>
    );
  }

  const isSovereign = telemetry?.network.is_sovereign ?? true;

  return (
    <div
      style={{
        backgroundColor: "#070b14",
        border: "1px solid #14284b",
        borderRadius: "8px",
        padding: "16px",
        color: "#e2e8f0",
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        boxShadow: "0 0 20px rgba(0, 206, 209, 0.15)",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #14284b", paddingBottom: "10px" }}>
        <div>
          <span style={{ color: "#00ced1", fontWeight: "bold" }}>IVERI SOVEREIGN MONITOR</span>
          <span style={{ marginLeft: "12px", fontSize: "12px", color: "#64748b" }}>DEFENSE-GRADE TELEMETRY</span>
        </div>
        <div
          style={{
            backgroundColor: isSovereign ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
            border: `1px solid ${isSovereign ? "#10b981" : "#ef4444"}`,
            borderRadius: "4px",
            padding: "2px 8px",
            fontSize: "12px",
            color: isSovereign ? "#10b981" : "#ef4444",
            fontWeight: "bold",
          }}
        >
          {isSovereign ? "🛡️ AIR-GAPPED // ZERO EXFILTRATION" : "⚠️ EXTERNAL ATTEMPTS DETECTED"}
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginTop: "14px" }}>
        <div style={{ backgroundColor: "#0b1329", padding: "10px", borderRadius: "4px", border: "1px solid #1e3a8a" }}>
          <div style={{ fontSize: "11px", color: "#94a3b8" }}>NETWORK ISOLATION</div>
          <div style={{ fontSize: "16px", fontWeight: "bold", color: "#38bdf8", marginTop: "4px" }}>
            {telemetry?.network.mode_display || "STANDBY"}
          </div>
        </div>

        <div style={{ backgroundColor: "#0b1329", padding: "10px", borderRadius: "4px", border: "1px solid #1e3a8a" }}>
          <div style={{ fontSize: "11px", color: "#94a3b8" }}>EXTERNAL ATTEMPTS</div>
          <div style={{ fontSize: "16px", fontWeight: "bold", color: isSovereign ? "#10b981" : "#ef4444", marginTop: "4px" }}>
            {telemetry?.network.external_calls_attempted || 0}
          </div>
        </div>

        <div style={{ backgroundColor: "#0b1329", padding: "10px", borderRadius: "4px", border: "1px solid #1e3a8a" }}>
          <div style={{ fontSize: "11px", color: "#94a3b8" }}>AVAILABLE VRAM/BUDGET</div>
          <div style={{ fontSize: "16px", fontWeight: "bold", color: "#fbbf24", marginTop: "4px" }}>
            {telemetry?.hardware.available_vram_gb || 0} GB
          </div>
        </div>

        <div style={{ backgroundColor: "#0b1329", padding: "10px", borderRadius: "4px", border: "1px solid #1e3a8a" }}>
          <div style={{ fontSize: "11px", color: "#94a3b8" }}>SYSTEM RAM</div>
          <div style={{ fontSize: "16px", fontWeight: "bold", color: "#a855f7", marginTop: "4px" }}>
            {telemetry?.hardware.available_ram_gb || 0} GB
          </div>
        </div>
      </div>

      {/* Mode Controls */}
      <div style={{ marginTop: "16px", display: "flex", gap: "10px", alignItems: "center" }}>
        <span style={{ fontSize: "12px", color: "#64748b" }}>SWITCH ENFORCEMENT:</span>
        {["air_gapped", "lan_only", "online"].map((m) => (
          <button
            key={m}
            disabled={modeSwitching}
            onClick={() => switchMode(m)}
            style={{
              backgroundColor: telemetry?.network.mode === m ? "#0284c7" : "#0f172a",
              border: "1px solid #334155",
              color: "#f8fafc",
              padding: "4px 10px",
              borderRadius: "4px",
              fontSize: "12px",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            {m.replace("_", " ").toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
};
