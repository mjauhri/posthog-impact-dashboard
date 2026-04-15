import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

function ScoreBar({ label, value }) {
  return (
    <div className="bar">
      <div className="bar-label">{label}</div>
      <div className="bar-rail">
        <div className="bar-fill" style={{ width: `${value}%` }} />
      </div>
      <div className="bar-value">{value}</div>
    </div>
  );
}

function EngineerCard({ engineer, index, active, onClick }) {
  return (
    <button className={`card ${active ? "active" : ""}`} onClick={onClick}>
      <div className="card-head">
        <div className="rank">#{index + 1}</div>
        <div className="card-title">
          <div className="name">{engineer.name}</div>
          <div className="area">{engineer.area}</div>
        </div>
        <div className="score-box">
          <div className="score">{engineer.score}</div>
          <div className="score-label">impact</div>
        </div>
      </div>
      <p className="why">{engineer.why}</p>
      <div className="chips">
        {engineer.chips.map((chip) => (
          <span className="chip" key={chip}>{chip}</span>
        ))}
      </div>
    </button>
  );
}

export default function App() {
  const [sortMode, setSortMode] = useState("score");
  const [days, setDays] = useState(90);
  const [engineers, setEngineers] = useState([]);
  const [summary, setSummary] = useState(null);
  const [selectedName, setSelectedName] = useState("");
  const [refreshTick, setRefreshTick] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    const refresh = refreshTick > 0 ? "&refresh=true" : "";
    Promise.all([
      fetch(`${API_BASE}/api/summary?days=${days}${refresh}`).then((r) => r.json()),
      fetch(`${API_BASE}/api/engineers?days=${days}&sort=${sortMode}${refresh}`).then((r) => r.json())
    ]).then(([summaryData, engineersData]) => {
      if (summaryData.error) {
        setError(summaryData.error);
        return;
      }
      if (engineersData.error) {
        setError(engineersData.error);
        return;
      }
      setError("");
      setSummary(summaryData);
      setEngineers(engineersData);
      if (!selectedName && engineersData.length) {
        setSelectedName(engineersData[0].name);
      }
    }).catch((e) => setError(String(e)));
  }, [sortMode, days, refreshTick]);

  const selected = useMemo(
    () => engineers.find((e) => e.name === selectedName) ?? engineers[0],
    [engineers, selectedName]
  );

  useEffect(() => {
    if (engineers.length && !engineers.some((e) => e.name === selectedName)) {
      setSelectedName(engineers[0].name);
    }
  }, [engineers, selectedName]);

  if (error) {
    return <div className="loading error">{error}</div>;
  }

  if (!engineers.length || !summary) {
    return <div className="loading">Loading live GitHub data…</div>;
  }

  return (
    <div className="page">
      <div className="topbar">
        <section className="panel">
          <div className="eyebrow">PostHog / live GitHub ingestion</div>
          <h1>Most impactful engineers, scored from the repo</h1>
          <p className="subtitle">
            The Python backend ingests merged pull requests from the last {summary.days} days,
            fetches changed files for each PR, then computes ownership, breadth, leverage,
            and execution signals automatically.
          </p>
          <div className="metrics">
            <div className="metric"><div className="metric-k">Repo</div><div className="metric-v">{summary.repo}</div></div>
            <div className="metric"><div className="metric-k">Window</div><div className="metric-v">{summary.days} days</div></div>
            <div className="metric"><div className="metric-k">Merged PRs scored</div><div className="metric-v">{summary.pr_count}</div></div>
            <div className="metric"><div className="metric-k">Generated</div><div className="metric-v">{summary.generated_at.slice(0, 10)}</div></div>
          </div>
        </section>

        <section className="panel">
          <div className="eyebrow">Controls</div>
          <div className="legend">
            <div><strong>Impact</strong> = weighted blend of delivery, repeated ownership, breadth, leverage, and reliability.</div>
            <div><strong>Ownership</strong> rewards sustained work in a consistent domain.</div>
            <div><strong>Leverage</strong> rewards platform, infra, shared library, and cross-cutting changes.</div>
            <div><strong>Execution</strong> rewards fixes, tests, hardening, and reliability-oriented work.</div>
          </div>
          <div className="controls">
            <label>
              Time window
              <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
                <option value={90}>90 days</option>
                <option value={120}>120 days</option>
                <option value={180}>180 days</option>
              </select>
            </label>

            <label>
              Sort by
              <select value={sortMode} onChange={(e) => setSortMode(e.target.value)}>
                <option value="score">Impact score</option>
                <option value="ownership">Ownership</option>
                <option value="breadth">Breadth</option>
                <option value="leverage">Leverage</option>
                <option value="execution">Execution</option>
              </select>
            </label>

            <button onClick={() => setRefreshTick((x) => x + 1)}>Refresh from GitHub</button>
          </div>
          <p className="footnote">
            Use a <code>GITHUB_TOKEN</code> environment variable if you hit public rate limits.
          </p>
        </section>
      </div>

      <div className="main">
        <section className="panel list-panel">
          <div className="eyebrow">Top 5 engineers</div>
          <div className="list">
            {engineers.map((engineer, index) => (
              <EngineerCard
                key={engineer.name}
                engineer={engineer}
                index={index}
                active={engineer.name === selected?.name}
                onClick={() => setSelectedName(engineer.name)}
              />
            ))}
          </div>
        </section>

        <section className="panel detail-panel">
          <div className="eyebrow">Selected engineer</div>
          {selected && (
            <>
              <h2>{selected.name}</h2>
              <p className="detail-lede">{selected.area}. {selected.why}</p>

              <div className="bars">
                <ScoreBar label="Impact score" value={selected.score} />
                <ScoreBar label="Ownership" value={selected.ownership} />
                <ScoreBar label="Breadth" value={selected.breadth} />
                <ScoreBar label="Leverage" value={selected.leverage} />
                <ScoreBar label="Execution" value={selected.execution} />
              </div>

              <div className="section-title">Highest-scoring evidence</div>
              <div className="evidence">
                {selected.evidence.map((item) => (
                  <div className="evidence-item" key={item.pr}>
                    <div className="evidence-pr">{item.pr}</div>
                    <div className="evidence-meta">{item.meta}</div>
                  </div>
                ))}
              </div>

              <div className="two-col">
                <div className="mini">
                  <div className="mini-title">Leader takeaway</div>
                  <ul>
                    {selected.strengths.map((s) => <li key={s}>{s}</li>)}
                  </ul>
                </div>
                <div className="mini">
                  <div className="mini-title">Caveats</div>
                  <ul>
                    {selected.risks.map((s) => <li key={s}>{s}</li>)}
                  </ul>
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
