# Ultimate Tic-Tac-Toe Monte Carlo 模型使用說明

## 說明

有做 C++ 跟 Python 的版本，Python 是我寫好 C++ 之後請 ChatPGT 5.5 幫我翻譯成 python 的，但由於速度本身差蠻多的，所以比較建議使用 C++。

另外模型強度上 flat 比 mcts 弱很多，可以優先考慮 mcts 就好。

flat 根據搜尋的深度做了 fast 跟 slow 版。

mcts 則根據一些參數跟策略做了 attack, balance, defense 三個不同風格的版本，也可以只以 balance 為主。

## 執行檔案

### C++

先編譯要執行的檔案：

```sh
g++ mcts_balance.cpp -o AI
```

接著執行

```sh
./AI
```

### python

```sh
python mcts_balance.py
```

## 輸入輸出格式

第一行必須輸入一個整數 0 或 1 ，代表：

- 0：該 AI 後手
- 1：該 AI 先手

| (0,0) | (0,1) | (0,2) | ... | (0,8) |
|-------|-------|-------|-----|-------|
| (1,0) | (1,1) | (1,2) | ... | (1,8) |
| (2,0) | (2,1) | (2,2) | ... | (2,8) |
| ...   | ...   | ...   | ... | ...   |
| (8,0) | (8,1) | (8,2) | ... | (8,8) |

接著會用上面的座標來進行遊戲（溝通）。

輪到 AI 時，會給出一組座標，兩個數字用空格隔開。

而需要再輸入另外一位玩家選的格子座標，格式也是兩個數字用空格隔開。

## 直接玩

任何一個 C++ 檔案，都可以透過把 `main` 裡面的註解給取消註解，然後直接跟該 AI 對戰，會顯示提示（輪到誰、放置合法、當前盤面）。

## `battle_mix.py`

可以用這個檔案來讓 C++ 跟 python 模型對戰。

建議在 Windows 上面跑。

但輸出輸入格式必須要符合我上面寫的。

### C++ vs C++

先編譯兩個要對戰的檔案

```sh
g++ mcts_attack.cpp -o AI1
g++ mcts_defense.cpp -o AI2
```

然後跑：

```sh
python battle_mix.py .\AI1.exe .\AI2.exe battle.log <對戰次數> <timeout 時間（毫秒）> <0/1 是否在log中顯示每一步的盤面>
```

### C++ vs python

先編譯 C++

```sh
g++ mcts_balance.cpp -o AI
```

然後跑：

```sh
python .\battle_mix.py .\AI.exe "python -u .\mcts_balance.py" battle.log <對戰次數> <timeout 時間（毫秒）> <0/1 是否在log中顯示每一步的盤面>
```

### python vs python

```sh
python .\battle_mix.py "python -u .\mcts_attack.py" "python -u .\mcts_defense.py" battle.log <對戰次數> <timeout 時間（毫秒）> <0/1 是否在log中顯示每一步的盤面>
```