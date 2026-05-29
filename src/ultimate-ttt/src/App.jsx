import { useEffect, useState, useRef } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

export default function App() {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(false);
  const [aiInfo, setAiInfo] = useState(null); // 儲存 AI 的最新動作與理由
  const [mode, setMode] = useState("easy");    // 追蹤當前的難度模式 ("easy" 或 "medium")
  const [isArenaRunning, setIsArenaRunning] = useState(false); // 畫面上按鈕顯示狀態

  // 🔒 核心關鍵：用來做非同步瞬間暫停的「絕對防禦護欄」
  // 它的值變更時不需要等網頁 Re-render，非同步 loop 隨時讀它都是最即時的最新狀態
  const isArenaRunningRef = useRef(false);

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
    // 如果正在自動對打，切換手動難度時強行切斷對戰
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

  // -----------------------
  // 玩家手動落子與連鎖 AI 邏輯
  // -----------------------
  const handleClick = async (b, r, c) => {
    if (loading || isArenaRunning) return; // 如果正在自動對打，禁止人類插手
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

  // -----------------------
  // 競技場單步驅動 (對接後端 /arena-step)
  // -----------------------
  const triggerArenaStep = async () => {
    try {
      const res = await fetch(`${API}/arena-step`, { method: "POST" });
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

  // ⏭️ 手動點擊「下一步」按鈕驅動
  const handleSingleArenaStep = async () => {
    if (loading || isArenaRunning) return;
    setLoading(true);
    await triggerArenaStep();
    setLoading(false);
  };

  // ⚔️ 點擊「Run AI vs AI」或「Pause」按鈕切換
  const toggleArenaBattle = () => {
    const nextState = !isArenaRunning;
    setIsArenaRunning(nextState);
    isArenaRunningRef.current = nextState; // 🔥 即時更新 Ref，讓非同步 loop 能秒讀到暫停訊號
  };

  // -----------------------
  // 自動對弈控制循環（雙重動態阻斷護欄）
  // -----------------------
  useEffect(() => {
    let timerId = null;

    const runLoop = async () => {
      // 🛡️ 護欄 1：進入前檢查，如果已經被叫停，立刻原地解散
      if (!isArenaRunningRef.current) return;
      
      setLoading(true);
      const data = await triggerArenaStep();
      setLoading(false);

      // 🛡️ 護欄 2：重要！等候後端大模型漫長的思考與 API 回傳回來後（通常過了 1~2 秒），
      // 必須再次即時檢查使用者在這段空檔內「有沒有按下暫停」。
      // 如果有，絕對不再設定下一次的計時器，當場斬斷幽靈計時器！
      if (data && !data.game_over && isArenaRunningRef.current) {
        timerId = setTimeout(runLoop, 1000); // 1 秒後引導下一步
      } else if (data && data.game_over) {
        setIsArenaRunning(false);
        isArenaRunningRef.current = false;
      }
    };

    if (isArenaRunning) {
      runLoop();
    }

    // 終極清理：當 Component 狀態改變時，死死掐斷任何殘留的背景 timer
    return () => {
      if (timerId) clearTimeout(timerId);
    };
  }, [isArenaRunning]);

  // -----------------------
  // 重置遊戲
  // -----------------------
  const reset = async () => {
    setIsArenaRunning(false); 
    isArenaRunningRef.current = false; // 🔥 重置時死死掐斷 Ref 護欄，避免重置後 AI 還在背景偷下
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
        
        {/* 手動難度選擇 */}
        <div className="mode-selector">
          <button 
            className={`mode-btn ${mode === "easy" ? "active-mode" : ""}`}
            onClick={() => handleModeChange("easy")}
            disabled={isArenaRunning}
          >
            Easy (Pure LLM)
          </button>
          <button 
            className={`mode-btn ${mode === "medium" ? "active-mode" : ""}`}
            onClick={() => handleModeChange("medium")}
            disabled={isArenaRunning}
          >
            Medium (Phi + Minimax)
          </button>
        </div>

        {/* AI vs AI 競技場控制器 */}
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

      {loading && (
        <p className="thinking-text">
          {isArenaRunning ? "🤖 Arena Battling & Thinking..." : "AI thinking..."}
        </p>
      )}

      <div className="big-board">
        {state.board.map((small, b) => {
          const isActive = state.active_box === null || state.active_box === b;
          const bigBoardStatus = state.big_board[b]; // 0: ongoing, 1: X won, 2: O won, 3: draw

          return (
            <div
              key={b}
              className={`small-board 
                ${isActive && bigBoardStatus === 0 ? "active" : ""} 
                ${bigBoardStatus !== 0 ? "completed" : ""}`}
            >
              {/* 大格連線或平手覆蓋層 */}
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

                  // 高亮 AI 最新落子
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

      {/* AI 思考軌跡與 Reason 即時刷新區 */}
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