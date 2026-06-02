from pydantic import BaseModel

class Move(BaseModel):
    box: int
    row: int
    col: int

class ModeSetting(BaseModel):
    mode: str

class ArenaStepRequest(BaseModel):
    '''
    Easy, Medium, Minimax
    '''
    p1_mode: str  
    p2_mode: str