import { useEffect, useState, useRef } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

export default function App() {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(false);
  const [aiInfo, setAiInfo] = useState(null);
  const [mode, setMode] = useState("easy");    // 追蹤人類對戰模式下的 AI 難度
  const [isArenaRunning, setIsArenaRunning] = useState(false);

  // 🔥 新增：追蹤 AI 競技場中雙方的指定陣容 
  const [arenaP1, setArenaP1] = useState("easy");
  const [arenaP2, setArenaP2] = useState("medium");

  const isArenaRunningRef = useRef(false);

  const fetchState = async () => {
    const res = await fetch(`${API}/state`);
    const data = await res.json();
    setState(data);
  };

  useEffect(() => {
    fetchState();
  }, []);

  const handleModeChange = async (selectedMode) => {
    if (isArenaRunningRef.current) {
      setIsArenaRunning(false);
      isArenaRunningRef.current = false;
    }
    
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

  const handleClick = async (b, r, c) => {
    if (loading || isArenaRunning) return;
    if (!state) return;
    if (state.big_board[b] !== 0) return;

    setLoading(true);

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
      
      if (data.ai_info) {
        setAiInfo(data.ai_info);
      } else {
        setAiInfo(null);
      }
    } catch (err) {
      console.error("Move failed:", err);
      fetchState();
    } finally {
      setLoading(false);
    }
  };

  // ⚡ 改造：將前端選擇的雙方模式打包 POST 送給升級後的後端
  const triggerArenaStep = async () => {
    try {
      const res = await fetch(`${API}/arena-step`, { 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          p1_mode: arenaP1,
          p2_mode: arenaP2
        })
      });
      const data = await res.json();
      
      setState(data.state);
      if (data.ai_info) {
        setAiInfo(data.ai_info);
      }
      return data;
    } catch (err) {
      console.error("Arena step failed:", err);
      setIsArenaRunning(false);
      isArenaRunningRef.current = false;
      return { game_over: true };
    }
  };

  const handleSingleArenaStep = async () => {
    if (loading || isArenaRunning) return;
    setLoading(true);
    await triggerArenaStep();
    setLoading(false);
  };

  const toggleArenaBattle = () => {
    const nextState = !isArenaRunning;
    setIsArenaRunning(nextState);
    isArenaRunningRef.current = nextState;
  };

  // 將 arenaP1 與 arenaP2 加進依賴項，確保切換時 loop 讀取到最新設定
  useEffect(() => {
    let timerId = null;

    const runLoop = async () => {
      if (!isArenaRunningRef.current) return;
      
      setLoading(true);
      const data = await triggerArenaStep();
      setLoading(false);

      if (data && !data.game_over && isArenaRunningRef.current) {
        timerId = setTimeout(runLoop, 1000);
      } else if (data && data.game_over) {
        setIsArenaRunning(false);
        isArenaRunningRef.current = false;
      }
    };

    if (isArenaRunning) {
      runLoop();
    }

    return () => {
      if (timerId) clearTimeout(timerId);
    };
  }, [isArenaRunning, arenaP1, arenaP2]); 

  const reset = async () => {
    setIsArenaRunning(false);
    isArenaRunningRef.current = false;
    setLoading(true);
    await fetch(`${API}/reset`, { method: "POST" });
    setAiInfo(null);
    await fetchState();
    setLoading(false);
  };

  if (!state) return <div className="loading">Loading...</div>;

  return (
    <div className="container">
      <h1>Ultimate Tic Tac Toe</h1>

      {/* 控制面板 */}
      <div className="control-panel">
        <button onClick={reset} className="reset">
          Reset Game
        </button>
        
        {/* 👤 手動對戰難度選擇區塊 (升級為 3 選 1) */}
        <div className="panel-section">
          <span className="section-title">👤 人類 vs AI 難度</span>
          <div className="mode-selector">
            <button 
              className={`mode-btn ${mode === "easy" ? "active-mode" : ""}`}
              onClick={() => handleModeChange("easy")}
              disabled={isArenaRunning}
            >
              Easy (Pure Qwen)
            </button>
            <button 
              className={`mode-btn ${mode === "medium" ? "active-mode" : ""}`}
              onClick={() => handleModeChange("medium")}
              disabled={isArenaRunning}
            >
              Medium (Qwen + Gemma)
            </button>
            <button 
              className={`mode-btn ${mode === "minimax" ? "active-mode" : ""}`}
              onClick={() => handleModeChange("minimax")}
              disabled={isArenaRunning}
            >
              Minimax (傳統搜索)
            </button>
          </div>
        </div>

        {/* ⚔️ AI 競技場陣容配置與控制器 */}
        <div className="panel-section arena-section">
          <span className="section-title">⚔️ AI 競技場配置</span>
          
          <div className="arena-selectors">
            <select 
              value={arenaP1} 
              onChange={(e) => setArenaP1(e.target.value)}
              disabled={isArenaRunning}
              className="arena-select"
            >
              <option value="easy">P1 先手: Easy</option>
              <option value="medium">P1 先手: Medium</option>
              <option value="minimax">P1 先手: Minimax</option>
            </select>
            
            <span className="vs-text">VS</span>

            <select 
              value={arenaP2} 
              onChange={(e) => setArenaP2(e.target.value)}
              disabled={isArenaRunning}
              className="arena-select"
            >
              <option value="easy">P2 後手: Easy</option>
              <option value="medium">P2 後手: Medium</option>
              <option value="minimax">P2 後手: Minimax</option>
            </select>
          </div>

          <div className="arena-controls">
            <button 
              className={`mode-btn ${isArenaRunning ? "active-mode" : ""}`}
              style={{ 
                backgroundColor: isArenaRunning ? "#e74c3c" : "#9b59b6",
                borderColor: isArenaRunning ? "#e74c3c" : "#9b59b6"
              }}
              onClick={toggleArenaBattle}
            >
              {isArenaRunning ? "⏸️ Pause Arena" : "⚔️ Run AI vs AI"}
            </button>
            <button 
              className="mode-btn"
              onClick={handleSingleArenaStep}
              disabled={isArenaRunning || loading}
            >
              ⏭️ Next Step
            </button>
          </div>
        </div>
      </div>

      {loading && (
        <p className="thinking-text">
          {isArenaRunning ? "🤖 Arena Battling & Thinking..." : "AI thinking..."}
        </p>
      )}

      {/* 大棋盤區 */}
      <div className="big-board">
        {state.board.map((small, b) => {
          const isActive = state.active_box === null || state.active_box === b;
          const bigBoardStatus = state.big_board[b];

          return (
            <div
              key={b}
              className={`small-board 
                ${isActive && bigBoardStatus === 0 ? "active" : ""} 
                ${bigBoardStatus !== 0 ? "completed" : ""}`}
            >
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

      {/* AI 思考軌跡區 */}
      {aiInfo && (
        <div className="ai-reason-box">
          <h3>Latest Decision Track:</h3>
          <p style={{ fontWeight: "bold", color: "#3b82f6", marginBottom: "5px" }}>
            落子點：Box {aiInfo.box}, Row {aiInfo.row}, Col {aiInfo.col}
          </p>
          <p>{aiInfo.reason}</p>
        </div>
      )}
    </div>
  );
}