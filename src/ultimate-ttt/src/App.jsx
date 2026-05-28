import { useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

export default function App() {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(false);
  const [aiInfo, setAiInfo] = useState(null); // 儲存 AI 的最新動作與理由
  const [mode, setMode] = useState("easy");    // 追蹤當前的難度模式 ("easy" 或 "medium")

  // -----------------------
  // 獲取後端最新狀態
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
  // 切換遊戲難度 (對接後端 /set-mode)
  // -----------------------
  const handleModeChange = async (selectedMode) => {
    setMode(selectedMode);
    try {
      await fetch(`${API}/set-mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: selectedMode })
      });
    } catch (err) {
      console.error("Failed to change mode:", err);
    }
  };

  // -----------------------
  // 玩家落子與連鎖 AI 邏輯
  // -----------------------
  const handleClick = async (b, r, c) => {
    if (loading) return;
    if (!state) return;

    // 如果這個大格已經分出勝負，則該區塊鎖死不可點擊
    if (state.big_board[b] !== 0) return;

    setLoading(true);

    // 樂觀 UI 更新：讓玩家點擊後立刻在畫面上看到 ❌
    setState(prev => {
      const newState = structuredClone(prev);
      newState.board[b][r][c] = 1;
      return newState;
    });

    try {
      const res = await fetch(`${API}/move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ box: b, row: r, col: c })
      });

      const data = await res.json();
      setState(data.state);
      
      // 更新 AI 思考資訊
      if (data.ai_info) {
        setAiInfo(data.ai_info); 
      } else {
        setAiInfo(null);
      }

    } catch (err) {
      console.error("Move failed:", err);
      fetchState(); // 失敗時拉回後端權威狀態
    } finally {
      setLoading(false);
    }
  };

  // -----------------------
  // 重置遊戲（彻底清除所有狀態）
  // -----------------------
  const reset = async () => {
    setLoading(true);
    await fetch(`${API}/reset`, { method: "POST" });
    setAiInfo(null); // 徹底清空上一步的藍格標記與 Reasoning Box
    await fetchState();
    setLoading(false);
  };

  if (!state) return <div className="loading">Loading...</div>;

  return (
    <div className="container">
      <h1>Ultimate Tic Tac Toe</h1>

      {/* 控制面板：包含重置與難度切換 */}
      <div className="control-panel">
        <button onClick={reset} className="reset">
          Reset
        </button>
        
        <div className="mode-selector">
          <button 
            className={`mode-btn ${mode === "easy" ? "active-mode" : ""}`}
            onClick={() => handleModeChange("easy")}
          >
            Easy (Pure LLM)
          </button>
          <button 
            className={`mode-btn ${mode === "medium" ? "active-mode" : ""}`}
            onClick={() => handleModeChange("medium")}
          >
            Medium (Depth-2 Minimax)
          </button>
        </div>
      </div>

      {loading && <p className="thinking-text">AI thinking...</p>}

      <div className="big-board">
        {state.board.map((small, b) => {
          const isActive = state.active_box === null || state.active_box === b;
          const bigBoardStatus = state.big_board[b]; // 0: 未分勝負, 1: 玩家贏, 2: AI 贏

          return (
            <div
              key={b}
              className={`small-board 
                ${isActive && bigBoardStatus === 0 ? "active" : ""} 
                ${bigBoardStatus !== 0 ? "completed" : ""}`}
            >
              {/* 大格連線優化：將壓暗遮罩層與高亮大符號拆開，防止大符號變淡 */}
              {bigBoardStatus !== 0 && (
                <>
                  <div className="board-grid-mask"></div>
                  <div className="big-board-overlay">
                    {bigBoardStatus === 1 ? "❌" : bigBoardStatus === 2 ? "⭕" : "🤝"}
                  </div>
                </>
              )}

              {small.map((row, r) =>
                row.map((cell, c) => {
                  const legal = state.legal_moves?.some(
                    (m) => m[0] === b && m[1] === r && m[2] === c
                  );

                  // 判斷這一格是否為 AI 的最新落子
                  const isAiMove = aiInfo && aiInfo.box === b && aiInfo.row === r && aiInfo.col === c;

                  return (
                    <div
                      key={`${r}-${c}`}
                      className={`cell 
                        ${legal && bigBoardStatus === 0 ? "legal" : ""} 
                        ${isAiMove ? "ai-cell" : ""}`}
                      onClick={() => bigBoardStatus === 0 && handleClick(b, r, c)}
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

      {/* AI 思考軌跡展示區 */}
      {aiInfo && (
        <div className="ai-reason-box">
          <h3>AI's Reasoning:</h3>
          <p>{aiInfo.reason}</p>
        </div>
      )}
    </div>
  );
}