from fastapi import FastAPI, HTTPException
from calculator import Calculator

app = FastAPI()
calc = Calculator()

@app.get("/add")
def add(a: float, b: float):
    return {"result": calc.add(a, b)}

@app.get("/divide")
def divide(a: float, b: float):
    try:
        return {"result": calc.divide(a, b)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
