# Ultimate Tic-Tac-Toe Minimax 模型使用說明

此 minimax 模型是一個 stateful Ultimate Tic-Tac-Toe agent。初始化後，agent 會自行維護棋局狀態；整合端只需要在對手落子後傳入該步位置，agent 會回傳自己的下一步。

## 匯入

```python
from minimax_model import MinimaxAgent
from minimax_model import InvalidInitialStateError
```

## 建立 Agent

### 全新棋局

```python
agent = MinimaxAgent(
    model_player="X",
    starting_player="X",
    debug=False,
    max_depth=80,
    time_limit_sec=3.0
)
```

參數：

- `model_player`: minimax 模型使用的棋子，必須是 `"X"` 或 `"O"`
- `starting_player`: 本局先手，必須是 `"X"` 或 `"O"`
- `debug`: 是否輸出 debug txt
- `max_depth`: iterative deepening 最大搜尋深度，預設使用 `80`
- `time_limit_sec`: 單次搜尋時間限制，單位為秒

先手由 `starting_player` 決定，不固定為 `"X"`。

### 恢復既有棋局

若要從中途局面建立 agent，需提供 `initial_board`。

```python
agent = MinimaxAgent(
    model_player="X",
    starting_player="X",
    initial_board={
        "board": visual_board,
        "last_move": {
            "board": 4,
            "row": 1,
            "col": 2,
            "player": "O"
        }
    },
    debug=False,
    max_depth=80,
    time_limit_sec=3.0
)
```

`last_move` 代表目前局面的最後一步，格式如下：

```python
{
    "board": 0,      # 0~8
    "row": 0,        # 0~2
    "col": 0,        # 0~2
    "player": "X"    # "X" 或 "O"
}
```

若提供 `initial_board`，`last_move` 必須存在且不可為 `None`。

完整範例：

```python
from minimax_model import MinimaxAgent

visual_board = [
    [
        [
            ["X", None, None],
            [None, "O", None],
            [None, None, None],
        ],
        [
            [None, None, None],
            [None, None, None],
            [None, None, None],
        ],
        [
            [None, None, None],
            [None, None, None],
            [None, None, None],
        ],
    ],
    [
        [
            [None, None, None],
            [None, None, None],
            [None, None, None],
        ],
        [
            [None, None, None],
            [None, "X", None],
            [None, None, None],
        ],
        [
            [None, None, None],
            [None, None, None],
            [None, None, None],
        ],
    ],
    [
        [
            [None, None, None],
            [None, None, None],
            [None, None, None],
        ],
        [
            [None, None, None],
            [None, None, None],
            [None, None, None],
        ],
        [
            [None, None, None],
            [None, None, None],
            [None, None, "O"],
        ],
    ],
]

agent = MinimaxAgent(
    model_player="X",
    starting_player="X",
    initial_board={
        "board": visual_board,
        "last_move": {
            "board": 8,
            "row": 2,
            "col": 2,
            "player": "O",
        },
    },
    debug=False,
    max_depth=80,
    time_limit_sec=3.0,
)

result = agent.step()
print(agent.format_result(result))
```

## 棋盤格式

`initial_board["board"]` 使用 3x3 的大棋盤格式：

```python
visual_board = [
    [small_board_0, small_board_1, small_board_2],
    [small_board_3, small_board_4, small_board_5],
    [small_board_6, small_board_7, small_board_8],
]
```

每個 `small_board` 是 3x3：

```python
[
    ["X", "O", None],
    [None, "X", None],
    ["O", None, None]
]
```

Cell 只能是：

```python
"X"
"O"
None
```

小棋盤 index：

```text
0 | 1 | 2
---------
3 | 4 | 5
---------
6 | 7 | 8
```

小棋盤內部座標：

```text
(0,0) | (0,1) | (0,2)
---------------------
(1,0) | (1,1) | (1,2)
---------------------
(2,0) | (2,1) | (2,2)
```

## 呼叫 Minimax 模型下棋

主要方法：

```python
result = agent.step(move=None)
```

### Agent 直接下棋

目前輪到 minimax 模型時，使用：

```python
result = agent.step()
print(agent.format_result(result))
```

### 對手剛下完

對手下完後，傳入對手剛下的位置：

```python
result = agent.step({
    "board": 0,
    "row": 1,
    "col": 2
})

print(agent.format_result(result))
```

`step(move)` 中的 `move` 永遠代表對手的 move。Move 內不需要傳入玩家，agent 會依照 `model_player` 推導對手棋子。

### Minimax 模型先手範例

```python
from minimax_model import MinimaxAgent

agent = MinimaxAgent(
    model_player="X",
    starting_player="X",
    debug=False,
    max_depth=80,
    time_limit_sec=3.0
)

# 目前輪到 minimax 模型，下第一步
result = agent.step()
print(agent.format_result(result))
```

流程：

```text
建立 agent
呼叫 step()
讀取 result["move"]
將 minimax 模型的 move 套用到外部棋盤或裁判系統
等待對手下一步
```

### Minimax 模型後手範例

```python
from minimax_model import MinimaxAgent

agent = MinimaxAgent(
    model_player="O",
    starting_player="X",
    debug=False,
    max_depth=80,
    time_limit_sec=3.0
)

# 對手 X 剛下在 board=4, row=1, col=1
result = agent.step({
    "board": 4,
    "row": 1,
    "col": 1
})

print(agent.format_result(result))
```

流程：

```text
建立 agent
等待對手先下
將對手 move 傳入 step(move)
讀取 result["move"]
將 minimax 模型的 move 套用到外部棋盤或裁判系統
```

## Move Input

```python
move = {
    "board": 0,  # 0~8
    "row": 1,   # 0~2
    "col": 2    # 0~2
}
```

## Output

格式化輸出：

```python
print(agent.format_result(result))
```

輸出 JSON 會使用縮排與換行。

### 正常回合

```python
{
    "status": "ok",
    "move": {
        "board": 7,
        "row": 0,
        "col": 2
    },
    "player": "X",
    "stats": {
        "thinking_time_sec": 1.231
    }
}
```

欄位：

- `status`: `"ok"` 表示 minimax 模型成功回傳一步
- `move`: minimax 模型選擇的落子位置
- `player`: minimax 模型的棋子
- `thinking_time_sec`: 本次搜尋與決策時間

### 遊戲結束

對手 move 造成終局時，minimax 模型不會再下棋：

```python
{
    "status": "game_over",
    "move": None,
    "winner": "O",
    "player": "X",
    "stats": {
        "thinking_time_sec": 0.0
    }
}
```

minimax 模型的最後一步造成終局時，`move` 會回傳該最後一步：

```python
{
    "status": "game_over",
    "move": {
        "board": 7,
        "row": 0,
        "col": 2
    },
    "winner": "X",
    "player": "X",
    "stats": {
        "thinking_time_sec": 1.231
    }
}
```

`winner` 可能是：

```python
"X"
"O"
"D"
```

`"D"` 表示平手。

### 非法 Move

整合端傳入非法對手 move 時，回傳：

```python
{
    "status": "invalid_move",
    "move": None,
    "error": {
        "code": "BOARD_NOT_LEGAL",
        "message": "Target board is not legal in the current state."
    }
}
```

常見原因：

- move 格式錯誤
- `board` / `row` / `col` 超出範圍
- 目標格已經有棋
- 目標小棋盤已結束
- 目標小棋盤不是目前合法可下的位置
- 遊戲已經結束
- 目前不是對手回合

### 非法狀態

不是 minimax 模型的回合卻呼叫 `step(None)` 時，回傳：

```python
{
    "status": "invalid_state",
    "move": None,
    "error": {
        "code": "NOT_MODEL_TURN",
        "message": "It is not model player's turn."
    }
}
```

### 內部錯誤

```python
{
    "status": "internal_error",
    "move": None,
    "error": {
        "code": "MODEL_MOVE_ILLEGAL",
        "message": "Model selected an illegal move."
    }
}
```

Debug txt 寫入失敗時，回傳：

```python
{
    "status": "internal_error",
    "move": None,
    "error": {
        "code": "DEBUG_WRITE_FAILED",
        "message": "Failed to write debug report."
    }
}
```

## Debug

Debug 預設關閉。

啟用 debug：

```python
agent = MinimaxAgent(
    model_player="X",
    starting_player="X",
    debug=True,
    debug_output_path="debug_board.txt",
    max_depth=80,
    time_limit_sec=3.0
)
```

Debug 行為：

- agent 初始化時會覆蓋並重建 `debug_output_path`
- 每次 `step` 後 append 一段 report
- 同一個 agent instance 的完整棋局會保存在同一份 debug txt
- debug 寫入失敗時，`step` 會回傳 `internal_error`

Debug report 包含：

- 棋盤
- `thinking_time_sec`
- `heuristic_time_sec`
- `move_ordering_time_sec`
- `search_depth`
- `nodes_searched`
- `alpha_beta_cutoffs`
- `transposition_hits`

## 初始化錯誤

初始化時若參數或棋盤不合法，會 raise exception。

### `InvalidInitialStateError`

常見原因：

- `model_player` 或 `starting_player` 不是 `"X"` / `"O"`
- `initial_board` 格式錯誤
- `last_move` 缺失或與棋盤不一致
- X/O 數量不合理
- 傳入的 `initial_board` 已經是終局棋盤
- `max_depth` 不是正整數
- `time_limit_sec` 不是正數

## 簡單範例

```python
from minimax_model import MinimaxAgent

agent = MinimaxAgent(
    model_player="X",
    starting_player="X",
    debug=False,
    max_depth=80,
    time_limit_sec=3.0
)

# minimax 模型先下
result = agent.step()
print(agent.format_result(result))

while result["status"] == "ok":
    raw = input("Opponent move (board row col): ").strip()

    if raw.lower() in {"q", "quit", "exit"}:
        break

    board, row, col = map(int, raw.split())

    result = agent.step({
        "board": board,
        "row": row,
        "col": col
    })

    print(agent.format_result(result))
```

## 整合注意事項

- 初始化後，整合端不需要每回合傳完整棋盤
- 對手下完後，呼叫 `step(move)`
- 目前輪到 minimax 模型下棋時，呼叫 `step(None)` 或 `step()`
- `status == "ok"` 時，整合端應套用回傳的 `move`
- `status == "game_over"` 時，整合端應讀取 `winner`
- `status == "invalid_move"` 時，代表整合端傳入的對手 move 不合法
- `status == "invalid_state"` 時，代表目前狀態不允許 minimax 模型直接下棋
- `status == "internal_error"` 時，代表 agent 內部流程或 debug 輸出異常
