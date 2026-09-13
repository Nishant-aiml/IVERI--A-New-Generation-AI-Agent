import React, { useEffect, useState } from "react";

export interface ArtifactItem {
  identifier: string;
  type: string;

  title: string;
  content: string;
  version: number;
  file_path?: string;
  created_at: number;
}

export const ArtifactsDrawer: React.FC<{ sessionId?: string }> = ({ sessionId = "default" }) => {
  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  const [activeArtifact, setActiveArtifact] = useState<ArtifactItem | null>(null);

  const fetchArtifacts = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:5174/api/artifacts?session_id=${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setArtifacts(data.artifacts || []);
        if (data.artifacts?.length > 0 && !activeArtifact) {
          setActiveArtifact(data.artifacts[0]);
        }
      }
    } catch (e) {
      console.debug("Failed to fetch artifacts:", e);
    }
  };

  useEffect(() => {
    fetchArtifacts();
    const interval = setInterval(fetchArtifacts, 2000);
    return () => clearInterval(interval);
  }, [sessionId]);

  if (artifacts.length === 0) {
    return null; // Keep drawer collapsed when no artifacts exist
  }

  return (
    <div
      style={{
        width: "360px",
        height: "100%",
        backgroundColor: "#090d16",
        borderLeft: "1px solid #1e293b",
        display: "flex",
        flexDirection: "column",
        fontFamily: "'Inter', sans-serif",
        color: "#f8fafc",
      }}
    >
      {/* Drawer Title */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid #1e293b", display: "flex", justifyContent: "space-between" }}>
        <span style={{ fontWeight: 600, fontSize: "14px", color: "#38bdf8" }}>ARTIFACTS & DELIVERABLES</span>
        <span style={{ fontSize: "12px", color: "#94a3b8" }}>{artifacts.length} total</span>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", overflowX: "auto", borderBottom: "1px solid #1e293b", backgroundColor: "#040711" }}>
        {artifacts.map((a) => (
          <button
            key={a.identifier}
            onClick={() => setActiveArtifact(a)}
            style={{
              padding: "8px 12px",
              fontSize: "12px",
              border: "none",
              borderBottom: activeArtifact?.identifier === a.identifier ? "2px solid #00ced1" : "none",
              backgroundColor: activeArtifact?.identifier === a.identifier ? "#0f172a" : "transparent",
              color: activeArtifact?.identifier === a.identifier ? "#00ced1" : "#94a3b8",
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            {a.title} (v{a.version})
          </button>
        ))}
      </div>

      {/* Content Pane */}
      <div style={{ flex: 1, padding: "16px", overflowY: "auto", fontSize: "13px", lineHeight: "1.6" }}>
        {activeArtifact && (
          <div>
            <div style={{ marginBottom: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase" }}>{activeArtifact.type}</span>
              {activeArtifact.file_path && (
                <button
                  onClick={() => alert(`Saved at: ${activeArtifact.file_path}`)}
                  style={{
                    backgroundColor: "#0284c7",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    padding: "4px 8px",
                    fontSize: "11px",
                    cursor: "pointer",
                  }}
                >
                  Download / Open
                </button>
              )}
            </div>
            <pre
              style={{
                backgroundColor: "#030712",
                padding: "12px",
                borderRadius: "6px",
                border: "1px solid #1f2937",
                overflowX: "auto",
                fontFamily: "monospace",
                color: "#cbd5e1",
              }}
            >
              {activeArtifact.content}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};
