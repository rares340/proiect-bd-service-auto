import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import auth, clienti, vehicule, comenzi, itp

app = FastAPI(
    title="Service Auto & ITP API",
    version="1.0.0",
    description="Backend pentru gestionarea service-ului auto și a stației ITP.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Erorile din baza de date devin raspunsuri HTTP
# cu mesajul din SQL, ca sa ajunga in interfata.
def _mesaj(exc: Exception) -> str:
    diag = getattr(exc, "diag", None)
    if diag is not None and diag.message_primary:
        return diag.message_primary
    return str(exc)


@app.exception_handler(psycopg.errors.RaiseException)
async def handle_regula_business(request: Request, exc: psycopg.errors.RaiseException):
    # RAISE EXCEPTION din triggere/functii: stoc insuficient, ITP invalid etc.
    return JSONResponse(status_code=400, content={"detail": _mesaj(exc)})


@app.exception_handler(psycopg.errors.UniqueViolation)
async def handle_unique(request: Request, exc: psycopg.errors.UniqueViolation):
    detaliu = exc.diag.message_detail or ""
    return JSONResponse(status_code=409, content={"detail": f"Valoare deja existenta. {detaliu}".strip()})


@app.exception_handler(psycopg.errors.ForeignKeyViolation)
async def handle_fk(request: Request, exc: psycopg.errors.ForeignKeyViolation):
    detaliu = exc.diag.message_detail or ""
    return JSONResponse(status_code=400, content={"detail": f"Referinta inexistenta. {detaliu}".strip()})


@app.exception_handler(psycopg.errors.CheckViolation)
async def handle_check(request: Request, exc: psycopg.errors.CheckViolation):
    return JSONResponse(status_code=400, content={"detail": f"Valoare invalida: {_mesaj(exc)}"})


@app.exception_handler(psycopg.errors.NotNullViolation)
async def handle_not_null(request: Request, exc: psycopg.errors.NotNullViolation):
    return JSONResponse(status_code=400, content={"detail": f"Camp obligatoriu lipsa: {_mesaj(exc)}"})


app.include_router(auth.router)
app.include_router(clienti.router)
app.include_router(vehicule.router)
app.include_router(comenzi.router)
app.include_router(itp.router)


@app.get("/")
def read_root():
    return {"message": "API-ul ruleaza cu succes"}