import { useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

export default function App() {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(false);
  const [aiInfo, setAiInfo] = useState(null);

  // -----------------------
  // fetch state
  // -----------------------
  const fetchState = async () => {
    const res = await fetch(`${API}/state`);
    const data = await res.json();
    setState(data);
  };

  useEffect(() => {
    fetchState();
  }, []);

  // -----------------------
  // player move (stable version)
  // -----------------------
  const handleClick = async (b, r, c) => {
    if (loading) return;

    // ❌ 防止 null crash
    if (!state) return;

    setLoading(true);

    // 1. optimistic UI（玩家立即看到）
    setState(prev => {
      const newState = structuredClone(prev);
      newState.board[b][r][c] = 1;
      return newState;
    });

    try {
      // 2. send move + let backend handle AI
      const res = await fetch(`${API}/move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ box: b, row: r, col: c })
      });

      const data = await res.json();

      // 3. replace with authoritative state (包含 AI move)
      setState(data.state);
      if (data.ai_info) {
        setAiInfo(data.ai_info); // 儲存 AI 的動作與理由
      }

    } catch (err) {
      console.error("Move failed:", err);
      fetchState(); // fallback
    } finally {
      setLoading(false);
    }
  };

  // -----------------------
  // reset
  // -----------------------
  const reset = async () => {
    setLoading(true);
    await fetch(`${API}/reset`, { method: "POST" });
    await fetchState();
    setLoading(false);
  };

  // -----------------------
  // loading guard
  // -----------------------
  if (!state) return <div>Loading...</div>;

  return (
    <div className="container">
      <h1>Ultimate Tic Tac Toe</h1>

      <button onClick={reset} className="reset">
        Reset
      </button>

      {loading && <p>AI thinking...</p>}

      {aiInfo && (
        <div className="ai-reason-box">
          <h3>AI's Reasoning</h3>
          <p>{aiInfo.reason}</p>
        </div>
      )}

      <div className="big-board">
        {state.board.map((small, b) => {
          const isActive =
            state.active_box === null || state.active_box === b;

          return (
            <div
              key={b}
              className={`small-board ${isActive ? "active" : ""}`}
            >
              {small.map((row, r) =>
                row.map((cell, c) => {
                  const legal = state.legal_moves?.some(
                    (m) => m[0] === b && m[1] === r && m[2] === c
                  );
                  const isAiMove = aiInfo && aiInfo.box === b && aiInfo.row === r && aiInfo.col === c;
                  return (
                    <div
                      key={`${r}-${c}`}
                      className={`cell ${legal ? "legal" : ""} ${isAiMove ? "ai-cell" : ""}`}
                      onClick={() => handleClick(b, r, c)}
                    >
                      {cell === 1 ? "❌" : cell === 2 ? "⭕" : ""}
                    </div>
                  );
                })
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}