from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, clienti, vehicule, comenzi, itp

app = FastAPI(
    title="Service Auto & ITP API",
    version="1.0.0",
    description="Backend pentru service auto"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(clienti.router)
app.include_router(vehicule.router)
app.include_router(comenzi.router)
app.include_router(itp.router)

@app.get("/")
def read_root():
    return {"message": "API-ul ruleaza cu succes"}
