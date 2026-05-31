let state = null;

const boardEl = document.getElementById("board");
const currentPlayerEl = document.getElementById("current-player");
const activeMicroEl = document.getElementById("active-micro");
const humanSideEl = document.getElementById("human-side");
const aiSideEl = document.getElementById("ai-side");
const aiLatencyEl = document.getElementById("ai-latency");
const resultEl = document.getElementById("result");
const historyEl = document.getElementById("history");

const checkpointSelect = document.getElementById("checkpoint-select");
const mctsSimsInput = document.getElementById("mcts-sims");
const humanFirstInput = document.getElementById("human-first");
const newGameBtn = document.getElementById("new-game-btn");


function playerToText(player) {
    if (player === 1) {
        return "O";
    }

    if (player === -1) {
        return "X";
    }

    return "-";
}


function cellToText(value) {
    if (value === 1) {
        return "O";
    }

    if (value === -1) {
        return "X";
    }

    return "";
}


function actionToMicro(action) {
    return Math.floor(action / 9);
}


function actionToLocal(action) {
    return action % 9;
}


function localToRowCol(local) {
    return {
        row: Math.floor(local / 3),
        col: local % 3
    };
}


async function fetchState() {
    const res = await fetch("/api/state");
    state = await res.json();
    render();
}


async function fetchCheckpoints() {
    const res = await fetch("/api/checkpoints");
    const checkpoints = await res.json();

    checkpointSelect.innerHTML = "";

    for (const ckpt of checkpoints) {
        const option = document.createElement("option");
        option.value = ckpt;
        option.textContent = ckpt;
        checkpointSelect.appendChild(option);
    }

    if (checkpoints.length === 0) {
        const option = document.createElement("option");
        option.value = "checkpoints/uttt_model_iter_25.pth";
        option.textContent = "checkpoints/uttt_model_iter_25.pth";
        checkpointSelect.appendChild(option);
    }
}


async function startNewGame() {
    const payload = {
        human_first: humanFirstInput.checked,
        model_path: checkpointSelect.value,
        mcts_sims: parseInt(mctsSimsInput.value)
    };

    const res = await fetch("/api/new_game", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    state = await res.json();
    render();
}


async function humanMove(action) {
    if (!state) {
        return;
    }

    if (state.game_over) {
        return;
    }

    if (state.current_player !== state.human_player) {
        return;
    }

    if (!state.legal_actions.includes(action)) {
        return;
    }

    const res = await fetch("/api/human_move", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            action: action
        })
    });

    const data = await res.json();

    if (!data.ok) {
        alert(data.error);
    }

    state = data.state;
    render();
}


function render() {
    renderBoard();
    renderStatus();
    renderHistory();
}


function renderBoard() {
    boardEl.innerHTML = "";

    const legalSet = new Set(state.legal_actions);
    const lastMove = state.history.length > 0
        ? state.history[state.history.length - 1].move
        : null;

    for (let micro = 0; micro < 9; micro++) {
        const microEl = document.createElement("div");
        microEl.className = "micro-board";

        const microWinner = state.micro_winners[micro];

        if (state.active_micro === micro) {
            microEl.classList.add("active");
        }

        if (microWinner === 1) {
            microEl.classList.add("won-o", "done");
        } else if (microWinner === -1) {
            microEl.classList.add("won-x", "done");
        } else if (microWinner === 2) {
            microEl.classList.add("draw", "done");
        }

        for (let local = 0; local < 9; local++) {
            const action = micro * 9 + local;
            const value = state.board[action];

            const cell = document.createElement("button");
            cell.className = "cell";
            cell.textContent = cellToText(value);

            if (value === 1) {
                cell.classList.add("o");
            } else if (value === -1) {
                cell.classList.add("x");
            }

            if (legalSet.has(action) && !state.game_over && state.current_player === state.human_player) {
                cell.classList.add("legal");
            } else {
                cell.classList.add("illegal");
            }

            if (action === lastMove) {
                cell.classList.add("last-move");
            }

            cell.title = `Action ${action}`;

            cell.addEventListener("click", () => {
                humanMove(action);
            });

            microEl.appendChild(cell);
        }

        boardEl.appendChild(microEl);
    }
}


function renderStatus() {
    currentPlayerEl.textContent = playerToText(state.current_player);

    if (state.active_micro === -1) {
        activeMicroEl.textContent = "Wildcard";
    } else {
        activeMicroEl.textContent = state.active_micro;
    }

    humanSideEl.textContent = playerToText(state.human_player);
    aiSideEl.textContent = playerToText(state.ai_player);

    aiLatencyEl.textContent = `${state.last_ai_latency.toFixed(4)}s`;

    if (!state.game_over) {
        resultEl.textContent = "Playing";
        return;
    }

    if (state.winner === 1) {
        resultEl.textContent = "O Wins";
    } else if (state.winner === -1) {
        resultEl.textContent = "X Wins";
    } else {
        resultEl.textContent = "Draw";
    }
}


function renderHistory() {
    historyEl.innerHTML = "";

    for (let i = 0; i < state.history.length; i++) {
        const h = state.history[i];

        const item = document.createElement("div");
        item.className = `history-item ${h.source}`;

        const micro = actionToMicro(h.move);
        const local = actionToLocal(h.move);
        const pos = localToRowCol(local);

        item.textContent =
            `${String(i + 1).padStart(2, "0")}. ` +
            `${h.source.toUpperCase()} ` +
            `${playerToText(h.player)} ` +
            `move=${h.move} ` +
            `(B${micro}, r${pos.row}, c${pos.col})`;

        historyEl.appendChild(item);
    }

    historyEl.scrollTop = historyEl.scrollHeight;
}


newGameBtn.addEventListener("click", startNewGame);


async function main() {
    await fetchCheckpoints();
    await fetchState();
}

main();