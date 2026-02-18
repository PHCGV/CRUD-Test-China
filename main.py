from fastapi import FastAPI
import uvicorn
from app.routes import produto_routes, frete_routes

app = FastAPI(title="China/CSSBuy CRUD")

app.include_router(produto_routes.router)
app.include_router(frete_routes.router)


@app.get("/")
def home():
    return {"mensagem": "Sistema funcionando em /docs"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)